import { useEffect, useState } from 'react'
import api from '../services/api'
import EmptyState from '../components/EmptyState'
import { formatDateTime } from '../utils/format'
import { mensagemErroApi } from '../utils/erros'
import { useFeedback } from '../context/FeedbackContext'

export default function Aprovacoes() {
  const feedback = useFeedback()
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
    let observacao = observacoes[reserva.id] || ''
    if (status === 'negada') {
      const justificativa = await feedback.confirmar({
        titulo: 'Negar solicitação',
        mensagem: `Negar a reserva de ${reserva.usuario_nome || 'usuário'}? O solicitante verá a justificativa.`,
        confirmar: 'Negar',
        cancelar: 'Voltar',
        tom: 'danger',
        justificativa: { placeholder: 'Motivo da negação', inicial: observacao },
      })
      if (!justificativa) return
      observacao = justificativa
    }
    setProcessando(reserva.id)
    try {
      await api.patch(`/reservas/${reserva.id}/aprovar/`, {
        status,
        observacao_admin: observacao,
      })
      feedback.sucesso(status === 'aprovada' ? 'Reserva aprovada.' : 'Reserva negada.')
      load()
    } catch (err) {
      feedback.erro(mensagemErroApi(err, 'Não foi possível processar a decisão.'))
    } finally {
      setProcessando(null)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>
          Aprovações
          {!loading && reservas.length > 0 && (
            <span className="page-count">
              {reservas.length} pendente{reservas.length !== 1 ? 's' : ''}
            </span>
          )}
        </h1>
      </div>

      {loading ? (
        <div className="skeleton-list" />
      ) : reservas.length === 0 ? (
        <EmptyState icon="✔" title="Nenhuma solicitação pendente" />
      ) : (
        <div className="reservation-list">
          {reservas.map((r) => (
            <div key={r.id} className="reservation-card">
              <div className="reservation-card-main">
                <div>
                  <strong>{r.veiculo_info || `Veículo #${r.veiculo}`}</strong>
                  <p className="muted-note">
                    {r.usuario_nome || `Usuário #${r.usuario}`}
                    {r.usuario_matricula ? ` · Matrícula ${r.usuario_matricula}` : ''}
                  </p>
                </div>
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
                {r.pernoite &&
                  ` · Pernoite${r.unidade_pernoite ? `: ${r.unidade_pernoite}` : ''}`}
              </p>

              <div className="reservation-decision">
                <input
                  type="text"
                  aria-label="Observação para o solicitante"
                  value={observacoes[r.id] || ''}
                  onChange={(e) => setObservacoes((o) => ({ ...o, [r.id]: e.target.value }))}
                  placeholder="Observação (opcional)"
                />
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
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
