import { useEffect, useState } from 'react'
import api from '../services/api'
import EmptyState from '../components/EmptyState'
import ConfirmDialog from '../components/ConfirmDialog'
import { useFeedback } from '../context/FeedbackContext'
import { formatDate } from '../utils/format'
import { mensagemErroApi } from '../utils/erros'
export default function CnhAdmin() {
  const feedback = useFeedback()
  const [pendentes, setPendentes] = useState([])
  const [loading, setLoading] = useState(true)
  const [processando, setProcessando] = useState(null)
  const [observacoes, setObservacoes] = useState({})
  const [validades, setValidades] = useState({})
  const [rejeitar, setRejeitar] = useState(null)
  const [erroAprovacao, setErroAprovacao] = useState(null)

  async function load() {
    setLoading(true)
    try {
      const { data } = await api.get('/usuarios/cnh/', { params: { status: 'pendente' } })
      setPendentes(data.results ?? data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function decidir(doc, status, justificativa) {
    setErroAprovacao(null)
    const body = {
      status,
      observacao_admin: justificativa ?? (observacoes[doc.id] || ''),
    }
    if (status === 'aprovado') {
      if (!validades[doc.id]) {
        setErroAprovacao({ id: doc.id, mensagem: 'Informe a data de validade da CNH para aprovar.' })
        return
      }
      body.data_validade = validades[doc.id]
    }
    setProcessando(doc.id)
    try {
      await api.patch(`/usuarios/cnh/${doc.id}/decisao/`, body)
      setRejeitar(null)
      feedback.sucesso(
        status === 'aprovado'
          ? `CNH de ${doc.usuario_nome} aprovada.`
          : `CNH de ${doc.usuario_nome} rejeitada.`
      )
      await load()
    } catch (err) {
      const mensagem = mensagemErroApi(err, 'Não foi possível concluir a decisão.')
      if (status === 'aprovado') {
        setErroAprovacao({ id: doc.id, mensagem })
      } else {
        feedback.erro(mensagem)
      }
    } finally {
      setProcessando(null)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>
          CNH pendentes
          {!loading && pendentes.length > 0 && (
            <span className="page-count">{pendentes.length} aguardando análise</span>
          )}
        </h1>
      </div>

      {loading ? (
        <div className="skeleton-list" />
      ) : pendentes.length === 0 ? (
        <EmptyState icon="✔" title="Nenhuma CNH pendente" />
      ) : (
        <div className="reservation-list">
          {pendentes.map((doc) => (
            <div key={doc.id} className="reservation-card">
              <div className="reservation-card-main">
                <div>
                  <strong>{doc.usuario_nome}</strong>
                  <p className="muted-note">
                    Matrícula {doc.usuario_matricula} · Enviado em {formatDate(doc.criado_em)}
                  </p>
                </div>
                {doc.arquivo_url && (
                  <a className="link" href={doc.arquivo_url} target="_blank" rel="noreferrer">
                    Abrir documento
                  </a>
                )}
              </div>
              <div className="field-row">
                <label className="field">
                  <span>Validade (obrigatória para aprovar)</span>
                  <input
                    type="date"
                    value={validades[doc.id] || ''}
                    onChange={(e) => setValidades((v) => ({ ...v, [doc.id]: e.target.value }))}
                  />
                </label>
                <label className="field">
                  <span>Observação</span>
                  <input
                    value={observacoes[doc.id] || ''}
                    onChange={(e) => setObservacoes((o) => ({ ...o, [doc.id]: e.target.value }))}
                    placeholder="Opcional"
                  />
                </label>
              </div>
              {erroAprovacao?.id === doc.id && (
                <div className="form-error">{erroAprovacao.mensagem}</div>
              )}
              <div className="reservation-actions">
                <button
                  className="btn btn-ghost-danger btn-sm"
                  disabled={processando === doc.id}
                  onClick={() => setRejeitar(doc)}
                >
                  Rejeitar
                </button>
                <button
                  className="btn btn-primary btn-sm"
                  disabled={processando === doc.id}
                  onClick={() => decidir(doc, 'aprovado')}
                >
                  {processando === doc.id ? 'Processando…' : 'Aprovar'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {rejeitar && (
        <ConfirmDialog
          title="Rejeitar CNH"
          message={`Confirma a rejeição da CNH de ${rejeitar.usuario_nome}? O usuário verá a justificativa.`}
          confirmLabel="Rejeitar"
          tone="danger"
          requireReason
          reasonPlaceholder="Motivo da rejeição da CNH"
          initialReason={observacoes[rejeitar.id] || ''}
          loading={processando === rejeitar.id}
          onConfirm={(motivo) => decidir(rejeitar, 'rejeitado', motivo)}
          onCancel={() => setRejeitar(null)}
        />
      )}
    </div>
  )
}
