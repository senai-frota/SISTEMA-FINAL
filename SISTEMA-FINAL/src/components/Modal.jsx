export default function Modal({ title, onClose, children, width = 480, mobileSheet = false }) {
  return (
    <div className="modal-overlay" onMouseDown={onClose}>
      <div
        className={`modal-panel${mobileSheet ? ' modal-panel-sheet' : ''}`}
        style={{ maxWidth: width }}
        onMouseDown={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className="modal-header">
          <h3>{title}</h3>
          <button className="icon-btn" onClick={onClose} aria-label="Fechar" type="button">
            ✕
          </button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  )
}
