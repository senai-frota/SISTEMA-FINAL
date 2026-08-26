import { useEffect, useState } from 'react'
import api from '../services/api'
import { formatDate } from '../utils/format'
import StatusBadge from '../components/StatusBadge'

const ENTIDADES = ['FIBRA', 'SESI', 'SENAI', 'IEL']

function hojeInput() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export default function MeuTermo() {
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState(null) // { pode_reservar, termo }
  const [form, setForm] = useState({
    entidade: 'SENAI',
    cpf: '',
    cnh: '',
    data_solicitacao: hojeInput(),
  })
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const { data } = await api.get('/termos/meu-status/')
      setStatus(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setErrors({})
    setSaving(true)
    try {
      await api.post('/termos/', form)
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
  const precisaFormulario = !termo || termo.status === 'rejeitado' || (termo.status === 'aprovado' && termo.dias_restantes < 0)

  function abrirPdf() {
    if (!termo?.arquivo_pdf_url) return
    window.open(termo.arquivo_pdf_url, '_blank')
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Meu Termo de Responsabilidade</h1>
          <p className="page-subtitle">
            Preencha e envie o termo para poder solicitar veículos da frota.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="skeleton-list" />
      ) : (
        <>
          {termo && (
            <div
              className={`termo-status-card ${
                termo.status === 'aprovado' && termo.dias_restantes >= 0
                  ? 'termo-ok'
                  : termo.status === 'pendente'
                  ? 'termo-pendente'
                  : 'termo-alerta'
              }`}
            >
              <div className="termo-status-main">
                <h3>
                  <StatusBadge status={termo.status} /> Termo enviado em{' '}
                  {formatDate(termo.criado_em)}
                </h3>
                {termo.status === 'pendente' && (
                  <p>Aguardando análise do administrador.</p>
                )}
                {termo.status === 'rejeitado' && (
                  <p>
                    Solicitação rejeitada
                    {termo.observacao_admin ? `: ${termo.observacao_admin}` : '.'} Envie um novo
                    termo abaixo.
                  </p>
                )}
                {termo.status === 'aprovado' && termo.dias_restantes >= 0 && (
                  <p>Válido até {formatDate(termo.data_validade)}. Você já pode solicitar veículos.</p>
                )}
                {termo.status === 'aprovado' && termo.dias_restantes < 0 && (
                  <p>Seu termo venceu em {formatDate(termo.data_validade)}. Envie um novo abaixo.</p>
                )}
                {termo.arquivo_pdf_url && (
                  <button type="button" className="link" onClick={abrirPdf}>
                    Ver documento (PDF)
                  </button>
                )}
              </div>

              {termo.status === 'aprovado' && (
                <div className="termo-status-days">
                  {termo.dias_restantes >= 0 ? termo.dias_restantes : 0}
                  <small>dias restantes</small>
                </div>
              )}
            </div>
          )}

          {!termo && (
            <div className="admin-note">
              Você ainda não enviou seu Termo de Responsabilidade. Preencha o formulário abaixo
              para começar a solicitar veículos.
            </div>
          )}

          {precisaFormulario && (
            <div className="panel">
              <div className="panel-header">
                <h2>Enviar Termo de Responsabilidade</h2>
              </div>

              <form onSubmit={handleSubmit} className="form-grid">
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
                    <span>CNH</span>
                    <input
                      value={form.cnh}
                      onChange={(e) => update('cnh', e.target.value)}
                      placeholder="Número da CNH"
                      required
                    />
                    {errors.cnh && <small className="field-error">{errors.cnh[0]}</small>}
                  </label>
                </div>

                <label className="field">
                  <span>Data da solicitação</span>
                  <input
                    type="date"
                    max={hojeInput()}
                    value={form.data_solicitacao}
                    onChange={(e) => update('data_solicitacao', e.target.value)}
                    required
                  />
                  {errors.data_solicitacao && (
                    <small className="field-error">{errors.data_solicitacao[0]}</small>
                  )}
                </label>

                <p className="muted-note">
                  O documento será gerado automaticamente com seus dados, faltando apenas a
                  validação do administrador. A validade de 1 ano começa a contar a partir da
                  aprovação.
                </p>

                {errors.non_field_errors && (
                  <div className="form-error">
                    {Array.isArray(errors.non_field_errors)
                      ? errors.non_field_errors[0]
                      : errors.non_field_errors}
                  </div>
                )}

                <div className="modal-actions">
                  <button type="submit" className="btn btn-primary" disabled={saving}>
                    {saving ? 'Enviando…' : 'Enviar termo'}
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
