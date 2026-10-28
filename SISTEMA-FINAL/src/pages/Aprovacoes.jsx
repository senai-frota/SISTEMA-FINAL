import { useEffect, useState } from 'react'
import api from '../services/api'
import EmptyState from '../components/EmptyState'
import { formatDateTime } from '../utils/format'
import { mensagemErroApi } from '../utils/erros'
import { useFeedback } from '../context/FeedbackContext'

export default function Aprovacoes() {
  const feedback = useFeedback()
  const [reservas, setReservas] = useState([])
  const [antecipados, setAntecipados] = useState([])
  const [loading, setLoading] = useState(true)
  const [processando, setProcessando] = useState(null)
  const [observacoes, setObservacoes] = useState({})

  async function load(silencioso = false) {
    if (!silencioso) setLoading(true)
    try {
      const [reservasRes, antecipadosRes] = await Promise.all([
        api.get('/reservas/', { params: { status: 'pendente' } }),
        api.get('/reservas/autorizacoes-checkin/', { params: { status: 'pendente' } }),
      ])
      setReservas(reservasRes.data.results ?? reservasRes.data)
      setAntecipados(antecipadosRes.data.results ?? antecipadosRes.data)
    } catch (err) {
      if (!silencioso) {
        setReservas([])
        setAntecipados([])
        feedback.erro(mensagemErroApi(err, 'Não foi possível carregar as aprovações.'))
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const id = setInterval(() => load(true), 25000)
    return () => clearInterval(id)
  }, [])

  async function decidirAntecipado(item, status) {
    let observacao = ''
    if (status === 'rejeitada') {
      const justificativa = await feedback.confirmar({
        titulo: 'Rejeitar check-in antecipado',
        mensagem: `Rejeitar o pedido de ${item.solicitante_nome || 'usuário'}?`,
        confirmar: 'Rejeitar',
        cancelar: 'Voltar',
        tom: 'danger',
        justificativa: { placeholder: 'Motivo da rejeição' },
      })
      if (!justificativa) return
      observacao = justificativa
    } else {
      const confirmado = await feedback.confirmar({
        titulo: 'Autorizar check-in antecipado',
        mensagem: 'A autorização libera só a restrição de 30 minutos. Check-out e horário da reserva não mudam.',
        confirmar: 'Autorizar',
      })
      if (!confirmado) return
    }
    setProcessando(`ant-${item.id}`)
    try {
      await api.patch(`/reservas/autorizacoes-checkin/${item.id}/`, {
        status,
        observacao_admin: observacao,
      })
      feedback.sucesso(status === 'aprovada' ? 'Check-in antecipado autorizado.' : 'Pedido rejeitado.')
      await load()
    } catch (err) {
      feedback.erro(mensagemErroApi(err, 'Não foi possível registrar a decisão.'))
    } finally {
      setProcessando(null)
    }
  }

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
          {!loading && (reservas.length + antecipados.length) > 0 && (
            <span className="page-count">
              {reservas.length + antecipados.length} pendente
              {reservas.length + antecipados.length !== 1 ? 's' : ''}
            </span>
          )}
        </h1>
      </div>

      {!loading && antecipados.length > 0 && (
        <section className="panel" style={{ marginBottom: 16 }}>
          <div className="panel-header">
            <h2>Check-in antecipado</h2>
          </div>
          <div className="reservation-list">
            {antecipados.map((item) => {
              const r = item.reserva_info || {}
              return (
                <div key={item.id} className="reservation-card">
                  <div className="reservation-card-main">
                    <div>
                      <strong>{r.veiculo_info || `Reserva #${item.reserva}`}</strong>
                      <p className="muted-note">
                        {item.solicitante_nome} · Pedido em {formatDateTime(item.criado_em)}
                      </p>
                    </div>
                  </div>
                  <p className="reservation-motivo">
                    <strong>Justificativa:</strong> {item.justificativa}
                  </p>
                  <div className="reservation-actions">
                    <button
                      className="btn btn-ghost-danger btn-sm"
                      disabled={processando === `ant-${item.id}`}
                      onClick={() => decidirAntecipado(item, 'rejeitada')}
                    >
                      Rejeitar
                    </button>
                    <button
                      className="btn btn-primary btn-sm"
                      disabled={processando === `ant-${item.id}`}
                      onClick={() => decidirAntecipado(item, 'aprovada')}
                    >
                      Autorizar
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {loading ? (
        <div className="skeleton-list" />
      ) : reservas.length === 0 ? (
        <EmptyState
          icon="✔"
          title={antecipados.length ? 'Nenhuma reserva pendente' : 'Nenhuma solicitação pendente'}
        />
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
