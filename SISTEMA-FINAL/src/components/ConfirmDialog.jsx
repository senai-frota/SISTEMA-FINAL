import { useEffect, useRef, useState } from 'react'
import Modal from './Modal'

export const MSG_JUSTIFICATIVA_OBRIGATORIA = 'Informe a justificativa da recusa.'

export default function ConfirmDialog({
  title,
  message,
  children,
  note,
  confirmLabel = 'Confirmar',
  cancelLabel = 'Cancelar',
  loadingLabel = 'Processando…',
  tone = 'primary',
  loading = false,
  requireReason = false,
  reasonLabel = 'Justificativa (obrigatória)',
  reasonPlaceholder = 'Explique o motivo para o usuário',
  initialReason = '',
  onConfirm,
  onCancel,
}) {
  const cancelRef = useRef(null)
  const confirmRef = useRef(null)
  const reasonRef = useRef(null)
  const [motivo, setMotivo] = useState(initialReason)
  const [erroMotivo, setErroMotivo] = useState('')

  function cancelar() {
    if (!loading) onCancel()
  }

  function confirmar() {
    if (!requireReason) {
      onConfirm()
      return
    }
    const texto = motivo.trim()
    if (!texto) {
      setErroMotivo(MSG_JUSTIFICATIVA_OBRIGATORIA)
      reasonRef.current?.focus()
      return
    }
    onConfirm(texto)
  }

  useEffect(() => {
    // Em ações destrutivas o foco inicial fica em "Cancelar" para evitar confirmação acidental.
    const alvo = requireReason
      ? reasonRef.current
      : tone === 'danger' ? cancelRef.current : confirmRef.current
    alvo?.focus()
  }, [tone, requireReason])

  useEffect(() => {
    function onKeyDown(e) {
      if (e.key === 'Escape') cancelar()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  })

  return (
    <Modal title={title} onClose={cancelar} width={500}>
      <div className="form-grid confirm-dialog">
        {message && <p className="confirm-dialog-message">{message}</p>}

        {children}

        {requireReason && (
          <label className="field">
            <span>{reasonLabel}</span>
            <textarea
              ref={reasonRef}
              rows={3}
              value={motivo}
              onChange={(e) => {
                setMotivo(e.target.value)
                if (erroMotivo) setErroMotivo('')
              }}
              placeholder={reasonPlaceholder}
              aria-invalid={Boolean(erroMotivo)}
              disabled={loading}
            />
            {erroMotivo && <small className="field-error">{erroMotivo}</small>}
          </label>
        )}

        {note && <p className="muted-note">{note}</p>}

        <div className="modal-actions">
          <button
            ref={cancelRef}
            type="button"
            className="btn btn-ghost"
            onClick={cancelar}
            disabled={loading}
          >
            {cancelLabel}
          </button>

          <button
            ref={confirmRef}
            type="button"
            className={tone === 'danger' ? 'btn btn-ghost-danger' : 'btn btn-primary'}
            onClick={confirmar}
            disabled={loading}
          >
            {loading ? loadingLabel : confirmLabel}
          </button>
        </div>
      </div>
    </Modal>
  )
}
