export default function VehiclePlaceholder({ texto = 'Sem imagem' }) {
  return (
    <div className="vehicle-placeholder" role="img" aria-label={texto}>
      <svg viewBox="0 0 64 40" aria-hidden="true">
        <path
          d="M8 28V21l6-9a4 4 0 0 1 3.3-1.8h21.4a4 4 0 0 1 3 1.4L50 20h4a4 4 0 0 1 4 4v4"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        <path d="M4 28h56" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
        <path d="M17 20h29" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.6" />
        <circle cx="18" cy="29" r="5" fill="var(--color-surface-alt)" stroke="currentColor" strokeWidth="2.5" />
        <circle cx="47" cy="29" r="5" fill="var(--color-surface-alt)" stroke="currentColor" strokeWidth="2.5" />
      </svg>
      <small>{texto}</small>
    </div>
  )
}
