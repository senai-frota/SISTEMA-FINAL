import { useEffect, useState } from 'react'
import api from '../services/api'
import StatusBadge from '../components/StatusBadge'
import EmptyState from '../components/EmptyState'
import { formatDateTime } from '../utils/format'

export default function Aprovacoes() {
  const [reservas, setReservas] = useState([])
  const [loading, setLoading] = useState(true)
  const [processando, setProcessando] = useState(null)
  const [observacoes, setObservacoes] = useState({})

  async function load() {
    setLoading(true)
    try {
      const { data } = await api.get('/reservas/', { params: { status: 'pendente' } })
      setReservas(data.results ?? data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function handleDecisao(reserva, status) {
    setProcessando(reserva.id)
    try {
      await api.patch(`/reservas/${reserva.id}/aprovar/`, {
        status,
        observacao_admin: observacoes[reserva.id] || '',
      })
      load()
    } finally {
      setProcessando(null)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Aprovações</h1>
          <p className="page-subtitle">Solicitações de reserva aguardando decisão.</p>
        </div>
      </div>

      {loading ? (
        <div className="skeleton-list" />
      ) : reservas.length === 0 ? (
        <EmptyState icon="✔" title="Tudo em dia" description="Não há solicitações pendentes no momento." />
      ) : (
        <div className="reservation-list">
          {reservas.map((r) => (
            <div key={r.id} className="reservation-card">
              <div className="reservation-card-main">
                <div>
                  <strong>{r.veiculo_info || `Veículo #${r.veiculo}`}</strong>
                  <p className="muted-note">
                    Solicitado por {r.usuario_nome || `usuário #${r.usuario}`}
                    {r.usuario_matricula ? ` · Matrícula ${r.usuario_matricula}` : ''}
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

              {r.pernoite && (
                <p className="muted-note">
                  Pernoite: SIM
                  {r.unidade_pernoite ? ` · ${r.unidade_pernoite}` : ''}
                </p>
              )}

              <p className="reservation-motivo">
                <strong>Motivo:</strong> {r.motivo}
              </p>
              <p className="muted-note">
                Destino: {r.destino || 'não informado'} · {r.passageiros} passageiro(s)
              </p>

              <label className="field">
                <span>Observação (opcional)</span>
                <input
                  value={observacoes[r.id] || ''}
                  onChange={(e) => setObservacoes((o) => ({ ...o, [r.id]: e.target.value }))}
                  placeholder="Ex.: Retire na garagem às 8h."
                />
              </label>

              <div className="reservation-actions">
                <button
                  className="btn btn-ghost-danger btn-sm"
                  disabled={processando === r.id}
                  onClick={() => handleDecisao(r, 'negada')}
                >
                  Negar
                </button>
                <button
                  className="btn btn-primary btn-sm"
                  disabled={processando === r.id}
                  onClick={() => handleDecisao(r, 'aprovada')}
                >
                  {processando === r.id ? 'Processando…' : 'Aprovar'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
