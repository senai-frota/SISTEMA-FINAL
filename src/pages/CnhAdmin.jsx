import { useEffect, useState } from 'react'
import api from '../services/api'
import EmptyState from '../components/EmptyState'
import Modal from '../components/Modal'
import { formatDate } from '../utils/format'
import StatusBadge from '../components/StatusBadge'

export default function CnhAdmin() {
  const [pendentes, setPendentes] = useState([])
  const [loading, setLoading] = useState(true)
  const [processando, setProcessando] = useState(null)
  const [observacoes, setObservacoes] = useState({})
  const [validades, setValidades] = useState({})
  const [rejeitar, setRejeitar] = useState(null)
  const [erroAprovacao, setErroAprovacao] = useState('')

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

  async function decidir(doc, status) {
    setProcessando(doc.id)
    setErroAprovacao('')
    try {
      const body = {
        status,
        observacao_admin: observacoes[doc.id] || '',
      }
      if (status === 'aprovado') {
        if (!validades[doc.id]) {
          setErroAprovacao('Informe a data de validade da CNH para aprovar.')
          setProcessando(null)
          return
        }
        body.data_validade = validades[doc.id]
      }
      await api.patch(`/usuarios/cnh/${doc.id}/decisao/`, body)
      setRejeitar(null)
      await load()
    } catch (err) {
      const data = err.response?.data
      setErroAprovacao(
        data?.data_validade?.[0] || data?.detail || 'Não foi possível concluir a decisão.'
      )
    } finally {
      setProcessando(null)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>CNH pendentes</h1>
          <p className="page-subtitle">
            Analise o documento, informe a validade e aprove ou rejeite.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="skeleton-list" />
      ) : pendentes.length === 0 ? (
        <EmptyState icon="✔" title="Nenhuma CNH pendente" description="Não há documentos aguardando análise." />
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
                <StatusBadge status="pendente" />
              </div>
              {doc.arquivo_url && (
                <a className="link" href={doc.arquivo_url} target="_blank" rel="noreferrer">
                  Abrir documento
                </a>
              )}
              <label className="field">
                <span>Data de validade (obrigatória para aprovar)</span>
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
              {erroAprovacao && processando === doc.id && (
                <div className="form-error">{erroAprovacao}</div>
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
        <Modal title="Rejeitar CNH" onClose={() => setRejeitar(null)} width={480}>
          <div className="form-grid">
            <p>Confirma a rejeição da CNH de {rejeitar.usuario_nome}?</p>
            <div className="modal-actions">
              <button type="button" className="btn btn-ghost" onClick={() => setRejeitar(null)}>
                Cancelar
              </button>
              <button
                type="button"
                className="btn btn-ghost-danger"
                onClick={() => decidir(rejeitar, 'rejeitado')}
                disabled={processando === rejeitar.id}
              >
                Rejeitar
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
