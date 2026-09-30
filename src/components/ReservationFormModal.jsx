import { useEffect, useState } from 'react'
import api from '../services/api'
import Modal from './Modal'

const TURNOS = [
  { value: 'manha', label: 'Manhã (06:00 – 12:00)', inicio: '06:00', fim: '12:00' },
  { value: 'tarde', label: 'Tarde (12:00 – 18:00)', inicio: '12:00', fim: '18:00' },
  { value: 'noite', label: 'Noite (18:00 – 22:00)', inicio: '18:00', fim: '22:00' },
]

const HORARIOS = Array.from({ length: 24 * 2 }, (_, i) => {
  const h = String(Math.floor(i / 2)).padStart(2, '0')
  const m = i % 2 === 0 ? '00' : '30'
  return `${h}:${m}`
}).filter((h) => h >= '06:00' && h <= '22:00')

function formatDateInput(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function adicionarDias(data, dias) {
  const resultado = new Date(data)
  resultado.setDate(resultado.getDate() + dias)
  return resultado
}

function montarISO(data, hora) {
  if (!data || !hora) return ''
  return `${data}T${hora}:00`
}

export default function ReservationFormModal({
  veiculo,
  onClose,
  onSaved,
  cnhBloqueada,
  cnhMensagem,
  contaBloqueada = false,
  contaMensagem = '',
}) {
  const bloqueada = cnhBloqueada || contaBloqueada

  const hoje = new Date()
  const dataMaxima = formatDateInput(adicionarDias(hoje, 14))
  const dataMinima = formatDateInput(hoje)

  const [modalidade, setModalidade] = useState('horario')
  const [form, setForm] = useState({
    data: dataMinima,
    data_fim: dataMinima,
    hora_inicio: '08:00',
    hora_fim: '12:00',
    turno: 'manha',
    motivo: '',
    destino: '',
    passageiros: 1,
    pernoite: false,
    unidade_pernoite: '',
  })
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)
  const [disponibilidade, setDisponibilidade] = useState(null)

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }))
  }

  function intervaloAtual() {
    if (modalidade === 'turno') {
      const t = TURNOS.find((x) => x.value === form.turno)
      if (!t || !form.data) return null
      return {
        data_inicio: montarISO(form.data, t.inicio),
        data_fim: montarISO(form.data, t.fim),
      }
    }
    const dataFim = form.pernoite ? form.data_fim : form.data
    return {
      data_inicio: montarISO(form.data, form.hora_inicio),
      data_fim: montarISO(dataFim, form.hora_fim),
    }
  }

  useEffect(() => {
    const intervalo = intervaloAtual()
    if (!intervalo?.data_inicio || !intervalo?.data_fim) {
      setDisponibilidade(null)
      return
    }
    let cancelado = false
    const t = setTimeout(async () => {
      try {
        const { data } = await api.get('/reservas/disponibilidade/', {
          params: {
            veiculo: veiculo.id,
            data_inicio: intervalo.data_inicio,
            data_fim: intervalo.data_fim,
          },
        })
        if (!cancelado) setDisponibilidade(data)
      } catch {
        if (!cancelado) setDisponibilidade(null)
      }
    }, 300)
    return () => {
      cancelado = true
      clearTimeout(t)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    modalidade,
    form.data,
    form.data_fim,
    form.hora_inicio,
    form.hora_fim,
    form.turno,
    form.pernoite,
    veiculo.id,
  ])

  function validarFormulario() {
    const novosErros = {}
    if (!form.data) novosErros.data = ['Informe a data de início.']
    if (form.data && form.data < dataMinima) {
      novosErros.data = ['A data não pode estar no passado.']
    }
    if (form.data && form.data > dataMaxima) {
      novosErros.data = ['A reserva só pode ser feita para datas de até 14 dias à frente.']
    }
    if (modalidade === 'horario') {
      const dataFim = form.pernoite ? form.data_fim : form.data
      if (form.pernoite) {
        if (!form.data_fim) novosErros.data_fim = ['Informe a data de término.']
        if (form.data_fim && form.data_fim < form.data) {
          novosErros.data_fim = ['A data de término deve ser igual ou posterior à de início.']
        }
        if (form.data_fim && form.data_fim > dataMaxima) {
          novosErros.data_fim = ['A data de término não pode ultrapassar 14 dias à frente.']
        }
        if (!form.unidade_pernoite.trim()) {
          novosErros.unidade_pernoite = [
            'Informe a unidade onde o veículo ficará durante o pernoite.',
          ]
        }
      }
      const inicio = montarISO(form.data, form.hora_inicio)
      const fim = montarISO(dataFim, form.hora_fim)
      if (inicio && fim && fim <= inicio) {
        novosErros.hora_fim = ['O horário de fim deve ser depois do início.']
      }
    }
    if (modalidade === 'turno' && form.data === formatDateInput(new Date())) {
      const t = TURNOS.find((x) => x.value === form.turno)
      if (t && new Date(montarISO(form.data, t.fim)) <= new Date()) {
        novosErros.turno = ['Este turno já foi encerrado. Escolha outro turno ou data.']
      }
    }
    if (form.pernoite && modalidade === 'turno') {
      novosErros.pernoite = ['Pernoite só é permitido com horário personalizado.']
    }
    if (!form.motivo.trim()) novosErros.motivo = ['Informe o motivo da solicitação.']
    if (disponibilidade && !disponibilidade.disponivel) {
      novosErros.non_field_errors = ['Este veículo já possui reserva neste horário.']
    }
    return novosErros
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (cnhBloqueada) {
      setErrors({ non_field_errors: [cnhMensagem || 'CNH inválida para reservas.'] })
      return
    }
    const novosErros = validarFormulario()
    if (Object.keys(novosErros).length > 0) {
      setErrors(novosErros)
      return
    }
    setSaving(true)
    setErrors({})
    try {
      const payload =
        modalidade === 'turno'
          ? {
              veiculo: veiculo.id,
              modalidade: 'turno',
              turno: form.turno,
              data: form.data,
              motivo: form.motivo,
              destino: form.destino,
              passageiros: Number(form.passageiros),
              pernoite: false,
              unidade_pernoite: null,
            }
          : {
              veiculo: veiculo.id,
              modalidade: 'horario',
              data_inicio: montarISO(form.data, form.hora_inicio),
              data_fim: montarISO(
                form.pernoite ? form.data_fim : form.data,
                form.hora_fim
              ),
              motivo: form.motivo,
              destino: form.destino,
              passageiros: Number(form.passageiros),
              pernoite: !!form.pernoite,
              unidade_pernoite: form.pernoite ? form.unidade_pernoite : null,
            }
      await api.post('/reservas/', payload)
      onSaved()
    } catch (err) {
      if (err.response?.data && typeof err.response.data === 'object') {
        setErrors(err.response.data)
      } else {
        setErrors({ non_field_errors: ['Não foi possível criar a reserva. Tente novamente.'] })
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal title={`Reservar ${veiculo.marca} ${veiculo.modelo}`} onClose={onClose} width={560}>
      <form onSubmit={handleSubmit} className="form-grid">
        <p className="muted-note">
          Placa {veiculo.placa} · {veiculo.capacidade} lugares · {veiculo.cor}
        </p>

        {contaBloqueada && (
          <div className="form-error">
            {contaMensagem || 'Sua conta está inativa ou sem termo válido. Renove o termo antes de reservar.'}
          </div>
        )}

        {cnhBloqueada && (
          <div className="form-error">
            {cnhMensagem || 'Envie/atualize sua CNH antes de solicitar uma reserva.'}
          </div>
        )}

        <div className="field-row">
          <label className="field">
            <span>Modalidade</span>
            <select
              value={modalidade}
              onChange={(e) => {
                const value = e.target.value
                setModalidade(value)
                if (value === 'turno') {
                  update('pernoite', false)
                  update('unidade_pernoite', '')
                }
              }}
              disabled={bloqueada}
            >
              <option value="horario">Horário personalizado</option>
              <option value="turno">Turno</option>
            </select>
          </label>
          <label className="field">
            <span>{form.pernoite && modalidade === 'horario' ? 'Data de início' : 'Data'}</span>
            <input
              type="date"
              min={dataMinima}
              max={dataMaxima}
              value={form.data}
              onChange={(e) => {
                update('data', e.target.value)
                if (!form.pernoite || e.target.value > form.data_fim) {
                  update('data_fim', e.target.value)
                }
              }}
              required
              disabled={bloqueada}
            />
            {errors.data ? (
              <small className="field-error">{errors.data[0]}</small>
            ) : (
              <small className="muted-note">Até 14 dias à frente, incluindo hoje.</small>
            )}
          </label>
        </div>

        {modalidade === 'horario' && (
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={form.pernoite}
              disabled={bloqueada}
              onChange={(e) => {
                const checked = e.target.checked
                update('pernoite', checked)
                if (!checked) {
                  update('unidade_pernoite', '')
                  update('data_fim', form.data)
                } else if (!form.data_fim || form.data_fim < form.data) {
                  update('data_fim', form.data)
                }
              }}
            />
            <span>Pernoite (veículo permanece fora da unidade durante a noite)</span>
          </label>
        )}
        {errors.pernoite && <small className="field-error">{errors.pernoite[0]}</small>}

        {form.pernoite && modalidade === 'horario' && (
          <>
            <label className="field">
              <span>Data de término</span>
              <input
                type="date"
                min={form.data || dataMinima}
                max={dataMaxima}
                value={form.data_fim}
                onChange={(e) => update('data_fim', e.target.value)}
                required
                disabled={bloqueada}
              />
              {errors.data_fim && <small className="field-error">{errors.data_fim[0]}</small>}
            </label>

            <label className="field">
              <span>Unidade do pernoite</span>
              <input
                value={form.unidade_pernoite}
                onChange={(e) => update('unidade_pernoite', e.target.value)}
                placeholder="Ex.: UNIDADE SENAI GAMA"
                required
                disabled={bloqueada}
              />
              {errors.unidade_pernoite && (
                <small className="field-error">{errors.unidade_pernoite[0]}</small>
              )}
            </label>
          </>
        )}

        {modalidade === 'turno' ? (
          <label className="field">
            <span>Turno</span>
            <select
              value={form.turno}
              onChange={(e) => update('turno', e.target.value)}
              disabled={bloqueada}
            >
              {TURNOS.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
            {errors.turno && <small className="field-error">{errors.turno[0]}</small>}
          </label>
        ) : (
          <div className="field-row">
            <label className="field">
              <span>Horário de início</span>
              <select
                value={form.hora_inicio}
                onChange={(e) => update('hora_inicio', e.target.value)}
                disabled={bloqueada}
              >
                {HORARIOS.map((h) => (
                  <option key={h} value={h}>
                    {h}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Horário de fim</span>
              <select
                value={form.hora_fim}
                onChange={(e) => update('hora_fim', e.target.value)}
                disabled={bloqueada}
              >
                {HORARIOS.map((h) => (
                  <option key={h} value={h}>
                    {h}
                  </option>
                ))}
              </select>
              {errors.hora_fim && <small className="field-error">{errors.hora_fim[0]}</small>}
            </label>
          </div>
        )}

        {disponibilidade && (
          <p className={`muted-note ${disponibilidade.disponivel ? '' : 'field-error'}`}>
            {disponibilidade.disponivel
              ? 'Horário disponível para este veículo.'
              : 'Conflito: já existe reserva neste intervalo.'}
          </p>
        )}

        <div className="field-row">
          <label className="field">
            <span>Destino</span>
            <input
              value={form.destino}
              onChange={(e) => update('destino', e.target.value)}
              placeholder="Ex.: SENAI GAMA"
              disabled={bloqueada}
            />
          </label>

          <label className="field">
            <span>Passageiros</span>
            <input
              type="number"
              min={1}
              max={veiculo.capacidade}
              value={form.passageiros}
              onChange={(e) => update('passageiros', e.target.value)}
              required
              disabled={bloqueada}
            />
          </label>
        </div>

        <label className="field">
          <span>Motivo</span>
          <textarea
            rows={3}
            value={form.motivo}
            onChange={(e) => update('motivo', e.target.value)}
            placeholder="Descreva o motivo da viagem"
            required
            disabled={bloqueada}
          />
          {errors.motivo && <small className="field-error">{errors.motivo[0]}</small>}
        </label>

        {(errors.non_field_errors || errors.data_inicio) && (
          <div className="form-error">
            {Array.isArray(errors.non_field_errors)
              ? errors.non_field_errors[0]
              : errors.non_field_errors ||
                (Array.isArray(errors.data_inicio) ? errors.data_inicio[0] : errors.data_inicio)}
          </div>
        )}

        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose} disabled={saving}>
            Cancelar
          </button>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={saving || bloqueada || (disponibilidade && !disponibilidade.disponivel)}
          >
            {saving ? 'Enviando…' : 'Solicitar reserva'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
