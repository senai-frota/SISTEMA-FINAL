import { useEffect, useState } from 'react'
import api from '../services/api'
import { formatDate } from '../utils/format'
import StatusBadge from '../components/StatusBadge'
import { errosParaFormulario, mensagemErroApi, textoCampo } from '../utils/erros'
import { useFeedback } from '../context/FeedbackContext'

export default function MeuCNH() {
  const feedback = useFeedback()
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState(null)
  const [arquivo, setArquivo] = useState(null)
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const { data } = await api.get('/usuarios/cnh/meu-status/')
      setStatus(data)
    } catch (err) {
      feedback.erro(mensagemErroApi(err, 'Não foi possível carregar a CNH.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const podeEnviar =
    !status?.pendente &&
    (!status?.pode_reservar ||
      status?.situacao === 'proxima_vencimento' ||
      status?.situacao === 'vencida' ||
      status?.situacao === 'rejeitada' ||
      status?.situacao === 'sem_cnh')

  async function handleSubmit(e) {
    e.preventDefault()
    setErrors({})
    setSaving(true)
    try {
      const fd = new FormData()
      fd.append('arquivo', arquivo)
      await api.post('/usuarios/cnh/', fd)
      setArquivo(null)
      await load()
    } catch (err) {
      setErrors(errosParaFormulario(err, 'Não foi possível enviar a CNH.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Minha CNH</h1>
      </div>

      {loading ? (
        <div className="skeleton-list" />
      ) : (
        <>
          <div
            className={`termo-status-card ${
              status?.pode_reservar
                ? status?.proxima_do_vencimento
                  ? 'termo-pendente'
                  : 'termo-ok'
                : 'termo-alerta'
            }`}
          >
            <div className="termo-status-main">
              <StatusBadge status={status?.situacao || 'pendente'} />
              <p>{status?.mensagem}</p>
              {status?.data_validade && (
                <p className="muted-note">Validade: {formatDate(status.data_validade)}</p>
              )}
              {status?.vigente?.arquivo_url && (
                <a className="link" href={status.vigente.arquivo_url} target="_blank" rel="noreferrer">
                  Ver documento vigente
                </a>
              )}
              {status?.pendente?.arquivo_url && (
                <p className="muted-note">
                  Documento pendente enviado em {formatDate(status.pendente.criado_em)}.{' '}
                  <a className="link" href={status.pendente.arquivo_url} target="_blank" rel="noreferrer">
                    Abrir
                  </a>
                </p>
              )}
            </div>
            {typeof status?.dias_restantes === 'number' && status.pode_reservar && (
              <div className="termo-status-days">
                {status.dias_restantes}
                <small>dias restantes</small>
              </div>
            )}
          </div>

          {podeEnviar && (
            <div className="panel">
              <div className="panel-header">
                <h2>Enviar CNH</h2>
              </div>
              <form onSubmit={handleSubmit} className="form-grid">
                <label className="field">
                  <span>Arquivo (PDF ou imagem)</span>
                  <input
                    type="file"
                    accept="image/*,.pdf,application/pdf"
                    required
                    onChange={(e) => setArquivo(e.target.files?.[0] || null)}
                  />
                  {textoCampo(errors, 'arquivo') && (
                    <small className="field-error">{textoCampo(errors, 'arquivo')}</small>
                  )}
                </label>
                <p className="muted-note">
                  O gestor analisa o documento e define a validade na aprovação.
                </p>
                {textoCampo(errors, 'non_field_errors') && (
                  <div className="form-error">{textoCampo(errors, 'non_field_errors')}</div>
                )}
                <div className="modal-actions">
                  <button type="submit" className="btn btn-primary" disabled={saving || !arquivo}>
                    {saving ? 'Enviando…' : 'Enviar'}
                  </button>
                </div>
              </form>
            </div>
          )}
        </>
      )}
    </div>
  )
}
