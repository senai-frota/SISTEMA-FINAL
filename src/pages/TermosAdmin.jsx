import { useEffect, useState } from 'react'
import api from '../services/api'
import EmptyState from '../components/EmptyState'
import Modal from '../components/Modal'
import { formatDate } from '../utils/format'

const ENTIDADE_LABELS = {
  FIBRA: 'FIBRA',
  SESI: 'SESI',
  SENAI: 'SENAI',
  IEL: 'IEL',
}

export default function TermosAdmin() {
  const [termos, setTermos] = useState([])
  const [loading, setLoading] = useState(true)
  const [processando, setProcessando] = useState(null)
  const [observacoes, setObservacoes] = useState({})
  const [termoRejeitar, setTermoRejeitar] = useState(null)

  async function load() {
    setLoading(true)
    try {
      const { data } = await api.get('/termos/', { params: { status: 'pendente' } })
      setTermos(data.results ?? data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function handleDecisao(termo, status) {
    setProcessando(termo.id)
    try {
      await api.patch(`/termos/${termo.id}/decisao/`, {
        status,
        observacao_admin: observacoes[termo.id] || '',
      })
      setTermoRejeitar(null)
      await load()
    } finally {
      setProcessando(null)
    }
  }

  function abrirPdf(termo) {
    if (termo.arquivo_pdf_url) window.open(termo.arquivo_pdf_url, '_blank')
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Termos de Responsabilidade</h1>
          <p className="page-subtitle">
            Solicitações aguardando validação para liberar reservas de veículos.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="skeleton-list" />
      ) : termos.length === 0 ? (
        <EmptyState
          icon="✔"
          title="Tudo em dia"
          description="Não há Termos de Responsabilidade pendentes no momento."
        />
      ) : (
        <div className="reservation-list">
          {termos.map((t) => (
            <div key={t.id} className="reservation-card">
              <div className="reservation-card-main">
                <div>
                  <strong>{t.usuario_nome || `Usuário #${t.usuario}`}</strong>
                  <p className="muted-note">
                    Matrícula {t.usuario_matricula} · Entidade {ENTIDADE_LABELS[t.entidade]}
                  </p>
                </div>
              </div>

              <div className="reservation-dates">
                <div>
                  <small>Data da solicitação</small>
                  <span>{formatDate(t.data_solicitacao)}</span>
                </div>
                <div>
                  <small>CPF</small>
                  <span>{t.cpf}</span>
                </div>
                <div>
                  <small>CNH</small>
                  <span>{t.cnh}</span>
                </div>
              </div>

              <button type="button" className="link" onClick={() => abrirPdf(t)}>
                Ver documento gerado (PDF)
              </button>

              <label className="field">
                <span>Observação (opcional)</span>
                <input
                  value={observacoes[t.id] || ''}
                  onChange={(e) =>
                    setObservacoes((o) => ({ ...o, [t.id]: e.target.value }))
                  }
                  placeholder="Ex.: CNH vencida, favor reenviar."
                />
              </label>

              <div className="reservation-actions">
                <button
                  className="btn btn-ghost-danger btn-sm"
                  disabled={processando === t.id}
                  onClick={() => setTermoRejeitar(t)}
                >
                  Rejeitar
                </button>
                <button
                  className="btn btn-primary btn-sm"
                  disabled={processando === t.id}
                  onClick={() => handleDecisao(t, 'aprovado')}
                >
                  {processando === t.id ? 'Processando…' : 'Aprovar'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {termoRejeitar && (
        <Modal title="Rejeitar Termo" onClose={() => setTermoRejeitar(null)} width={500}>
          <div className="form-grid">
            <p>Tem certeza que deseja rejeitar este Termo de Responsabilidade?</p>
            <div className="admin-note">
              <strong>{termoRejeitar.usuario_nome}</strong>
              <br />
              <span>Matrícula {termoRejeitar.usuario_matricula}</span>
            </div>
            <p className="muted-note">
              O usuário permanecerá sem poder reservar veículos até enviar um novo termo.
            </p>
            <div className="modal-actions">
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setTermoRejeitar(null)}
                disabled={processando === termoRejeitar.id}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="btn btn-ghost-danger"
                onClick={() => handleDecisao(termoRejeitar, 'rejeitado')}
                disabled={processando === termoRejeitar.id}
              >
                {processando === termoRejeitar.id ? 'Processando…' : 'Sim, rejeitar'}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
