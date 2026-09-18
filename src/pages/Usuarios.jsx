import { useEffect, useState } from 'react'
import api from '../services/api'
import EmptyState from '../components/EmptyState'
import UserFormModal from '../components/UserFormModal'
import Modal from '../components/Modal'

export default function Usuarios() {
  const [usuarios, setUsuarios] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)

  const [usuarioParaRemover, setUsuarioParaRemover] = useState(null)
  const [removendo, setRemovendo] = useState(false)

  async function load() {
    setLoading(true)

    try {
      const { data } = await api.get('/usuarios/')
      setUsuarios(data.results ?? data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

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
      setUsuarioParaRemover(null)
      await load()
    } catch (err) {
      const data = err.response?.data
      const msg =
        (typeof data?.detail === 'string' && data.detail) ||
        data?.non_field_errors?.[0] ||
        'Não foi possível remover o usuário. Tente novamente.'
      alert(msg)
    } finally {
      setRemovendo(false)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Usuários</h1>

          <p className="page-subtitle">
            Gerencie os funcionários com acesso ao sistema.
          </p>
        </div>

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

      {loading ? (
        <div className="skeleton-list" />
      ) : usuarios.length === 0 ? (
        <EmptyState
          icon="◉"
          title="Nenhum usuário cadastrado"
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
                  <th>Validade CNH</th>
                  <th>Termo / Conta</th>
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
                      <span
                        className={`chip ${
                          u.cnh?.situacao === 'aprovada'
                            ? 'chip-disponivel'
                            : u.cnh?.situacao === 'proxima_vencimento'
                              ? 'chip-manutencao'
                              : 'chip-inativo'
                        }`}
                      >
                        {u.cnh?.situacao === 'proxima_vencimento'
                          ? 'Próx. vencimento'
                          : u.cnh?.situacao === 'pendente'
                            ? 'Pendente'
                            : u.cnh?.situacao === 'aprovada'
                              ? 'Aprovada'
                              : u.cnh?.situacao === 'vencida'
                                ? 'Vencida'
                                : u.cnh?.situacao === 'rejeitada'
                                  ? 'Rejeitada'
                                  : 'Sem CNH'}
                      </span>
                    </td>
                    <td>
                      {u.cnh?.data_validade
                        ? new Date(u.cnh.data_validade).toLocaleDateString('pt-BR')
                        : '—'}
                    </td>
                    <td>
                      <span className={`chip ${u.is_active ? 'chip-disponivel' : 'chip-inativo'}`}>
                        {u.is_active ? 'Ativa' : 'Inativa'}
                      </span>
                      <br />
                      <small className="muted-note">
                        {u.termo?.situacao === 'valido'
                          ? 'Termo válido'
                          : u.termo?.situacao === 'pendente'
                            ? 'Termo pendente'
                            : u.termo?.situacao === 'vencido'
                              ? 'Termo vencido'
                              : u.termo?.situacao === 'rejeitado'
                                ? 'Termo rejeitado'
                                : 'Sem termo'}
                      </small>
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
                  {' · '}
                  CNH:{' '}
                  {u.cnh?.situacao === 'aprovada'
                    ? 'Aprovada'
                    : u.cnh?.situacao === 'pendente'
                      ? 'Pendente'
                      : u.cnh?.situacao || 'Sem CNH'}
                  {' · '}
                  {u.termo?.situacao === 'valido' ? 'Termo válido' : 'Termo pendente/vencido'}
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
        <Modal
          title="Remover usuário"
          onClose={fecharConfirmacaoRemocao}
          width={500}
        >
          <div className="form-grid">
            <p>
              Tem certeza que deseja remover este
              usuário?
            </p>

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

            <p className="muted-note">
              A conta será desativada (exclusão lógica). O histórico de
              reservas, termos e documentos permanece preservado.
            </p>

            <div className="modal-actions">
              <button
                type="button"
                className="btn btn-ghost"
                onClick={fecharConfirmacaoRemocao}
                disabled={removendo}
              >
                Cancelar
              </button>

              <button
                type="button"
                className="btn btn-ghost-danger"
                onClick={handleDelete}
                disabled={removendo}
              >
                {removendo
                  ? 'Removendo…'
                  : 'Remover usuário'}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}