import { useState } from 'react'
import api from '../services/api'
import Modal from './Modal'

const HORARIOS = Array.from({ length: 24 }, (_, i) => {
  const hora = String(i).padStart(2, '0')
  return `${hora}:00`
})

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

export default function ReservationFormModal({
  veiculo,
  onClose,
  onSaved,
}) {
  const hoje = new Date()

  // Primeira data permitida: 14 dias a partir de hoje
  const dataMinima = adicionarDias(hoje, 14)
  const dataMinimaInput = formatDateInput(dataMinima)

  const [form, setForm] = useState({
    data_inicio: dataMinimaInput,
    hora_inicio: '08:00',
    data_fim: dataMinimaInput,
    hora_fim: '09:00',
    motivo: '',
    destino: '',
    passageiros: 1,
  })

  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  function update(field, value) {
    setForm((f) => ({
      ...f,
      [field]: value,
    }))
  }

  function montarDataHora(data, hora) {
    if (!data || !hora) return ''

    return `${data}T${hora}`
  }

  function validarFormulario() {
    const novosErros = {}

    if (!form.data_inicio) {
      novosErros.data_inicio = ['Informe a data de retirada.']
    }

    if (!form.data_fim) {
      novosErros.data_fim = ['Informe a data de devolução.']
    }

    if (form.data_inicio && form.data_inicio < dataMinimaInput) {
      novosErros.data_inicio = [
        'A reserva deve ser feita com pelo menos 2 semanas de antecedência.',
      ]
    }

    if (form.data_fim && form.data_fim < dataMinimaInput) {
      novosErros.data_fim = [
        'A reserva deve ser feita com pelo menos 2 semanas de antecedência.',
      ]
    }

    const inicio = montarDataHora(
      form.data_inicio,
      form.hora_inicio
    )

    const fim = montarDataHora(
      form.data_fim,
      form.hora_fim
    )

    if (inicio && fim && fim <= inicio) {
      novosErros.data_fim = [
        'A devolução deve acontecer depois da retirada.',
      ]
    }

    if (!form.motivo.trim()) {
      novosErros.motivo = [
        'Informe o motivo da solicitação.',
      ]
    }

    return novosErros
  }

  async function handleSubmit(e) {
    e.preventDefault()

    const novosErros = validarFormulario()

    if (Object.keys(novosErros).length > 0) {
      setErrors(novosErros)
      return
    }

    setSaving(true)
    setErrors({})

    try {
      await api.post('/reservas/', {
        veiculo: veiculo.id,
        data_inicio: montarDataHora(
          form.data_inicio,
          form.hora_inicio
        ),
        data_fim: montarDataHora(
          form.data_fim,
          form.hora_fim
        ),
        motivo: form.motivo,
        destino: form.destino,
        passageiros: Number(form.passageiros),
      })

      onSaved()
    } catch (err) {
      if (
        err.response?.data &&
        typeof err.response.data === 'object'
      ) {
        setErrors(err.response.data)
      } else {
        setErrors({
          non_field_errors: [
            'Não foi possível criar a reserva. Tente novamente.',
          ],
        })
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      title={`Reservar ${veiculo.marca} ${veiculo.modelo}`}
      onClose={onClose}
      width={560}
    >
      <form
        onSubmit={handleSubmit}
        className="form-grid"
      >
        <div className="reservation-vehicle-info">
          <strong>
            {veiculo.marca} {veiculo.modelo}
          </strong>

          <span>
            Placa {veiculo.placa} · {veiculo.capacidade} lugares ·{' '}
            {veiculo.cor}
          </span>
        </div>

        <div className="reservation-rule">
          <strong>Antecedência mínima</strong>

          <span>
            As reservas devem ser realizadas com pelo menos
            2 semanas de antecedência.
          </span>
        </div>

        <div className="reservation-period">
          <div className="reservation-period-header">
            <span className="reservation-period-number">
              1
            </span>

            <div>
              <strong>Retirada</strong>
              <small>
                Quando o veículo será retirado
              </small>
            </div>
          </div>

          <div className="field-row">
            <label className="field">
              <span>Data</span>

              <input
                type="date"
                min={dataMinimaInput}
                value={form.data_inicio}
                onChange={(e) =>
                  update('data_inicio', e.target.value)
                }
                required
              />

              {errors.data_inicio && (
                <small className="field-error">
                  {errors.data_inicio[0]}
                </small>
              )}
            </label>

            <label className="field">
              <span>Horário</span>

              <select
                value={form.hora_inicio}
                onChange={(e) =>
                  update('hora_inicio', e.target.value)
                }
                required
              >
                {HORARIOS.map((hora) => (
                  <option key={hora} value={hora}>
                    {hora}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>

        <div className="reservation-period">
          <div className="reservation-period-header">
            <span className="reservation-period-number">
              2
            </span>

            <div>
              <strong>Devolução</strong>
              <small>
                Quando o veículo será devolvido
              </small>
            </div>
          </div>

          <div className="field-row">
            <label className="field">
              <span>Data</span>

              <input
                type="date"
                min={dataMinimaInput}
                value={form.data_fim}
                onChange={(e) =>
                  update('data_fim', e.target.value)
                }
                required
              />

              {errors.data_fim && (
                <small className="field-error">
                  {errors.data_fim[0]}
                </small>
              )}
            </label>

            <label className="field">
              <span>Horário</span>

              <select
                value={form.hora_fim}
                onChange={(e) =>
                  update('hora_fim', e.target.value)
                }
                required
              >
                {HORARIOS.map((hora) => (
                  <option key={hora} value={hora}>
                    {hora}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>

        <label className="field">
          <span>Destino</span>

          <input
            value={form.destino}
            onChange={(e) =>
              update('destino', e.target.value)
            }
            placeholder="Ex.: SENAI GAMA"
          />
        </label>

        <label className="field">
          <span>Passageiros</span>

          <input
            type="number"
            min={1}
            max={veiculo.capacidade}
            value={form.passageiros}
            onChange={(e) =>
              update('passageiros', e.target.value)
            }
            required
          />
        </label>

        <label className="field">
          <span>Motivo da solicitação</span>

          <textarea
            rows={3}
            value={form.motivo}
            onChange={(e) =>
              update('motivo', e.target.value)
            }
            placeholder="Descreva o motivo da viagem"
            required
          />

          {errors.motivo && (
            <small className="field-error">
              {errors.motivo[0]}
            </small>
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
          <button
            type="button"
            className="btn btn-ghost"
            onClick={onClose}
            disabled={saving}
          >
            Cancelar
          </button>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={saving}
          >
            {saving
              ? 'Enviando…'
              : 'Solicitar reserva'}
          </button>
        </div>
      </form>
    </Modal>
  )
}