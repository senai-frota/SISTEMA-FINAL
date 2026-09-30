import { useEffect, useState } from 'react'
import api from '../services/api'
import EmptyState from '../components/EmptyState'
import Modal from '../components/Modal'
import { formatDateTime } from '../utils/format'
import { mensagemErroApi } from '../utils/erros'
import { useFeedback } from '../context/FeedbackContext'

const SITUACOES = [
  { value: '', label: 'Todas as situações' },
  { value: 'ativos', label: 'Registros ativos' },
  { value: 'inativos', label: 'Registros inativos' },
]

function situacaoRegistro(valor) {
  if (valor === true) return 'Ativo'
  if (valor === false) return 'Inativo'
  return '—'
}

function resumoDetalhes(detalhes) {
  if (!detalhes || typeof detalhes !== 'object') return ''
  if (Array.isArray(detalhes.campos) && detalhes.campos.length) {
    return `Campos: ${detalhes.campos.join(', ')}`
  }
  if (detalhes.destino) return `Destino: ${detalhes.destino}`
  if (detalhes.fotos) return `${detalhes.fotos} foto(s)`
  if (detalhes.filtros && typeof detalhes.filtros === 'object') {
    const partes = Object.entries(detalhes.filtros)
      .filter(([, valor]) => valor !== null && valor !== '')
      .map(([chave, valor]) => `${chave}: ${valor}`)
    return partes.length ? `Filtros: ${partes.join(', ')}` : 'Sem filtros'
  }
  return ''
}

const MOTIVOS_FALHA = {
  hash_invalido: 'conteúdo alterado',
  encadeamento_quebrado: 'encadeamento quebrado',
  sequencia_ausente: 'registro ausente',
  versao_desconhecida: 'versão desconhecida',
}

function IntegridadeBanner({ estado, verificando, onVerificar }) {
  if (!estado && !verificando) return null
  const integra = estado?.integra
  const classe = verificando ? '' : integra ? 'audit-integrity-ok' : 'audit-integrity-falha'
  return (
    <div className={`audit-integrity ${classe}`} role="status">
      <div>
        <strong>
          {verificando
            ? 'Verificando integridade da auditoria…'
            : integra
              ? 'Cadeia de auditoria íntegra'
              : 'Inconsistência detectada na auditoria'}
        </strong>
        {estado && !verificando && (
          <>
            <p className="muted-note">
              {estado.total} registro(s) verificados com {estado.algoritmo} (versão {estado.versao_hash}).
              {' '}Último selo: nº {estado.ultima_sequencia} · {String(estado.ultimo_hash).slice(0, 16)}…
            </p>
            {!integra && (
              <p className="muted-note">
                {estado.total_falhas} falha(s):{' '}
                {estado.falhas
                  .slice(0, 3)
                  .map((f) => `nº ${f.sequencia} (${MOTIVOS_FALHA[f.motivo] || f.motivo})`)
                  .join(', ')}
                {estado.total_falhas > 3 ? '…' : ''}
              </p>
            )}
          </>
        )}
      </div>
      <button type="button" className="btn btn-ghost btn-sm" onClick={onVerificar} disabled={verificando}>
        Verificar novamente
      </button>
    </div>
  )
}

export default function Auditoria() {
  const feedback = useFeedback()
  const [aba, setAba] = useState('acoes')
  const [opcoes, setOpcoes] = useState({ acoes: [], entidades: [], tipos_arquivo: [] })
  const [itens, setItens] = useState([])
  const [total, setTotal] = useState(0)
  const [pagina, setPagina] = useState(1)
  const [temProxima, setTemProxima] = useState(false)
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState('')
  const [preview, setPreview] = useState(null)

  const [busca, setBusca] = useState('')
  const [acao, setAcao] = useState('')
  const [entidade, setEntidade] = useState('')
  const [tipoArquivo, setTipoArquivo] = useState('')
  const [situacao, setSituacao] = useState('')
  const [de, setDe] = useState('')
  const [ate, setAte] = useState('')

  const [integridade, setIntegridade] = useState(null)
  const [verificando, setVerificando] = useState(false)

  async function verificarIntegridade() {
    setVerificando(true)
    try {
      const { data } = await api.get('/auditoria/integridade/')
      setIntegridade(data)
    } catch (err) {
      setIntegridade(null)
      feedback.erro(mensagemErroApi(err, 'Não foi possível verificar a integridade da auditoria.'))
    } finally {
      setVerificando(false)
    }
  }

  useEffect(() => {
    api.get('/auditoria/opcoes/').then(({ data }) => setOpcoes(data)).catch(() => {})
    verificarIntegridade()
  }, [])

  useEffect(() => {
    let cancelado = false

    async function load() {
      setLoading(true)
      setErro('')
      try {
        const params = { page: pagina }
        if (busca.trim()) params.busca = busca.trim()
        if (situacao) params.situacao = situacao
        if (de) params.de = de
        if (ate) params.ate = ate
        if (aba === 'acoes') {
          if (acao) params.acao = acao
          if (entidade) params.entidade = entidade
        } else if (tipoArquivo) {
          params.tipo = tipoArquivo
        }
        const caminho = aba === 'acoes' ? '/auditoria/acoes/' : '/auditoria/arquivos/'
        const { data } = await api.get(caminho, { params })
        if (cancelado) return
        setItens(data.results ?? data)
        setTotal(data.count ?? (data.results ?? data).length)
        setTemProxima(Boolean(data.next))
      } catch {
        if (!cancelado) {
          setErro('Não foi possível carregar a auditoria.')
          setItens([])
          setTotal(0)
        }
      } finally {
        if (!cancelado) setLoading(false)
      }
    }

    const timer = setTimeout(load, 250)
    return () => {
      cancelado = true
      clearTimeout(timer)
    }
  }, [aba, pagina, busca, acao, entidade, tipoArquivo, situacao, de, ate])

  function trocarAba(proxima) {
    setAba(proxima)
    setPagina(1)
    setItens([])
  }

  const totalPaginas = Math.max(1, Math.ceil(total / 20))

  return (
    <div className="page">
      <div className="page-header">
        <h1>
          Auditoria
          <span className="page-count page-count-neutral">Somente leitura</span>
        </h1>
      </div>

      <IntegridadeBanner
        estado={integridade}
        verificando={verificando}
        onVerificar={verificarIntegridade}
      />
      <div className="audit-tabs">
        <button
          type="button"
          className={`btn btn-sm ${aba === 'acoes' ? 'btn-primary' : 'btn-ghost'}`}
          onClick={() => trocarAba('acoes')}
        >
          Ações
        </button>
        <button
          type="button"
          className={`btn btn-sm ${aba === 'arquivos' ? 'btn-primary' : 'btn-ghost'}`}
          onClick={() => trocarAba('arquivos')}
        >
          Arquivos e fotos
        </button>
        <input
          className="search-input"
          placeholder={aba === 'acoes' ? 'Buscar por descrição, nome ou matrícula…' : 'Buscar por nome, placa ou matrícula…'}
          value={busca}
          onChange={(e) => {
            setPagina(1)
            setBusca(e.target.value)
          }}
        />
      </div>

      <div className="toolbar">
        {aba === 'acoes' ? (
          <>
            <select
              value={acao}
              onChange={(e) => {
                setPagina(1)
                setAcao(e.target.value)
              }}
            >
              <option value="">Todas as ações</option>
              {opcoes.acoes.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
            <select
              value={entidade}
              onChange={(e) => {
                setPagina(1)
                setEntidade(e.target.value)
              }}
            >
              <option value="">Todas as entidades</option>
              {opcoes.entidades.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
          </>
        ) : (
          <select
            value={tipoArquivo}
            onChange={(e) => {
              setPagina(1)
              setTipoArquivo(e.target.value)
            }}
          >
            <option value="">Todos os arquivos</option>
            {opcoes.tipos_arquivo.map((item) => (
              <option key={item.value} value={item.value}>{item.label}</option>
            ))}
          </select>
        )}

        <select
          value={situacao}
          onChange={(e) => {
            setPagina(1)
            setSituacao(e.target.value)
          }}
        >
          {SITUACOES.map((item) => (
            <option key={item.value || 'todos'} value={item.value}>{item.label}</option>
          ))}
        </select>

        <label className="toolbar-field">
          <span>De</span>
          <input
            type="date"
            aria-label="Data inicial"
            value={de}
            onChange={(e) => {
              setPagina(1)
              setDe(e.target.value)
            }}
          />
        </label>
        <label className="toolbar-field">
          <span>Até</span>
          <input
            type="date"
            aria-label="Data final"
            value={ate}
            onChange={(e) => {
              setPagina(1)
              setAte(e.target.value)
            }}
          />
        </label>
      </div>

      {erro && <div className="form-error">{erro}</div>}

      {loading ? (
        <div className="skeleton-list" />
      ) : itens.length === 0 ? (
        <EmptyState
          icon="▦"
          title={aba === 'acoes' ? 'Nenhuma ação encontrada' : 'Nenhum arquivo encontrado'}
        />
      ) : aba === 'acoes' ? (
        <>
          <div className="table-desktop-only table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Responsável</th>
                  <th>Ação</th>
                  <th>Registro</th>
                  <th>Usuário afetado</th>
                  <th>Situação</th>
                  <th>Descrição</th>
                </tr>
              </thead>
              <tbody>
                {itens.map((item) => (
                  <tr key={item.id}>
                    <td>{formatDateTime(item.criado_em)}</td>
                    <td>
                      {item.ator_nome || 'Sistema'}
                      {item.ator_matricula ? (
                        <small className="muted-note"><br />{item.ator_matricula}</small>
                      ) : null}
                    </td>
                    <td>{item.acao_label}</td>
                    <td>
                      {item.entidade_label}
                      {item.identificacao ? (
                        <small className="muted-note"><br />{item.identificacao}</small>
                      ) : null}
                    </td>
                    <td>
                      {item.usuario_afetado_nome || '—'}
                      {item.usuario_afetado_matricula ? (
                        <small className="muted-note"><br />{item.usuario_afetado_matricula}</small>
                      ) : null}
                    </td>
                    <td>
                      <span className={`chip ${item.registro_ativo === false ? 'chip-inativo' : 'chip-disponivel'}`}>
                        {situacaoRegistro(item.registro_ativo)}
                      </span>
                    </td>
                    <td>
                      {item.descricao}
                      {item.justificativa && (
                        <small className="audit-justificativa"><br /><strong>Justificativa:</strong> {item.justificativa}</small>
                      )}
                      {resumoDetalhes(item.detalhes) && (
                        <small className="muted-note"><br />{resumoDetalhes(item.detalhes)}</small>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mobile-card-list">
            {itens.map((item) => (
              <article key={item.id} className="mobile-entity-card">
                <strong>{item.acao_label}</strong>
                <p className="muted-note">{formatDateTime(item.criado_em)} · {item.ator_nome || 'Sistema'}</p>
                <p>{item.descricao}</p>
                {item.justificativa && (
                  <p className="audit-justificativa"><strong>Justificativa:</strong> {item.justificativa}</p>
                )}
                {item.usuario_afetado_nome && (
                  <p className="muted-note">Usuário afetado: {item.usuario_afetado_nome}</p>
                )}
                <p className="muted-note">
                  {item.entidade_label}
                  {item.identificacao ? ` · ${item.identificacao}` : ''}
                  {' · '}
                  {situacaoRegistro(item.registro_ativo)}
                </p>
              </article>
            ))}
          </div>
        </>
      ) : (
        <>
          <div className="table-desktop-only table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Arquivo</th>
                  <th>Pertence a</th>
                  <th>Enviado por</th>
                  <th>Quando</th>
                  <th>Situação</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {itens.map((item) => (
                  <tr key={`${item.tipo}-${item.id}`}>
                    <td>
                      {item.titulo}
                      <small className="muted-note"><br />{item.nome_arquivo}</small>
                    </td>
                    <td>{item.entidade_rotulo || '—'}</td>
                    <td>{item.autor_nome}</td>
                    <td>{formatDateTime(item.enviado_em)}</td>
                    <td>
                      <span className={`chip ${item.registro_ativo === false ? 'chip-inativo' : 'chip-disponivel'}`}>
                        {situacaoRegistro(item.registro_ativo)}
                      </span>
                    </td>
                    <td className="table-actions">
                      {item.imagem && item.url && (
                        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setPreview(item)}>
                          Ver
                        </button>
                      )}
                      {item.url && (
                        <a className="btn btn-ghost btn-sm" href={item.url} target="_blank" rel="noreferrer">
                          Abrir
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mobile-card-list">
            {itens.map((item) => (
              <article key={`${item.tipo}-${item.id}`} className="mobile-entity-card">
                <strong>{item.titulo}</strong>
                <p className="muted-note">{item.entidade_rotulo}</p>
                <p className="muted-note">
                  {item.autor_nome} · {formatDateTime(item.enviado_em)} · {situacaoRegistro(item.registro_ativo)}
                </p>
                <div className="reservation-actions">
                  {item.imagem && item.url && (
                    <button type="button" className="btn btn-ghost btn-touch" onClick={() => setPreview(item)}>
                      Ver
                    </button>
                  )}
                  {item.url && (
                    <a className="btn btn-ghost btn-touch" href={item.url} target="_blank" rel="noreferrer">
                      Abrir
                    </a>
                  )}
                </div>
              </article>
            ))}
          </div>
        </>
      )}

      {!loading && total > 0 && (
        <div className="pagination">
          <button
            type="button"
            className="btn btn-ghost"
            disabled={pagina <= 1}
            onClick={() => setPagina((atual) => Math.max(1, atual - 1))}
          >
            Anterior
          </button>
          <span className="muted-note">Página {pagina} de {totalPaginas}</span>
          <button
            type="button"
            className="btn btn-ghost"
            disabled={!temProxima}
            onClick={() => setPagina((atual) => atual + 1)}
          >
            Próxima
          </button>
        </div>
      )}

      {preview && (
        <Modal title={preview.titulo} onClose={() => setPreview(null)} width={720}>
          <img className="audit-preview" src={preview.url} alt={preview.titulo} />
          <p className="muted-note">{preview.entidade_rotulo}</p>
        </Modal>
      )}
    </div>
  )
}
