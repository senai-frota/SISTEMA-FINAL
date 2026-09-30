import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react'
import ConfirmDialog from '../components/ConfirmDialog'

const FeedbackContext = createContext(null)

const MAX_TOASTS = 4

const DURACAO_PADRAO = {
  success: 4000,
  info: 5000,
  warning: 6000,
  error: 8000,
}

const ICONES = {
  success: '✓',
  info: 'i',
  warning: '!',
  error: '✕',
}

export function FeedbackProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const [dialogo, setDialogo] = useState(null)
  const proximoId = useRef(0)

  const fecharToast = useCallback((id) => {
    setToasts((lista) => lista.filter((t) => t.id !== id))
  }, [])

  const notificar = useCallback((tipo, mensagem, opcoes = {}) => {
    const id = ++proximoId.current
    setToasts((lista) => [
      ...lista,
      { id, tipo, mensagem, titulo: opcoes.titulo },
    ].slice(-MAX_TOASTS))
    const duracao = opcoes.duracao ?? DURACAO_PADRAO[tipo]
    if (duracao) setTimeout(() => fecharToast(id), duracao)
  }, [fecharToast])

  const confirmar = useCallback((opcoes) => new Promise((resolve) => {
    setDialogo({ ...opcoes, resolve })
  }), [])

  // Com `justificativa`, confirmar() resolve com o texto informado (ou null se cancelado).
  function responder(confirmado, texto) {
    if (dialogo?.justificativa) dialogo.resolve(confirmado ? texto : null)
    else dialogo?.resolve(confirmado)
    setDialogo(null)
  }

  const valor = useMemo(() => ({
    sucesso: (mensagem, opcoes) => notificar('success', mensagem, opcoes),
    erro: (mensagem, opcoes) => notificar('error', mensagem, opcoes),
    aviso: (mensagem, opcoes) => notificar('warning', mensagem, opcoes),
    info: (mensagem, opcoes) => notificar('info', mensagem, opcoes),
    confirmar,
  }), [notificar, confirmar])

  return (
    <FeedbackContext.Provider value={valor}>
      {children}

      {dialogo && (
        <ConfirmDialog
          title={dialogo.titulo}
          message={dialogo.mensagem}
          note={dialogo.nota}
          confirmLabel={dialogo.confirmar}
          cancelLabel={dialogo.cancelar}
          tone={dialogo.tom}
          requireReason={Boolean(dialogo.justificativa)}
          reasonLabel={dialogo.justificativa?.rotulo}
          reasonPlaceholder={dialogo.justificativa?.placeholder}
          initialReason={dialogo.justificativa?.inicial || ''}
          onConfirm={(texto) => responder(true, texto)}
          onCancel={() => responder(false)}
        />
      )}

      <div className="toast-region" aria-live="polite">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`toast toast-${t.tipo}`}
            role={t.tipo === 'error' ? 'alert' : 'status'}
          >
            <span className="toast-icon" aria-hidden="true">{ICONES[t.tipo]}</span>
            <div className="toast-content">
              {t.titulo && <strong>{t.titulo}</strong>}
              <p>{t.mensagem}</p>
            </div>
            <button
              type="button"
              className="toast-close"
              onClick={() => fecharToast(t.id)}
              aria-label="Fechar notificação"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </FeedbackContext.Provider>
  )
}

export function useFeedback() {
  const ctx = useContext(FeedbackContext)
  if (!ctx) throw new Error('useFeedback deve ser usado dentro de FeedbackProvider')
  return ctx
}
