import { useEffect, useState } from 'react'
import api from '../services/api'
import EmptyState from '../components/EmptyState'
import UserFormModal from '../components/UserFormModal'
import Modal from '../components/Modal'
import StatusBadge from '../components/StatusBadge'
import { formatDate } from '../utils/format'

// Deriva o status "de exibição" do Termo de Responsabilidade para a coluna
// da tabela: um termo aprovado mas com a validade já vencida vira "vencido"
// (o backend só guarda status aprovado/pendente/rejeitado; o vencimento é
// calculado a partir de termo_dias_restantes).
function termoStatusExibicao(usuario) {
  if (!usuario.termo_status) return 'nao_enviado'
  if (
    usuario.termo_status === 'aprovado' &&
    usuario.termo_dias_restantes !== null &&
    usuario.termo_dias_restantes < 0
  ) {
    return 'vencido'
  }
  return usuario.termo_status
}

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
      await api.delete(
        `/usuarios/${usuarioParaRemover.id}/`
      )

      setUsuarioParaRemover(null)

      await load()
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
        <table className="data-table">
          <thead>
            <tr>
              <th>Nome</th>
              <th>Matrícula</th>
              <th>Setor</th>
              <th>Perfil</th>
              <th>Termo de Responsabilidade</th>
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

                <td>
                  {u.is_admin
                    ? 'Administrador'
                    : 'Funcionário'}
                </td>

                <td>
                  <StatusBadge status={termoStatusExibicao(u)} />

                  {u.termo_status === 'aprovado' && (
                    <div className="table-subtext">
                      {u.termo_dias_restantes >= 0
                        ? `Válido até ${formatDate(u.termo_validade)} (${u.termo_dias_restantes} dias)`
                        : `Venceu em ${formatDate(u.termo_validade)}`}
                    </div>
                  )}
                </td>

                <td>
                  <button
                    className={`chip chip-toggle ${
                      u.is_active
                        ? 'chip-disponivel'
                        : 'chip-inativo'
                    }`}
                    onClick={() =>
                      handleToggleAtivo(u)
                    }
                  >
                    {u.is_active
                      ? 'Ativo'
                      : 'Inativo'}
                  </button>
                </td>

                <td className="table-actions">
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => {
                      setEditing(u)
                      setShowForm(true)
                    }}
                  >
                    Editar
                  </button>

                  <button
                    className="btn btn-ghost-danger btn-sm"
                    onClick={() =>
                      abrirConfirmacaoRemocao(u)
                    }
                  >
                    Remover
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
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
              Esta ação não poderá ser desfeita.
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