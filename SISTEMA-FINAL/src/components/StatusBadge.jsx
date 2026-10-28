const LABELS = {
  disponivel: 'Disponível',
  em_uso: 'Em uso',
  manutencao: 'Em manutenção',
  inativo: 'Inativo',
  pendente: 'Pendente',
  aprovada: 'Aprovada',
  aprovado: 'Aprovado',
  negada: 'Rejeitada',
  rejeitada: 'Rejeitada',
  em_andamento: 'Em andamento',
  concluida: 'Concluída',
  cancelada: 'Cancelada',
  sem_cnh: 'Sem CNH',
  proxima_vencimento: 'Próxima do vencimento',
  vencida: 'Vencida',
}

export default function StatusBadge({ status }) {
  const label = LABELS[status] || status
  return (
    <span
      className="status-badge"
      style={{
        color: `var(--status-${status}, var(--senai-gray))`,
        background: `var(--status-${status}-bg, var(--senai-gray-lighter))`,
      }}
    >
      <span className="status-dot" />
      {label}
    </span>
  )
}
