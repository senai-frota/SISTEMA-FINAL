import { useState } from 'react'
import api from '../services/api'
import Modal from './Modal'

const DESCRICOES = [
  { value: 'frente', label: 'Frente' },
  { value: 'tras', label: 'Traseira' },
  { value: 'lateral_esq', label: 'Lateral esquerda' },
  { value: 'lateral_dir', label: 'Lateral direita' },
  { value: 'painel', label: 'Painel / interior' },
]

const MAX_FOTOS = 5

export default function VistoriaModal({ reserva, tipo, onClose, onDone }) {
  const [observacoes, setObservacoes] = useState('')
  const [fotos, setFotos] = useState([]) // { file, preview, descricao, observacao }
  const [step, setStep] = useState('form') // form | sending
  const [error, setError] = useState('')

  const titulo = tipo === 'checkin' ? 'Check-in do veículo' : 'Check-out do veículo'

  function addFotos(fileList) {
    const novos = Array.from(fileList)
      .slice(0, MAX_FOTOS - fotos.length)
      .map((file) => ({
        file,
        preview: URL.createObjectURL(file),
        descricao: '',
        observacao: '',
      }))
    setFotos((f) => [...f, ...novos])
  }

  function removeFoto(index) {
    setFotos((f) => f.filter((_, i) => i !== index))
  }

  function updateFoto(index, field, value) {
    setFotos((f) => f.map((foto, i) => (i === index ? { ...foto, [field]: value } : foto)))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')

    if (fotos.length === 0) {
      setError('Adicione ao menos 1 foto da vistoria.')
      return
    }

    setStep('sending')
    try {
      // Tudo em uma única requisição: o backend cria a vistoria, sobe as
      // fotos e atualiza o status da reserva numa única transação. Se
      // qualquer parte falhar, nada fica gravado pela metade e dá pra
      // simplesmente tentar de novo (antes, isso ficava "travado").
      const formData = new FormData()
      formData.append('reserva', reserva.id)
      formData.append('tipo', tipo)
      formData.append('observacoes', observacoes)
      fotos.forEach((foto) => {
        formData.append('fotos', foto.file)
        formData.append('descricoes', foto.descricao || '')
        formData.append('observacoes_fotos', foto.observacao || '')
      })

      await api.post('/vistorias/completa/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      onDone()
    } catch (err) {
      setStep('form')
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.non_field_errors?.[0] ||
        'Não foi possível concluir a vistoria. Tente novamente.'
      setError(msg)
    }
  }

  return (
    <Modal title={titulo} onClose={onClose} width={600}>
      <form onSubmit={handleSubmit} className="form-grid">
        <p className="muted-note">
          {reserva.veiculo_info || `Veículo #${reserva.veiculo}`}
          {reserva.veiculo_placa ? ` · ${reserva.veiculo_placa}` : ''}
        </p>

        <label className="field">
          <span>Observações gerais</span>
          <textarea
            rows={2}
            value={observacoes}
            onChange={(e) => setObservacoes(e.target.value)}
            placeholder="Ex.: Veículo em bom estado, sem avarias."
          />
        </label>

        <div className="field">
          <span>Fotos da vistoria ({fotos.length}/{MAX_FOTOS})</span>
          <div className="photo-grid">
            {fotos.map((foto, i) => (
              <div key={i} className="photo-item">
                <img src={foto.preview} alt={`Foto ${i + 1}`} />
                <button
                  type="button"
                  className="photo-remove"
                  onClick={() => removeFoto(i)}
                  aria-label="Remover foto"
                >
                  ✕
                </button>
                <select
                  value={foto.descricao}
                  onChange={(e) => updateFoto(i, 'descricao', e.target.value)}
                >
                  <option value="">Ângulo…</option>
                  {DESCRICOES.map((d) => (
                    <option key={d.value} value={d.value}>
                      {d.label}
                    </option>
                  ))}
                </select>
              </div>
            ))}

            {fotos.length < MAX_FOTOS && (
              <label className="photo-upload-tile">
                <input
                  type="file"
                  accept="image/*"
                  multiple
                  hidden
                  onChange={(e) => e.target.files && addFotos(e.target.files)}
                />
                <span>+</span>
                <small>Adicionar foto</small>
              </label>
            )}
          </div>
        </div>

        {error && <div className="form-error">{error}</div>}

        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose} disabled={step === 'sending'}>
            Cancelar
          </button>
          <button type="submit" className="btn btn-primary" disabled={step === 'sending'}>
            {step === 'sending' ? 'Enviando…' : `Concluir ${tipo === 'checkin' ? 'check-in' : 'check-out'}`}
          </button>
        </div>
      </form>
    </Modal>
  )
}
