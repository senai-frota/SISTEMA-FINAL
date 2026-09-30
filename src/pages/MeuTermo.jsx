import { useEffect, useState } from 'react'
import api from '../services/api'
import { formatDate } from '../utils/format'
import StatusBadge from '../components/StatusBadge'
import { useAuth } from '../context/AuthContext'

const ENTIDADES = ['FIBRA', 'SESI', 'SENAI', 'IEL']

export default function MeuTermo() {
  const { loadPerfil } = useAuth()
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState(null)
  const [form, setForm] = useState({
    entidade: 'SENAI',
    cpf: '',
    cnh: '',
    arquivo: null,
  })
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const { data } = await api.get('/termos/meu-status/')
      setStatus(data)
      if (loadPerfil) await loadPerfil()
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setErrors({})
    setSaving(true)
    try {
      const fd = new FormData()
      fd.append('entidade', form.entidade)
      fd.append('cpf', form.cpf)
      fd.append('cnh', form.cnh)
      fd.append('arquivo_pdf', form.arquivo)
      await api.post('/termos/', fd)
      setForm((f) => ({ ...f, arquivo: null }))
      await load()
    } catch (err) {
      if (err.response?.data && typeof err.response.data === 'object') {
        setErrors(err.response.data)
      } else {
        setErrors({ non_field_errors: ['Não foi possível enviar o termo. Tente novamente.'] })
      }
    } finally {
      setSaving(false)
    }
  }

  const termo = status?.termo
  const precisaFormulario =
    !termo ||
    termo.status === 'rejeitado' ||
    status?.situacao === 'vencido' ||
    status?.situacao === 'sem_termo' ||
    (termo.status === 'aprovado' && termo.dias_restantes < 0)

  return (
    <div className="page">
      <div className="page-header">
        <h1>Termo de responsabilidade</h1>
      </div>

      {loading ? (
        <div className="skeleton-list" />
      ) : (
        <>
          <div
            className={`termo-status-card ${
              status?.conta_ativa && status?.situacao === 'valido'
                ? 'termo-ok'
                : status?.situacao === 'pendente'
                  ? 'termo-pendente'
                  : 'termo-alerta'
            }`}
          >
            <div className="termo-status-main">
              <h3>
                Conta {status?.conta_ativa ? 'ativa' : 'inativa'}
                {termo && (
                  <>
                    {' · '}
                    <StatusBadge status={termo.status} />
                  </>
                )}
              </h3>
              <p>{status?.mensagem}</p>
              {status?.data_validade && status?.situacao !== 'valido' && (
                <p className="muted-note">Válido até {formatDate(status.data_validade)}</p>
              )}
              {termo?.arquivo_pdf_url && (
                <a className="link" href={termo.arquivo_pdf_url} target="_blank" rel="noreferrer">
                  Ver documento enviado
                </a>
              )}
            </div>
          </div>

          {precisaFormulario && status?.situacao !== 'pendente' && (
            <div className="panel">
              <div className="panel-header">
                <h2>Enviar termo assinado</h2>
              </div>
              <form onSubmit={handleSubmit} className="form-grid">
                <p className="muted-note">
                  Retire o termo na secretaria, assine e envie o arquivo. A renovação é anual.
                </p>
                <label className="field">
                  <span>Entidade</span>
                  <select
                    value={form.entidade}
                    onChange={(e) => update('entidade', e.target.value)}
                    required
                  >
                    {ENTIDADES.map((e) => (
                      <option key={e} value={e}>
                        {e}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="field-row">
                  <label className="field">
                    <span>CPF</span>
                    <input
                      value={form.cpf}
                      onChange={(e) => update('cpf', e.target.value)}
                      placeholder="000.000.000-00"
                      required
                    />
                    {errors.cpf && <small className="field-error">{errors.cpf[0]}</small>}
                  </label>
                  <label className="field">
                    <span>CNH (número)</span>
                    <input
                      value={form.cnh}
                      onChange={(e) => update('cnh', e.target.value)}
                      required
                    />
                    {errors.cnh && <small className="field-error">{errors.cnh[0]}</small>}
                  </label>
                </div>
                <label className="field">
                  <span>Documento assinado (PDF ou imagem)</span>
                  <input
                    type="file"
                    accept="image/*,.pdf,application/pdf"
                    required
                    onChange={(e) => update('arquivo', e.target.files?.[0] || null)}
                  />
                  {errors.arquivo_pdf && (
                    <small className="field-error">{errors.arquivo_pdf[0]}</small>
                  )}
                </label>
                {errors.non_field_errors && (
                  <div className="form-error">
                    {Array.isArray(errors.non_field_errors)
                      ? errors.non_field_errors[0]
                      : errors.non_field_errors}
                  </div>
                )}
                <div className="modal-actions">
                  <button type="submit" className="btn btn-primary" disabled={saving}>
                    {saving ? 'Enviando…' : 'Enviar'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {Array.isArray(status?.historico) && status.historico.length > 0 && (
            <div className="panel">
              <div className="panel-header">
                <h2>Histórico</h2>
              </div>
              <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Envio</th>
                    <th>Status</th>
                    <th>Validade</th>
                    <th>Documento</th>
                  </tr>
                </thead>
                <tbody>
                  {status.historico.map((t) => (
                    <tr key={t.id}>
                      <td>{formatDate(t.criado_em)}</td>
                      <td>
                        <StatusBadge status={t.status} />
                      </td>
                      <td>{t.data_validade ? formatDate(t.data_validade) : '—'}</td>
                      <td>
                        {t.arquivo_pdf_url ? (
                          <a className="link" href={t.arquivo_pdf_url} target="_blank" rel="noreferrer">
                            Abrir
                          </a>
                        ) : (
                          '—'
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
