import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import EmptyState from '../components/EmptyState'
import { Barras, ColunasMensais, Rosca } from '../components/Graficos'
import { useFeedback } from '../context/FeedbackContext'
import { mensagemErroApi } from '../utils/erros'
import { formatDateTime } from '../utils/format'

const FILTROS_VAZIOS = { de: '', ate: '', veiculo: '', usuario: '', status: '', turno: '' }

const CORES_SITUACAO = {
  aprovada: 'var(--color-success)',
  valido: 'var(--color-success)',
  proxima_vencimento: 'var(--status-pendente)',
  pendente: 'var(--color-info)',
  vencida: 'var(--color-danger)',
  vencido: 'var(--color-danger)',
  rejeitada: 'var(--status-negada)',
  rejeitado: 'var(--status-negada)',
  sem_cnh: 'var(--color-text-soft)',
  sem_termo: 'var(--color-text-soft)',
}

function isoLocal(data) {
  const mes = String(data.getMonth() + 1).padStart(2, '0')
  const dia = String(data.getDate()).padStart(2, '0')
  return `${data.getFullYear()}-${mes}-${dia}`
}

function periodoRapido(tipo) {
  const hoje = new Date()
  if (tipo === 'mes') {
    return {
      de: isoLocal(new Date(hoje.getFullYear(), hoje.getMonth(), 1)),
      ate: isoLocal(new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0)),
    }
  }
  if (tipo === '30dias') {
    const inicio = new Date(hoje)
    inicio.setDate(inicio.getDate() - 29)
    return { de: isoLocal(inicio), ate: isoLocal(hoje) }
  }
  if (tipo === 'ano') {
    return { de: `${hoje.getFullYear()}-01-01`, ate: `${hoje.getFullYear()}-12-31` }
  }
  return { de: '', ate: '' }
}

function paramsDe(filtros) {
  return Object.fromEntries(Object.entries(filtros).filter(([, valor]) => valor !== ''))
}

function comCores(itens, mapaCores) {
  return itens.map((item) => ({ ...item, cor: mapaCores(item.valor) }))
}

function formatarNumero(valor) {
  return valor === null || valor === undefined ? '—' : Number(valor).toLocaleString('pt-BR')
}

async function mensagemErroExportacao(err) {
  const dados = err?.response?.data
  if (dados instanceof Blob) {
    try {
      return mensagemErroApi({ response: { data: JSON.parse(await dados.text()) } }, 'Não foi possível gerar a planilha.')
    } catch {
      return 'Não foi possível gerar a planilha.'
    }
  }
  return mensagemErroApi(err, 'Não foi possível gerar a planilha.')
}

function nomeArquivo(cabecalho) {
  const encontrado = /filename="?([^";]+)"?/i.exec(cabecalho || '')
  return encontrado ? encontrado[1] : 'relatorio-frota.xlsx'
}

function Kpi({ rotulo, valor, detalhe, destaque }) {
  return (
    <div className={`stat-card ${destaque ? 'stat-card-accent' : ''}`}>
      <span className="stat-label">{rotulo}</span>
      <span className="stat-value">{valor}</span>
      {detalhe && <small className="muted-note">{detalhe}</small>}
    </div>
  )
}

function Painel({ titulo, subtitulo, children, className = '' }) {
  return (
    <section className={`panel report-panel ${className}`}>
      <div className="panel-header">
        <div>
          <h2>{titulo}</h2>
          {subtitulo && <p className="muted-note">{subtitulo}</p>}
        </div>
      </div>
      {children}
    </section>
  )
}

export default function Relatorios() {
  const feedback = useFeedback()
  const [filtros, setFiltros] = useState(FILTROS_VAZIOS)
  const [opcoes, setOpcoes] = useState({ status: [], turnos: [], veiculos: [], usuarios: [] })
  const [dados, setDados] = useState(null)
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState('')
  const [exportando, setExportando] = useState(false)
  const [recarregar, setRecarregar] = useState(0)
  const [maisFiltros, setMaisFiltros] = useState(false)

  const periodoInvalido = Boolean(filtros.de && filtros.ate && filtros.de > filtros.ate)

  useEffect(() => {
    api
      .get('/relatorios/opcoes/')
      .then(({ data }) => setOpcoes(data))
      .catch((err) => feedback.erro(mensagemErroApi(err, 'Não foi possível carregar as opções de filtro.')))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (periodoInvalido) return undefined
    let cancelado = false

    async function carregar() {
      setLoading(true)
      setErro('')
      try {
        const { data } = await api.get('/relatorios/indicadores/', { params: paramsDe(filtros) })
        if (!cancelado) setDados(data)
      } catch (err) {
        if (cancelado) return
        const mensagem = mensagemErroApi(err, 'Não foi possível carregar os indicadores.')
        setErro(mensagem)
        feedback.erro(mensagem)
      } finally {
        if (!cancelado) setLoading(false)
      }
    }

    const timer = setTimeout(carregar, 250)
    return () => {
      cancelado = true
      clearTimeout(timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtros, periodoInvalido, recarregar])

  const alterar = useCallback((campo, valor) => {
    setFiltros((atual) => ({ ...atual, [campo]: valor }))
  }, [])

  const filtrosAtivos = useMemo(
    () => Object.values(filtros).filter((valor) => valor !== '').length,
    [filtros]
  )

  const filtrosExtrasAtivos = ['veiculo', 'usuario', 'status', 'turno'].filter(
    (campo) => filtros[campo] !== ''
  ).length

  async function exportar() {
    if (periodoInvalido) return
    setExportando(true)
    try {
      const resposta = await api.get('/relatorios/exportar/', {
        params: paramsDe(filtros),
        responseType: 'blob',
      })
      const url = URL.createObjectURL(resposta.data)
      const link = document.createElement('a')
      link.href = url
      link.download = nomeArquivo(resposta.headers?.['content-disposition'])
      document.body.appendChild(link)
      link.click()
      link.remove()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
      feedback.sucesso('Planilha gerada. A exportação foi registrada na auditoria.')
    } catch (err) {
      feedback.erro(await mensagemErroExportacao(err))
    } finally {
      setExportando(false)
    }
  }

  const reservas = dados?.reservas
  const frota = dados?.frota
  const usuarios = dados?.usuarios
  const vistorias = dados?.vistorias
  const semMovimento = dados && reservas.total === 0 && vistorias.total === 0

  return (
    <div className="page">
      <div className="page-header">
        <h1>Relatórios</h1>
        <div className="report-actions">
          <Link to="/relatorio-calendario" className="btn btn-ghost">
            Calendário mensal
          </Link>
          <button
            type="button"
            className="btn btn-primary"
            onClick={exportar}
            disabled={exportando || periodoInvalido}
          >
            {exportando ? 'Gerando planilha…' : 'Exportar Excel'}
          </button>
        </div>
      </div>

      <section className="panel report-filters" aria-label="Filtros do relatório">
        <div className="report-filter-row">
          <div className="report-presets">
            {[
              ['mes', 'Este mês'],
              ['30dias', 'Últimos 30 dias'],
              ['ano', 'Este ano'],
              ['tudo', 'Todo o período'],
            ].map(([tipo, rotulo]) => {
              const alvo = periodoRapido(tipo)
              const ativo = filtros.de === alvo.de && filtros.ate === alvo.ate
              return (
                <button
                  key={tipo}
                  type="button"
                  className={`btn btn-sm ${ativo ? 'btn-primary' : 'btn-ghost'}`}
                  onClick={() => setFiltros((atual) => ({ ...atual, ...alvo }))}
                >
                  {rotulo}
                </button>
              )
            })}
          </div>
          <label className="field">
            <span>De</span>
            <input type="date" value={filtros.de} onChange={(e) => alterar('de', e.target.value)} />
          </label>
          <label className="field">
            <span>Até</span>
            <input type="date" value={filtros.ate} onChange={(e) => alterar('ate', e.target.value)} />
          </label>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            aria-expanded={maisFiltros}
            aria-controls="relatorio-mais-filtros"
            onClick={() => setMaisFiltros((aberto) => !aberto)}
          >
            {maisFiltros ? 'Menos filtros' : 'Mais filtros'}
            {filtrosExtrasAtivos > 0 ? ` (${filtrosExtrasAtivos})` : ''}
          </button>
        </div>

        <div id="relatorio-mais-filtros" className="report-filter-grid" hidden={!maisFiltros}>
          <label className="field">
            <span>Veículo</span>
            <select value={filtros.veiculo} onChange={(e) => alterar('veiculo', e.target.value)}>
              <option value="">Todos</option>
              {opcoes.veiculos.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Usuário</span>
            <select value={filtros.usuario} onChange={(e) => alterar('usuario', e.target.value)}>
              <option value="">Todos</option>
              {opcoes.usuarios.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Status da reserva</span>
            <select value={filtros.status} onChange={(e) => alterar('status', e.target.value)}>
              <option value="">Todos</option>
              {opcoes.status.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Turno</span>
            <select value={filtros.turno} onChange={(e) => alterar('turno', e.target.value)}>
              <option value="">Todos</option>
              {opcoes.turnos.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </label>
        </div>

        <div className="report-filter-footer">
          {periodoInvalido ? (
            <small className="field-error">A data final deve ser igual ou posterior à data inicial.</small>
          ) : (
            <small className="muted-note">
              {filtrosAtivos ? `${filtrosAtivos} filtro(s) aplicado(s).` : 'Sem filtros: todo o histórico.'}
              {dados?.gerado_em ? ` Atualizado em ${formatDateTime(dados.gerado_em)}.` : ''}
            </small>
          )}
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => setFiltros(FILTROS_VAZIOS)}
            disabled={!filtrosAtivos}
          >
            Limpar filtros
          </button>
        </div>
      </section>

      {loading && !dados ? (
        <>
          <div className="skeleton-grid report-skeleton">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="skeleton-card" />
            ))}
          </div>
          <div className="skeleton-list" />
        </>
      ) : erro && !dados ? (
        <EmptyState
          icon="!"
          title="Indicadores indisponíveis"
          description={erro}
          action={
            <button type="button" className="btn btn-primary" onClick={() => setRecarregar((n) => n + 1)}>
              Tentar novamente
            </button>
          }
        />
      ) : dados ? (
        <div className={`report-body ${loading ? 'report-body-loading' : ''}`} aria-busy={loading}>
          <div className="stat-grid">
            <Kpi
              rotulo="Reservas no período"
              valor={formatarNumero(reservas.total)}
              detalhe={`${reservas.pendentes} aguardando decisão`}
              destaque
            />
            <Kpi
              rotulo="Taxa de aprovação"
              valor={reservas.taxa_aprovacao === null ? '—' : `${reservas.taxa_aprovacao.toLocaleString('pt-BR')}%`}
              detalhe={`${reservas.aprovadas} aprovadas · ${reservas.negadas} negadas`}
            />
            <Kpi
              rotulo="Km rodados"
              valor={formatarNumero(vistorias.km_rodados_total)}
              detalhe={`${vistorias.viagens_com_km} viagem(ns) com check-in e check-out`}
            />
            <Kpi
              rotulo="Frota disponível"
              valor={`${frota.disponiveis}/${frota.ativos}`}
              detalhe={
                frota.percentual_disponivel === null
                  ? 'Nenhum veículo ativo'
                  : `${frota.percentual_disponivel.toLocaleString('pt-BR')}% dos veículos ativos`
              }
            />
            <Kpi
              rotulo="Devoluções com atraso"
              valor={formatarNumero(reservas.devolucoes_com_atraso)}
              detalhe={`de ${reservas.devolucoes_registradas} devolução(ões) registradas`}
            />
          </div>

          {semMovimento && (
            <div className="report-empty">
              <EmptyState
                icon="▦"
                title="Nenhuma reserva ou vistoria encontrada"
                description="Frota e usuários abaixo mostram a situação atual."
              />
            </div>
          )}

          <h2 className="report-section-title">Reservas</h2>
          <div className="report-grid">
            <Painel titulo="Reservas por mês" subtitulo="Pela data de retirada" className="report-panel-wide">
              <ColunasMensais meses={reservas.por_mes} />
            </Painel>
            <Painel titulo="Reservas por status">
              <Rosca
                titulo="Reservas por status"
                centro="reservas"
                itens={reservas.por_status.map((s) => ({ ...s, cor: `var(--status-${s.valor})` }))}
              />
            </Painel>
            <Painel titulo="Reservas por turno">
              <Barras itens={reservas.por_turno} />
            </Painel>
            <Painel titulo="Veículos mais reservados">
              <Barras itens={reservas.top_veiculos} />
            </Painel>
            <Painel titulo="Solicitantes com mais reservas">
              <Barras itens={reservas.top_usuarios} />
            </Painel>
          </div>

          <h2 className="report-section-title">Frota</h2>
          <div className="report-grid">
            <Painel titulo="Situação atual da frota" subtitulo="Não depende do período">
              <Rosca
                titulo="Situação da frota"
                centro="veículos"
                itens={frota.por_status.map((s) => ({ ...s, cor: `var(--status-${s.valor})` }))}
              />
            </Painel>
            <Painel titulo="Km rodados por veículo" subtitulo="Check-out − check-in no período">
              <Barras
                itens={frota.uso_por_veiculo.map((v) => ({ rotulo: v.rotulo, total: v.km_rodados }))}
                unidade=" km"
                vazio="Nenhuma viagem com check-in e check-out no período."
              />
            </Painel>
            <Painel titulo="Uso por veículo" className="report-panel-wide">
              {frota.uso_por_veiculo.length === 0 ? (
                <p className="chart-empty">Nenhum veículo cadastrado.</p>
              ) : (
                <div className="table-scroll">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Veículo</th>
                        <th>Situação</th>
                        <th>Reservas aprovadas</th>
                        <th>Km rodados</th>
                      </tr>
                    </thead>
                    <tbody>
                      {frota.uso_por_veiculo.map((v) => (
                        <tr key={v.veiculo_id}>
                          <td>{v.rotulo}</td>
                          <td>
                            <span className={`chip chip-${v.status}`}>
                              {frota.por_status.find((s) => s.valor === v.status)?.rotulo || v.status}
                            </span>
                          </td>
                          <td>{formatarNumero(v.reservas)}</td>
                          <td>{formatarNumero(v.km_rodados)} km</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Painel>
          </div>

          <h2 className="report-section-title">Usuários, CNH e Termos</h2>
          <div className="stat-grid">
            <Kpi rotulo="Funcionários ativos" valor={formatarNumero(usuarios.funcionarios_ativos)} detalhe={`de ${usuarios.funcionarios} cadastrados`} />
            <Kpi rotulo="Funcionários inativos" valor={formatarNumero(usuarios.funcionarios_inativos)} />
            <Kpi rotulo="Primeiro acesso pendente" valor={formatarNumero(usuarios.primeiro_acesso_pendente)} />
            <Kpi rotulo="Administradores" valor={formatarNumero(usuarios.administradores)} />
          </div>
          <div className="report-grid">
            <Painel titulo="CNH dos funcionários" subtitulo="Situação atual">
              <Barras itens={comCores(usuarios.cnh_por_situacao, (v) => CORES_SITUACAO[v])} vazio="Nenhum funcionário cadastrado." />
            </Painel>
            <Painel titulo="Termo dos funcionários" subtitulo="Situação atual">
              <Barras itens={comCores(usuarios.termo_por_situacao, (v) => CORES_SITUACAO[v])} vazio="Nenhum funcionário cadastrado." />
            </Painel>
            <Painel titulo="CNHs enviadas no período">
              <Rosca
                titulo="CNHs enviadas no período"
                centro="CNHs"
                itens={comCores(usuarios.cnh_enviadas_periodo, (v) => CORES_SITUACAO[v === 'aprovado' ? 'aprovada' : v])}
              />
            </Painel>
            <Painel titulo="Termos enviados no período">
              <Rosca
                titulo="Termos enviados no período"
                centro="termos"
                itens={comCores(usuarios.termos_enviados_periodo, (v) => CORES_SITUACAO[v === 'aprovado' ? 'valido' : v])}
              />
            </Painel>
          </div>

          <h2 className="report-section-title">Vistorias</h2>
          <div className="stat-grid">
            <Kpi rotulo="Check-ins" valor={formatarNumero(vistorias.checkins)} />
            <Kpi rotulo="Check-outs" valor={formatarNumero(vistorias.checkouts)} />
            <Kpi rotulo="Com observações" valor={formatarNumero(vistorias.com_observacoes)} detalhe="Registros com observação escrita" />
            <Kpi rotulo="Com fotos" valor={formatarNumero(vistorias.com_fotos)} />
            <Kpi
              rotulo="Em andamento sem check-out"
              valor={formatarNumero(vistorias.em_andamento_sem_checkout)}
            />
          </div>
          <div className="report-grid">
            <Painel titulo="Vistorias por unidade">
              <Barras itens={vistorias.por_unidade} />
            </Painel>
          </div>

          <p className="muted-note report-footnote">
            Reservas entram no período pela data de retirada; vistorias pela data do registro; CNHs e Termos pela data de
            envio. A taxa de aprovação considera aprovadas, em andamento e concluídas sobre essas mais as negadas
            (pendentes e canceladas ficam fora). Km rodados = km do check-out − km do check-in da mesma reserva.
          </p>
        </div>
      ) : null}
    </div>
  )
}
