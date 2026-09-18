import { useEffect, useState } from 'react'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import StatusBadge from '../components/StatusBadge'
import EmptyState from '../components/EmptyState'
import VistoriaModal from '../components/VistoriaModal'
import Modal from '../components/Modal'
import { formatDateTime } from '../utils/format'
import { isMobileClient } from '../utils/device'

function dentroJanelaOperacional(agora = new Date()) {
  const minutos = agora.getHours() * 60 + agora.getMinutes()
  return minutos >= 6 * 60 && minutos <= 22 * 60
}

function dentroIntervaloReserva(reserva, agora = new Date()) {
  const inicio = new Date(reserva.data_inicio)
  const fim = new Date(reserva.data_fim)
  return agora >= inicio && agora <= fim
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
  return true
}

function mensagemBloqueioCheckin(reserva, userId) {
  if (reserva.status !== 'aprovada') return null
  if (String(reserva.usuario) !== String(userId)) return null
  if (!dentroJanelaOperacional()) {
    return 'Check-in permitido apenas entre 06:00 e 22:00.'
  }
  const agora = new Date()
  if (agora < new Date(reserva.data_inicio)) {
    return 'Check-in disponível a partir do horário de início da reserva.'
  }
  if (agora > new Date(reserva.data_fim)) {
    return 'O horário da reserva já encerrou. Check-in não é mais permitido.'
  }
  return null
}

export default function Reservas() {
  const { user, isAdmin } = useAuth()
  const [reservas, setReservas] = useState([])
  const [loading, setLoading] = useState(true)
  const [statusFiltro, setStatusFiltro] = useState('')
  const [vistoriaAlvo, setVistoriaAlvo] = useState(null)
  const [processando, setProcessando] = useState(null)
  const [rejeitarAlvo, setRejeitarAlvo] = useState(null)
  const [observacao, setObservacao] = useState('')
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
    if (!confirm('Cancelar esta reserva? O registro permanecerá no histórico.')) return
    await api.delete(`/reservas/${reserva.id}/`)
    load()
  }

  async function handleDecisao(reserva, status, obs = '') {
    if (status === 'aprovada') {
      if (!confirm('Aprovar esta solicitação de reserva?')) return
    }
    setProcessando(reserva.id)
    try {
      await api.patch(`/reservas/${reserva.id}/aprovar/`, {
        status,
        observacao_admin: obs,
      })
      setRejeitarAlvo(null)
      setObservacao('')
      await load()
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.non_field_errors?.[0] ||
        'Não foi possível processar a decisão.'
      alert(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setProcessando(null)
    }
  }

  function abrirVistoria(reserva, tipo) {
    if (!isMobileClient()) {
      alert(
        `${tipo === 'checkin' ? 'Check-in' : 'Check-out'} só pode ser feito no celular ou tablet. ` +
          'Abra o sistema no dispositivo móvel para capturar as fotos.'
      )
      return
    }
    const msg =
      tipo === 'checkin'
        ? 'Iniciar check-in? Você precisará capturar 5 fotos com a câmera.'
        : 'Iniciar check-out? Você precisará capturar 5 fotos com a câmera.'
    if (!confirm(msg)) return
    setVistoriaAlvo({ reserva, tipo })
  }

  function podeCancelar(reserva) {
    if (!['pendente', 'aprovada'].includes(reserva.status)) return false
    if (isAdmin) return true
    return String(reserva.usuario) === String(user?.id)
  }

  function rotuloStatusReserva(r) {
    if (r.status === 'aprovada') return 'Aguardando check-in'
    if (r.status === 'em_andamento') return 'Em utilização (veículo em uso)'
    if (r.status === 'concluida') return 'Utilização encerrada'
    return null
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>{isAdmin ? 'Reservas' : 'Minhas reservas'}</h1>
          <p className="page-subtitle">
            {isAdmin
              ? 'Analise solicitações, aprove, rejeite ou acompanhe o histórico.'
              : 'Acompanhe suas solicitações, check-in e check-out.'}
          </p>
        </div>
      </div>

      <div className="toolbar">
        <select value={statusFiltro} onChange={(e) => setStatusFiltro(e.target.value)}>
          <option value="">Todos os status</option>
          <option value="pendente">Pendente</option>
          <option value="aprovada">Aprovada</option>
          <option value="negada">Rejeitada</option>
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
          description={
            isAdmin
              ? 'Não há reservas com o filtro selecionado.'
              : 'Solicite um veículo na página de Veículos para começar.'
          }
        />
      ) : (
        <div className="reservation-list">
          {reservas.map((r) => {
            const extra = rotuloStatusReserva(r)
            const bloqueioCheckin = mensagemBloqueioCheckin(r, user?.id)
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
                        : r.modalidade === 'horario'
                          ? ' · Horário personalizado'
                          : ''}
                    </p>
                    {extra && <p className="muted-note">{extra}</p>}
                    {r.pernoite && (
                      <p className="muted-note">
                        Pernoite: SIM
                        {r.unidade_pernoite ? ` · ${r.unidade_pernoite}` : ''}
                      </p>
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

                <div className="reservation-actions">
                  {r.status === 'pendente' && isAdmin && (
                    <>
                      <button
                        className="btn btn-ghost-danger btn-sm"
                        disabled={processando === r.id}
                        onClick={() => {
                          setObservacao('')
                          setRejeitarAlvo(r)
                        }}
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

                  {podeExibirCheckin(r, user?.id) && (
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
            setVistoriaAlvo(null)
            load()
          }}
        />
      )}

      {rejeitarAlvo && (
        <Modal title="Rejeitar solicitação" onClose={() => setRejeitarAlvo(null)} width={480}>
          <p className="muted-note">
            Informe o motivo da rejeição (opcional). A reserva permanecerá no histórico como rejeitada.
          </p>
          <label className="field">
            <span>Observação</span>
            <textarea
              rows={3}
              value={observacao}
              onChange={(e) => setObservacao(e.target.value)}
              placeholder="Motivo da rejeição"
              style={{ textTransform: 'uppercase' }}
            />
          </label>
          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={() => setRejeitarAlvo(null)}>
              Voltar
            </button>
            <button
              type="button"
              className="btn btn-ghost-danger"
              disabled={processando === rejeitarAlvo.id}
              onClick={() => handleDecisao(rejeitarAlvo, 'negada', observacao)}
            >
              Confirmar rejeição
            </button>
          </div>
        </Modal>
      )}
    </div>
  )
}
