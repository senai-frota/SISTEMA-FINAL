import { useEffect, useState } from 'react'
import api from '../services/api'
import EmptyState from '../components/EmptyState'
import ConfirmDialog from '../components/ConfirmDialog'
import { useFeedback } from '../context/FeedbackContext'
import { formatDate, formatDateTime } from '../utils/format'
import { mensagemErroApi } from '../utils/erros'

const ENTIDADE_LABELS = {
  FIBRA: 'FIBRA',
  SESI: 'SESI',
  SENAI: 'SENAI',
  IEL: 'IEL',
}

export default function TermosAdmin() {
  const feedback = useFeedback()
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

  async function handleDecisao(termo, status, justificativa) {
    setProcessando(termo.id)
    try {
      await api.patch(`/termos/${termo.id}/decisao/`, {
        status,
        observacao_admin: justificativa ?? (observacoes[termo.id] || ''),
      })
      setTermoRejeitar(null)
      feedback.sucesso(
        status === 'aprovado'
          ? `Termo de ${termo.usuario_nome} aprovado.`
          : `Termo de ${termo.usuario_nome} rejeitado.`
      )
      await load()
    } catch (err) {
      feedback.erro(mensagemErroApi(err, 'Não foi possível concluir a decisão sobre o termo.'))
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
        <h1>
          Termos pendentes
          {!loading && termos.length > 0 && (
            <span className="page-count">{termos.length} aguardando validação</span>
          )}
        </h1>
      </div>

      {loading ? (
        <div className="skeleton-list" />
      ) : termos.length === 0 ? (
        <EmptyState icon="✔" title="Nenhum termo pendente" />
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
                <button type="button" className="link" onClick={() => abrirPdf(t)}>
                  Ver documento
                </button>
              </div>

              <div className="reservation-dates">
                <div>
                  <small>Solicitado em</small>
                  <span>{t.criado_em ? formatDateTime(t.criado_em) : formatDate(t.data_solicitacao)}</span>
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

              <div className="reservation-decision">
                <input
                  type="text"
                  aria-label="Observação para o usuário"
                  value={observacoes[t.id] || ''}
                  onChange={(e) =>
                    setObservacoes((o) => ({ ...o, [t.id]: e.target.value }))
                  }
                  placeholder="Observação (opcional)"
                />
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
            </div>
          ))}
        </div>
      )}

      {termoRejeitar && (
        <ConfirmDialog
          title="Rejeitar termo"
          message="O usuário ficará sem poder reservar até enviar um novo termo."
          confirmLabel="Rejeitar"
          tone="danger"
          requireReason
          reasonPlaceholder="Motivo da rejeição do termo"
          initialReason={observacoes[termoRejeitar.id] || ''}
          loading={processando === termoRejeitar.id}
          onConfirm={(motivo) => handleDecisao(termoRejeitar, 'rejeitado', motivo)}
          onCancel={() => setTermoRejeitar(null)}
        >
          <div className="admin-note">
            <strong>{termoRejeitar.usuario_nome}</strong>
            <br />
            <span>Matrícula {termoRejeitar.usuario_matricula}</span>
          </div>
        </ConfirmDialog>
      )}
    </div>
  )
}
