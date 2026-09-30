import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import api from '../services/api'
import EmptyState from '../components/EmptyState'
import UserFormModal from '../components/UserFormModal'
import ConfirmDialog from '../components/ConfirmDialog'
import { useFeedback } from '../context/FeedbackContext'
import { formatDate } from '../utils/format'

const ROTULOS_SITUACAO_CNH = {
  vencida: 'CNH vencida',
  proxima_vencimento: 'CNH próxima do vencimento',
  sem_cnh: 'sem CNH',
  rejeitada: 'CNH rejeitada',
  pendente: 'CNH em análise',
  aprovada: 'CNH aprovada',
}

const ROTULOS_SITUACAO_TERMO = {
  vencido: 'termo vencido',
  sem_termo: 'sem termo',
  rejeitado: 'termo rejeitado',
  pendente: 'termo em análise',
  valido: 'termo válido',
}

const CHIP_CNH = {
  proxima_vencimento: 'Próx. vencimento',
  pendente: 'Pendente',
  aprovada: 'Aprovada',
  vencida: 'Vencida',
  rejeitada: 'Rejeitada',
}

const CHIP_TERMO = {
  valido: 'Válido',
  pendente: 'Pendente',
  vencido: 'Vencido',
  rejeitado: 'Rejeitado',
}

function descreverFiltro(valor, rotulos) {
  return valor
    .split(',')
    .map((s) => rotulos[s.trim()] || s.trim())
    .join(' ou ')
}

export default function Usuarios() {
  const [searchParams, setSearchParams] = useSearchParams()
  const feedback = useFeedback()
  const [usuarios, setUsuarios] = useState([])
  const [totalUsuarios, setTotalUsuarios] = useState(0)
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)

  const [usuarioParaRemover, setUsuarioParaRemover] = useState(null)
  const [removendo, setRemovendo] = useState(false)
  const [mostrarInativos, setMostrarInativos] = useState(
    () => searchParams.get('incluir_inativos') === 'true'
  )

  const filtroCnh = searchParams.get('cnh_situacao') || ''
  const filtroTermo = searchParams.get('termo_situacao') || ''
  const filtroAtivo = searchParams.get('ativo') || ''
  const incluirInativosUrl = searchParams.get('incluir_inativos') === 'true'

  useEffect(() => {
    setMostrarInativos(incluirInativosUrl)
  }, [incluirInativosUrl])

  const filtrosAplicados = [
    filtroCnh && descreverFiltro(filtroCnh, ROTULOS_SITUACAO_CNH),
    filtroTermo && descreverFiltro(filtroTermo, ROTULOS_SITUACAO_TERMO),
    filtroAtivo === 'false' && 'contas inativas',
  ].filter(Boolean)

  async function load() {
    setLoading(true)

    try {
      const params = {}
      if (mostrarInativos) params.incluir_inativos = true
      if (filtroCnh) params.cnh_situacao = filtroCnh
      if (filtroTermo) params.termo_situacao = filtroTermo
      if (filtroAtivo) params.ativo = filtroAtivo
      const { data } = await api.get('/usuarios/', { params })
      const lista = data.results ?? data
      setUsuarios(lista)
      setTotalUsuarios(data.count ?? lista.length)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [mostrarInativos, filtroCnh, filtroTermo, filtroAtivo])

  function limparFiltros() {
    setSearchParams({}, { replace: true })
    setMostrarInativos(false)
  }

  async function handleToggleAtivo(usuario) {
    await api.patch(`/usuarios/${usuario.id}/`, {
      is_active: !usuario.is_active,
    })

    load()
  }

  function abrirConfirmacaoRemocao(usuario) {
    setUsuarioParaRemover(usuario)
  }

  function fecharConfirmacaoRemocao() {
    if (removendo) return

    setUsuarioParaRemover(null)
  }

  async function handleDelete() {
    if (!usuarioParaRemover) return

    setRemovendo(true)

    try {
      await api.delete(`/usuarios/${usuarioParaRemover.id}/`)
      feedback.sucesso(`Usuário ${usuarioParaRemover.nome} removido.`)
      setUsuarioParaRemover(null)
      await load()
    } catch (err) {
      const data = err.response?.data
      const msg =
        (typeof data?.detail === 'string' && data.detail) ||
        data?.non_field_errors?.[0] ||
        'Não foi possível remover o usuário. Tente novamente.'
      feedback.erro(msg)
    } finally {
      setRemovendo(false)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Usuários</h1>

        <button
          className="btn btn-primary"
          onClick={() => {
            setEditing(null)
            setShowForm(true)
          }}
        >
          + Novo usuário
        </button>
      </div>

      {(filtrosAplicados.length > 0 ||
        filtroAtivo !== 'false' ||
        (!loading && totalUsuarios > usuarios.length)) && (
        <div className="toolbar toolbar-inline">
          {filtrosAplicados.length > 0 && (
            <>
              <span className="muted-note">
                Filtro: <strong>{filtrosAplicados.join(' · ')}</strong>
              </span>
              <button type="button" className="btn btn-ghost btn-sm" onClick={limparFiltros}>
                Limpar filtro
              </button>
            </>
          )}
          {filtroAtivo !== 'false' && (
            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={mostrarInativos}
                onChange={(e) => setMostrarInativos(e.target.checked)}
              />
              <span>Mostrar inativos</span>
            </label>
          )}
          {!loading && totalUsuarios > usuarios.length && (
            <span className="muted-note">
              Exibindo {usuarios.length} de {totalUsuarios}
            </span>
          )}
        </div>
      )}

      {loading ? (
        <div className="skeleton-list" />
      ) : usuarios.length === 0 ? (
        <EmptyState
          icon="◉"
          title={
            filtrosAplicados.length > 0
              ? 'Nenhum usuário encontrado com este filtro'
              : 'Nenhum usuário cadastrado'
          }
        />
      ) : (
        <>
          <div className="table-desktop-only table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Matrícula</th>
                  <th>Setor</th>
                  <th>Perfil</th>
                  <th>CNH</th>
                  <th>Termo</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {usuarios.map((u) => (
                  <tr key={u.id}>
                    <td>{u.nome}</td>
                    <td>{u.matricula}</td>
                    <td>{u.setor || '—'}</td>
                    <td>{u.is_admin ? 'Administrador' : 'Funcionário'}</td>
                    <td>
                      {u.is_admin ? (
                        '—'
                      ) : (
                        <span
                          className={`chip ${
                            u.cnh?.situacao === 'aprovada'
                              ? 'chip-disponivel'
                              : u.cnh?.situacao === 'proxima_vencimento'
                                ? 'chip-manutencao'
                                : 'chip-inativo'
                          }`}
                        >
                          {CHIP_CNH[u.cnh?.situacao] || 'Sem CNH'}
                        </span>
                      )}
                      {!u.is_admin && u.cnh?.data_validade && (
                        <>
                          <br />
                          <small className="muted-note">
                            até {formatDate(u.cnh.data_validade)}
                          </small>
                        </>
                      )}
                    </td>
                    <td>
                      {u.is_admin
                        ? '—'
                        : CHIP_TERMO[u.termo?.situacao] || 'Sem termo'}
                    </td>
                    <td>
                      <button
                        className={`chip chip-toggle ${
                          u.is_active ? 'chip-disponivel' : 'chip-inativo'
                        }`}
                        onClick={() => handleToggleAtivo(u)}
                        type="button"
                      >
                        {u.is_active ? 'Ativo' : 'Inativo'}
                      </button>
                    </td>
                    <td className="table-actions">
                      <button
                        className="btn btn-ghost btn-sm"
                        type="button"
                        onClick={() => {
                          setEditing(u)
                          setShowForm(true)
                        }}
                      >
                        Editar
                      </button>
                      <button
                        className="btn btn-ghost-danger btn-sm"
                        type="button"
                        onClick={() => abrirConfirmacaoRemocao(u)}
                      >
                        Remover
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mobile-card-list">
            {usuarios.map((u) => (
              <article key={u.id} className="mobile-entity-card">
                <div className="mobile-entity-card-head">
                  <div>
                    <strong>{u.nome}</strong>
                    <p className="muted-note">
                      Matrícula {u.matricula}
                      {u.setor ? ` · ${u.setor}` : ''}
                    </p>
                  </div>
                  <span className={`chip ${u.is_active ? 'chip-disponivel' : 'chip-inativo'}`}>
                    {u.is_active ? 'Ativo' : 'Inativo'}
                  </span>
                </div>
                <p className="muted-note">
                  {u.is_admin ? 'Administrador' : 'Funcionário'}
                  {!u.is_admin && (
                    <>
                      {' · '}
                      CNH:{' '}
                      {CHIP_CNH[u.cnh?.situacao] || 'Sem CNH'}
                      {' · '}
                      Termo: {CHIP_TERMO[u.termo?.situacao] || 'Sem termo'}
                    </>
                  )}
                </p>
                <div className="reservation-actions">
                  <button
                    className="btn btn-ghost btn-touch"
                    type="button"
                    onClick={() => handleToggleAtivo(u)}
                  >
                    {u.is_active ? 'Desativar' : 'Ativar'}
                  </button>
                  <button
                    className="btn btn-ghost btn-touch"
                    type="button"
                    onClick={() => {
                      setEditing(u)
                      setShowForm(true)
                    }}
                  >
                    Editar
                  </button>
                  <button
                    className="btn btn-ghost-danger btn-touch"
                    type="button"
                    onClick={() => abrirConfirmacaoRemocao(u)}
                  >
                    Remover
                  </button>
                </div>
              </article>
            ))}
          </div>
        </>
      )}

      {showForm && (
        <UserFormModal
          usuario={editing}
          onClose={() =>
            setShowForm(false)
          }
          onSaved={() => {
            setShowForm(false)
            load()
          }}
        />
      )}

      {usuarioParaRemover && (
        <ConfirmDialog
          title="Remover usuário"
          message="A conta será desativada e poderá ser reativada depois."
          confirmLabel="Remover"
          loadingLabel="Removendo…"
          tone="danger"
          loading={removendo}
          onConfirm={handleDelete}
          onCancel={fecharConfirmacaoRemocao}
        >
          <div className="admin-note">
            <strong>
              {usuarioParaRemover.nome}
            </strong>

            <br />

            <span>
              Matrícula:{' '}
              {usuarioParaRemover.matricula}
            </span>

            <br />

            <span>
              Perfil:{' '}
              {usuarioParaRemover.is_admin
                ? 'Administrador'
                : 'Funcionário'}
            </span>
          </div>
        </ConfirmDialog>
      )}
    </div>
  )
}