import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import { useFeedback } from '../context/FeedbackContext'

const POLLING_MS = 25000

const ICONES = {
  checkin_proximo_cancelamento: '⏱',
  cancelamento_automatico: '✕',
  checkout_atrasado: '!',
  reserva_pendente: 'i',
  checkin_antecipado_pendente: 'i',
}

export default function AlertasOperacionais() {
  const { isAdmin, user } = useAuth()
  const feedback = useFeedback()
  const [dados, setDados] = useState(null)
  const [aberto, setAberto] = useState(false)
  const visto = useRef({ iniciado: false, pendentes: 0, ids: new Set() })

  useEffect(() => {
    if (!user) return undefined
    let cancelado = false

    async function carregar(silencioso) {
      try {
        const { data } = await api.get('/reservas/alertas-operacionais/')
        if (cancelado) return
        const ids = new Set([
          ...(data.criticos || []).map((i) => i.id),
          ...(data.comuns || []).map((i) => i.id),
        ])
        const pendentes = data.contagens?.reservas_pendentes || 0
        if (!visto.current.iniciado) {
          visto.current = { iniciado: true, pendentes, ids }
        } else if (isAdmin) {
          const novosComuns = (data.comuns || []).filter((i) => !visto.current.ids.has(i.id))
          if (pendentes > visto.current.pendentes) {
            feedback.info('Nova solicitação de reserva recebida.', {
              chave: 'nova-reserva',
              titulo: 'Solicitação',
            })
          } else if (novosComuns.some((i) => i.tipo === 'checkin_antecipado_pendente')) {
            feedback.info('Nova solicitação de check-in antecipado.', {
              chave: 'checkin-antecipado',
              titulo: 'Autorização',
            })
          }
          visto.current = { iniciado: true, pendentes, ids }
        }
        setDados(data)
      } catch {
        if (!silencioso && !cancelado) setDados(null)
      }
    }

    carregar(true)
    const id = setInterval(() => carregar(true), POLLING_MS)
    return () => {
      cancelado = true
      clearInterval(id)
    }
  }, [user, isAdmin, feedback])

  if (!dados) return null

  const criticos = dados.criticos || []
  const comuns = dados.comuns || []
  const total = criticos.length + comuns.length
  if (total === 0) return null

  const badge = criticos.length || comuns.length

  return (
    <div className="ops-alerts">
      <button
        type="button"
        className={`ops-alerts-toggle ${criticos.length ? 'ops-alerts-toggle-critical' : ''}`}
        onClick={() => setAberto((v) => !v)}
        aria-expanded={aberto}
        aria-controls="ops-alerts-panel"
      >
        <span className="ops-alerts-icon" aria-hidden="true">
          {criticos.length ? '!' : 'i'}
        </span>
        <span>
          {criticos.length
            ? `${criticos.length} alerta(s) crítico(s)`
            : `${comuns.length} aviso(s)`}
        </span>
        <span className="ops-alerts-count" aria-label={`${badge} pendências`}>
          {badge}
        </span>
      </button>

      {aberto && (
        <div id="ops-alerts-panel" className="ops-alerts-panel">
          {criticos.length > 0 && (
            <section className="ops-alerts-group">
              <h3>Alertas críticos</h3>
              <ul>
                {criticos.map((item) => (
                  <li key={item.id} className="ops-alert-item ops-alert-critical">
                    <span className="ops-alert-mark" aria-hidden="true">
                      {ICONES[item.tipo] || '!'}
                    </span>
                    <div>
                      <strong>{item.titulo}</strong>
                      <p>{item.mensagem}</p>
                      <small>
                        {item.veiculo_placa} · {item.usuario_nome} · {item.acao}
                      </small>
                      <Link to={item.para} className="link" onClick={() => setAberto(false)}>
                        Abrir reserva #{item.reserva_id}
                      </Link>
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}
          {comuns.length > 0 && (
            <section className="ops-alerts-group">
              <h3>Avisos</h3>
              <ul>
                {comuns.map((item) => (
                  <li key={item.id} className="ops-alert-item ops-alert-common">
                    <span className="ops-alert-mark" aria-hidden="true">
                      {ICONES[item.tipo] || 'i'}
                    </span>
                    <div>
                      <strong>{item.titulo}</strong>
                      <p>{item.mensagem}</p>
                      <Link to={item.para} className="link" onClick={() => setAberto(false)}>
                        Ver
                      </Link>
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </div>
  )
}
