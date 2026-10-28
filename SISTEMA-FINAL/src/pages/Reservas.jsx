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

function antecipadoAprovado(reserva) {
  return reserva.checkin_antecipado?.status === 'aprovada'
}

function antecipadoPendente(reserva) {
  return reserva.checkin_antecipado?.status === 'pendente'
}

function podeExibirCheckin(reserva, userId) {
  if (reserva.status !== 'aprovada') return false
  if (String(reserva.usuario) !== String(userId)) return false
  if (!dentroJanelaOperacional()) return false
  const agora = new Date()
  const { inicioTol, fimTol } = limitesComTolerancia(reserva)
  if (agora > fimTol) return false
  if (agora < inicioTol && !antecipadoAprovado(reserva)) return false
  return true
}

function podeExibirCheckout(reserva, userId) {
  if (reserva.status !== 'em_andamento') return false
  if (String(reserva.usuario) !== String(userId)) return false
  const agora = new Date()
  const { inicioTol } = limitesComTolerancia(reserva)
  return agora >= inicioTol
}

function podeSolicitarAntecipado(reserva, userId) {
  if (reserva.status !== 'aprovada') return false
  if (String(reserva.usuario) !== String(userId)) return false
  if (antecipadoAprovado(reserva) || antecipadoPendente(reserva)) return false
  const agora = new Date()
  const { inicioTol, fimTol } = limitesComTolerancia(reserva)
  return agora < inicioTol && agora <= fimTol
}

function mensagemBloqueioCheckin(reserva, userId) {
  if (reserva.status !== 'aprovada') return null
  if (String(reserva.usuario) !== String(userId)) return null
  if (!dentroJanelaOperacional()) {
    return 'Check-in permitido apenas entre 06:00 e 22:00. A autorização antecipada não abre a operação noturna.'
  }
  const agora = new Date()
  const { inicioTol, fimTol } = limitesComTolerancia(reserva)
  if (agora > fimTol) {
    return `O prazo de check-in encerrou (${TOLERANCIA_RESERVA_MINUTOS} minutos após o fim da reserva).`
  }
  if (agora < inicioTol) {
    if (antecipadoPendente(reserva)) {
      return 'Solicitação de check-in antecipado aguardando decisão do administrador.'
    }
    if (antecipadoAprovado(reserva)) {
      return null
    }
    return `Check-in disponível a partir de ${TOLERANCIA_RESERVA_MINUTOS} minutos antes do horário de início. Você pode solicitar autorização antecipada ao administrador.`
  }
  return null
}

function mensagemBloqueioCheckout(reserva, userId) {
  if (reserva.status !== 'em_andamento') return null
  if (String(reserva.usuario) !== String(userId)) return null
  const agora = new Date()
  const { inicioTol, fimTol } = limitesComTolerancia(reserva)
  if (agora < inicioTol) {
    return `Check-out disponível a partir de ${TOLERANCIA_RESERVA_MINUTOS} minutos antes do horário de início da reserva.`
  }
  if (agora > fimTol || reserva.checkout_atrasado) {
    return 'O prazo previsto já passou. O check-out atrasado continua permitido (24 h), na mesma unidade do check-in.'
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
  const [antecipadoAlvo, setAntecipadoAlvo] = useState(null)
  const [, setTick] = useState(0)

  async function load() {
    setLoading(true)
    try {
      const params = {}
      if (statusFiltro) params.status = statusFiltro
      const { data } = await api.get('/reservas/', { params })
      setReservas(data.results ?? data)
    } catch (err) {
      setReservas([])
      feedback.erro(mensagemErroApi(err, 'Não foi possível carregar as reservas.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
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

  function podeAprovarOuRejeitar(reserva) {
    return isAdmin && reserva.status === 'pendente'
  }

  function podeCancelar(reserva) {
    if (!['pendente', 'aprovada'].includes(reserva.status)) return false
    if (isAdmin) {
      // Pendente: o admin usa Aprovar/Rejeitar. Cancelar vale para reserva já aprovada.
      return reserva.status === 'aprovada'
    }
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
          Check-in: ±{TOLERANCIA_RESERVA_MINUTOS} min, das 06:00 às 22:00 (antecipação só com
          autorização). Check-out atrasado permitido 24 h na unidade do check-in.
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
            const checkoutDisponivel = podeExibirCheckout(r, user?.id)
            const pedirAntecipado = podeSolicitarAntecipado(r, user?.id)
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
                      {r.unidade_checkin_display
                        ? ` · Check-in: ${r.unidade_checkin_display}`
                        : ''}
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
                  {r.data_devolucao_real && (
                    <div>
                      <small>Devolução real</small>
                      <span>{formatDateTime(r.data_devolucao_real)}</span>
                    </div>
                  )}
                </div>

                <p className="reservation-motivo">{r.motivo}</p>

                {r.cancelamento_automatico && (
                  <div className="admin-note form-error">
                    Cancelada automaticamente por falta de check-in obrigatório.
                    Pernoite em outra unidade não dispensa o check-in.
                  </div>
                )}
                {r.observacao_admin && (
                  <div className="admin-note">
                    <strong>Observação do administrador:</strong> {r.observacao_admin}
                  </div>
                )}
                {r.checkin_antecipado?.status === 'aprovada' && (
                  <div className="admin-note">
                    Check-in antecipado autorizado
                    {r.checkin_antecipado.admin_nome
                      ? ` por ${r.checkin_antecipado.admin_nome}`
                      : ''}
                    {r.checkin_antecipado.decidido_em
                      ? ` em ${formatDateTime(r.checkin_antecipado.decidido_em)}`
                      : ''}
                    . A autorização não altera o horário da reserva nem as regras de check-out.
                  </div>
                )}

                {bloqueioCheckin && <div className="admin-note">{bloqueioCheckin}</div>}
                {bloqueioCheckout && <div className="admin-note">{bloqueioCheckout}</div>}

                <div className="reservation-actions">
                  {podeAprovarOuRejeitar(r) && (
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
                  {pedirAntecipado && (
                    <button
                      className="btn btn-ghost btn-sm"
                      disabled={processando === r.id}
                      onClick={() => setAntecipadoAlvo(r)}
                    >
                      Solicitar check-in antecipado
                    </button>
                  )}
                  {checkoutDisponivel && (
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

      {antecipadoAlvo && (
        <ConfirmDialog
          title="Solicitar check-in antecipado"
          message="O administrador precisa autorizar o check-in antes dos 30 minutos. A autorização não muda o horário da reserva nem as regras de check-out."
          confirmLabel="Enviar solicitação"
          cancelLabel="Voltar"
          requireReason
          reasonPlaceholder="Por que o check-in precisa ser antecipado?"
          loading={processando === antecipadoAlvo.id}
          onConfirm={async (justificativa) => {
            setProcessando(antecipadoAlvo.id)
            try {
              await api.post(`/reservas/${antecipadoAlvo.id}/checkin-antecipado/`, {
                justificativa,
              })
              feedback.sucesso('Solicitação de check-in antecipado enviada.')
              setAntecipadoAlvo(null)
              await load()
            } catch (err) {
              feedback.erro(mensagemErroApi(err, 'Não foi possível enviar a solicitação.'))
            } finally {
              setProcessando(null)
            }
          }}
          onCancel={() => setAntecipadoAlvo(null)}
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
