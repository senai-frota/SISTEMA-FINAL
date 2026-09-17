import { useEffect, useState } from 'react'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import StatusBadge from '../components/StatusBadge'
import EmptyState from '../components/EmptyState'
import VistoriaModal from '../components/VistoriaModal'
import { formatDateTime } from '../utils/format'

export default function Reservas() {
  const { user, isAdmin } = useAuth()
  const [reservas, setReservas] = useState([])
  const [loading, setLoading] = useState(true)
  const [statusFiltro, setStatusFiltro] = useState('')
  const [vistoriaAlvo, setVistoriaAlvo] = useState(null) // { reserva, tipo }

  async function load() {
    setLoading(true)
    try {
      const params = {}
      if (statusFiltro) params.status = statusFiltro
      const { data } = await api.get('/reservas/', { params })
      setReservas(data.results ?? data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFiltro])

  async function handleCancelar(reserva) {
    if (!confirm('Cancelar esta reserva?')) return
    await api.delete(`/reservas/${reserva.id}/`)
    load()
  }

  async function handleCheckin(reserva) {
    setVistoriaAlvo({ reserva, tipo: 'checkin' })
  }

  async function handleCheckout(reserva) {
    setVistoriaAlvo({ reserva, tipo: 'checkout' })
  }
  function podeFazerVistoria(reserva) {
  return String(reserva.usuario) === String(user?.id)
}

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>{isAdmin ? 'Reservas' : 'Minhas reservas'}</h1>
          <p className="page-subtitle">Acompanhe solicitações, check-in e check-out.</p>
        </div>
      </div>

      <div className="toolbar">
        <select value={statusFiltro} onChange={(e) => setStatusFiltro(e.target.value)}>
          <option value="">Todos os status</option>
          <option value="pendente">Pendente</option>
          <option value="aprovada">Aprovada</option>
          <option value="negada">Negada</option>
          <option value="em_andamento">Em andamento</option>
          <option value="concluida">Concluída</option>
          <option value="cancelada">Cancelada</option>
        </select>
      </div>

      {loading ? (
        <div className="skeleton-list" />
      ) : reservas.length === 0 ? (
        <EmptyState
          icon="▤"
          title="Nenhuma reserva por aqui"
          description="Solicite um veículo na página de Veículos para começar."
        />
      ) : (
        <div className="reservation-list">
          {reservas.map((r) => (
            <div key={r.id} className="reservation-card">
              <div className="reservation-card-main">
                <div>
                  <strong>{r.veiculo_info || `Veículo #${r.veiculo}`}</strong>
                  <p className="muted-note">
                    {r.destino || 'Destino não informado'} · {r.passageiros} passageiro(s)
                  </p>
                </div>
                <StatusBadge status={r.status} />
              </div>

              <div className="reservation-dates">
                <div>
                  <small>Retirada</small>
                  <span>{formatDateTime(r.data_inicio)}</span>
                </div>
                <div>
                  <small>Devolução prevista</small>
                  <span>{formatDateTime(r.data_fim)}</span>
                </div>
              </div>

              <p className="reservation-motivo">{r.motivo}</p>

              {r.observacao_admin && (
                <div className="admin-note">
                  <strong>Observação do administrador:</strong> {r.observacao_admin}
                </div>
              )}

              <div className="reservation-actions">
                {r.status === 'pendente' && (
                  <button className="btn btn-ghost-danger btn-sm" onClick={() => handleCancelar(r)}>
                    Cancelar solicitação
                  </button>
                )}
                {r.status === 'aprovada' && podeFazerVistoria(r) && (
  <button className="btn btn-primary btn-sm" onClick={() => handleCheckin(r)}>
    Fazer check-in
  </button>
)}
                {r.status === 'em_andamento' && podeFazerVistoria(r) && (
  <button className="btn btn-primary btn-sm" onClick={() => handleCheckout(r)}>
    Fazer check-out
  </button>
)}
              </div>
            </div>
          ))}
        </div>
      )}

      {vistoriaAlvo && (
        <VistoriaModal
          reserva={vistoriaAlvo.reserva}
          tipo={vistoriaAlvo.tipo}
          onClose={() => setVistoriaAlvo(null)}
          onDone={() => {
            setVistoriaAlvo(null)
            load()
          }}
        />
      )}
    </div>
  )
}
