import { useEffect, useState } from 'react'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import { useFeedback } from '../context/FeedbackContext'
import StatusBadge from '../components/StatusBadge'
import EmptyState from '../components/EmptyState'
import VistoriaModal from '../components/VistoriaModal'
import ConfirmDialog from '../components/ConfirmDialog'
import { formatDateTime } from '../utils/format'
import { mensagemErroApi } from '../utils/erros'
import { isMobileClient } from '../utils/device'

/** Tolerância de check-in/check-out (± minutos) — espelha o backend. */
export const TOLERANCIA_RESERVA_MINUTOS = 30

function dentroJanelaOperacional(agora = new Date()) {
  const minutos = agora.getHours() * 60 + agora.getMinutes()
  return minutos >= 6 * 60 && minutos <= 22 * 60
}

function limitesComTolerancia(reserva) {
  const inicio = new Date(reserva.data_inicio)
  const fim = new Date(reserva.data_fim)
  const tolMs = TOLERANCIA_RESERVA_MINUTOS * 60 * 1000
  return {
    inicioTol: new Date(inicio.getTime() - tolMs),
    fimTol: new Date(fim.getTime() + tolMs),
  }
}

function dentroIntervaloReserva(reserva, agora = new Date()) {
  const { inicioTol, fimTol } = limitesComTolerancia(reserva)
  return agora >= inicioTol && agora <= fimTol
}

function podeExibirCheckin(reserva, userId) {
  if (reserva.status !== 'aprovada') return false
  if (String(reserva.usuario) !== String(userId)) return false
  if (!dentroJanelaOperacional()) return false
  if (!dentroIntervaloReserva(reserva)) return false
  return true
}

function podeExibirCheckout(reserva, userId) {
  if (reserva.status !== 'em_andamento') return false
  if (String(reserva.usuario) !== String(userId)) return false
  if (!dentroJanelaOperacional()) return false
  if (!dentroIntervaloReserva(reserva)) return false
  return true
}

function mensagemBloqueioCheckin(reserva, userId) {
  if (reserva.status !== 'aprovada') return null
  if (String(reserva.usuario) !== String(userId)) return null
  if (!dentroJanelaOperacional()) {
    return 'Check-in permitido apenas entre 06:00 e 22:00.'
  }
  const agora = new Date()
  const { inicioTol, fimTol } = limitesComTolerancia(reserva)
  if (agora < inicioTol) {
    return `Check-in disponível a partir de ${TOLERANCIA_RESERVA_MINUTOS} minutos antes do horário de início da reserva.`
  }
  if (agora > fimTol) {
    return `O prazo de check-in encerrou (${TOLERANCIA_RESERVA_MINUTOS} minutos após o fim da reserva).`
  }
  return null
}

function mensagemBloqueioCheckout(reserva, userId) {
  if (reserva.status !== 'em_andamento') return null
  if (String(reserva.usuario) !== String(userId)) return null
  if (!dentroJanelaOperacional()) {
    return 'Check-out permitido apenas entre 06:00 e 22:00.'
  }
  const agora = new Date()
  const { inicioTol, fimTol } = limitesComTolerancia(reserva)
  if (agora < inicioTol) {
    return `Check-out disponível a partir de ${TOLERANCIA_RESERVA_MINUTOS} minutos antes do horário de início da reserva.`
  }
  if (agora > fimTol) {
    return `O prazo de check-out encerrou (${TOLERANCIA_RESERVA_MINUTOS} minutos após o fim da reserva).`
  }
  return null
}

export default function Reservas() {
  const { user, isAdmin } = useAuth()
  const feedback = useFeedback()
  const [reservas, setReservas] = useState([])
  const [loading, setLoading] = useState(true)
  const [statusFiltro, setStatusFiltro] = useState('')
  const [vistoriaAlvo, setVistoriaAlvo] = useState(null)
  const [processando, setProcessando] = useState(null)
  const [rejeitarAlvo, setRejeitarAlvo] = useState(null)
  const [, setTick] = useState(0)

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

  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 30000)
    return () => clearInterval(id)
  }, [])

  async function handleCancelar(reserva) {
    const deOutroUsuario = String(reserva.usuario) !== String(user?.id)
    const resposta = await feedback.confirmar({
      titulo: 'Cancelar reserva',
      mensagem: deOutroUsuario
        ? `Cancelar a reserva de ${reserva.usuario_nome || 'outro usuário'}? O registro permanecerá no histórico e o solicitante verá a justificativa.`
        : 'Cancelar esta reserva? O registro permanecerá no histórico.',
      confirmar: 'Cancelar reserva',
      cancelar: 'Voltar',
      tom: 'danger',
      justificativa: deOutroUsuario ? { placeholder: 'Motivo do cancelamento' } : undefined,
    })
    if (!resposta) return
    try {
      await api.delete(
        `/reservas/${reserva.id}/`,
        deOutroUsuario ? { data: { justificativa: resposta } } : undefined
      )
      feedback.sucesso('Reserva cancelada.')
    } catch (err) {
      feedback.erro(mensagemErroApi(err, 'Não foi possível cancelar a reserva.'))
    }
    load()
  }

  async function handleDecisao(reserva, status, obs = '') {
    if (status === 'aprovada') {
      const confirmado = await feedback.confirmar({
        titulo: 'Aprovar reserva',
        mensagem: 'Aprovar esta solicitação de reserva?',
        confirmar: 'Aprovar',
      })
      if (!confirmado) return
    }
    setProcessando(reserva.id)
    try {
      await api.patch(`/reservas/${reserva.id}/aprovar/`, {
        status,
        observacao_admin: obs,
      })
      setRejeitarAlvo(null)
      feedback.sucesso(status === 'aprovada' ? 'Reserva aprovada.' : 'Reserva negada.')
      await load()
    } catch (err) {
      feedback.erro(mensagemErroApi(err, 'Não foi possível processar a decisão.'))
    } finally {
      setProcessando(null)
    }
  }

  async function abrirVistoria(reserva, tipo) {
    const rotulo = tipo === 'checkin' ? 'Check-in' : 'Check-out'
    if (!isMobileClient()) {
      feedback.aviso(
        `${rotulo} só pode ser feito no celular ou tablet. ` +
          'Abra o sistema no dispositivo móvel para capturar as fotos.'
      )
      return
    }
    const confirmado = await feedback.confirmar({
      titulo: `Iniciar ${rotulo.toLowerCase()}`,
      mensagem: `Iniciar ${rotulo.toLowerCase()}? Você precisará capturar 5 fotos com a câmera.`,
      confirmar: `Iniciar ${rotulo.toLowerCase()}`,
    })
    if (!confirmado) return
    setVistoriaAlvo({ reserva, tipo })
  }

  function podeCancelar(reserva) {
    if (!['pendente', 'aprovada'].includes(reserva.status)) return false
    if (isAdmin) return true
    return String(reserva.usuario) === String(user?.id)
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>{isAdmin ? 'Reservas' : 'Minhas reservas'}</h1>
      </div>

      <div className="toolbar toolbar-inline">
        <select
          aria-label="Filtrar por status"
          value={statusFiltro}
          onChange={(e) => setStatusFiltro(e.target.value)}
        >
          <option value="">Todos os status</option>
          <option value="pendente">Pendente</option>
          <option value="aprovada">Aprovada</option>
          <option value="negada">Rejeitada</option>
          <option value="em_andamento">Em andamento</option>
          <option value="concluida">Concluída</option>
          <option value="cancelada">Cancelada</option>
        </select>
        <span className="muted-note">
          Check-in/check-out: ±{TOLERANCIA_RESERVA_MINUTOS} min do horário previsto, das 06:00 às
          22:00.
        </span>
      </div>

      {loading ? (
        <div className="skeleton-list" />
      ) : reservas.length === 0 ? (
        <EmptyState
          icon="▤"
          title="Nenhuma reserva encontrada"
          description={isAdmin || statusFiltro ? undefined : 'Reserve um veículo na página Veículos.'}
        />
      ) : (
        <div className="reservation-list">
          {reservas.map((r) => {
            const bloqueioCheckin = mensagemBloqueioCheckin(r, user?.id)
            const bloqueioCheckout = mensagemBloqueioCheckout(r, user?.id)
            const checkinDisponivel = podeExibirCheckin(r, user?.id)
            return (
              <div key={r.id} className="reservation-card">
                <div className="reservation-card-main">
                  <div>
                    <strong>{r.veiculo_info || `Veículo #${r.veiculo}`}</strong>
                    <p className="muted-note">
                      {isAdmin && (r.usuario_nome || r.usuario)
                        ? `Solicitante: ${r.usuario_nome || `#${r.usuario}`} · `
                        : ''}
                      {r.destino || 'Destino não informado'} · {r.passageiros} passageiro(s)
                      {r.modalidade === 'turno' && r.turno_display
                        ? ` · Turno: ${r.turno_display}`
                        : ''}
                      {r.pernoite &&
                        ` · Pernoite${r.unidade_pernoite ? `: ${r.unidade_pernoite}` : ''}`}
                    </p>
                    {r.status === 'aprovada' && !checkinDisponivel && !bloqueioCheckin && (
                      <p className="muted-note">Aguardando check-in</p>
                    )}
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

                {bloqueioCheckin && <div className="admin-note">{bloqueioCheckin}</div>}
                {bloqueioCheckout && <div className="admin-note">{bloqueioCheckout}</div>}

                <div className="reservation-actions">
                  {r.status === 'pendente' && isAdmin && (
                    <>
                      <button
                        className="btn btn-ghost-danger btn-sm"
                        disabled={processando === r.id}
                        onClick={() => setRejeitarAlvo(r)}
                      >
                        Rejeitar
                      </button>
                      <button
                        className="btn btn-primary btn-sm"
                        disabled={processando === r.id}
                        onClick={() => handleDecisao(r, 'aprovada')}
                      >
                        {processando === r.id ? 'Processando…' : 'Aprovar'}
                      </button>
                    </>
                  )}

                  {podeCancelar(r) && (
                    <button
                      className="btn btn-ghost-danger btn-sm"
                      onClick={() => handleCancelar(r)}
                    >
                      Cancelar
                    </button>
                  )}

                  {checkinDisponivel && (
                    <button
                      className="btn btn-primary btn-touch"
                      onClick={() => abrirVistoria(r, 'checkin')}
                    >
                      Fazer check-in
                    </button>
                  )}
                  {podeExibirCheckout(r, user?.id) && (
                    <button
                      className="btn btn-primary btn-touch"
                      onClick={() => abrirVistoria(r, 'checkout')}
                    >
                      Fazer check-out
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {vistoriaAlvo && (
        <VistoriaModal
          reserva={vistoriaAlvo.reserva}
          tipo={vistoriaAlvo.tipo}
          onClose={() => setVistoriaAlvo(null)}
          onDone={() => {
            feedback.sucesso(
              vistoriaAlvo.tipo === 'checkin'
                ? 'Check-in registrado. O veículo está em uso.'
                : 'Check-out registrado. A utilização foi encerrada.'
            )
            setVistoriaAlvo(null)
            load()
          }}
        />
      )}

      {rejeitarAlvo && (
        <ConfirmDialog
          title="Rejeitar solicitação"
          message="A reserva fica no histórico como rejeitada e o solicitante verá a justificativa."
          confirmLabel="Rejeitar"
          cancelLabel="Voltar"
          tone="danger"
          requireReason
          reasonPlaceholder="Motivo da rejeição"
          loading={processando === rejeitarAlvo.id}
          onConfirm={(motivo) => handleDecisao(rejeitarAlvo, 'negada', motivo)}
          onCancel={() => setRejeitarAlvo(null)}
        />
      )}
    </div>
  )
}
