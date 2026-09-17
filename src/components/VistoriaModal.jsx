import { useEffect, useState } from 'react'
import api from '../services/api'
import Modal from './Modal'

const DESCRICOES = [
  { value: 'frente', label: 'Frente' },
  { value: 'tras', label: 'Traseira' },
  { value: 'lateral_esq', label: 'Lateral esquerda' },
  { value: 'lateral_dir', label: 'Lateral direita' },
  { value: 'painel', label: 'Painel / interior' },
]

const UNIDADES = [
  { value: 'taguatinga', label: 'SENAI Taguatinga' },
  { value: 'gama', label: 'SENAI Gama' },
  { value: 'sobradinho', label: 'SENAI Sobradinho' },
  { value: 'sig', label: 'SENAI SIG' },
]

const MAX_FOTOS = 5

/**
 * Extrai uma mensagem legível de qualquer formato de erro do DRF:
 * {detail: "..."} | {non_field_errors: [...]} | {campo: ["..."]} | string
 */
function extrairMensagemErro(err) {
  const data = err?.response?.data

  if (!data) {
    return err?.message === 'Network Error'
      ? 'Não foi possível falar com o servidor. Verifique se o backend está rodando.'
      : 'Não foi possível concluir a vistoria. Tente novamente.'
  }

  if (typeof data === 'string') return data
  if (data.detail) return data.detail
  if (Array.isArray(data.non_field_errors) && data.non_field_errors.length) {
    return data.non_field_errors[0]
  }

  const mensagens = []
  Object.entries(data).forEach(([campo, valor]) => {
    const texto = Array.isArray(valor) ? valor.join(' ') : String(valor)
    mensagens.push(campo === 'non_field_errors' ? texto : `${campo}: ${texto}`)
  })

  return mensagens.length
    ? mensagens.join(' | ')
    : 'Não foi possível concluir a vistoria. Tente novamente.'
}

export default function VistoriaModal({ reserva, tipo, onClose, onDone }) {
  const [observacoes, setObservacoes] = useState('')
  const [unidade, setUnidade] = useState('')
  const [quilometragem, setQuilometragem] = useState('')
  const [fotos, setFotos] = useState([]) // { file, preview, descricao, observacao }
  const [step, setStep] = useState('form') // form | sending
  const [error, setError] = useState('')

  // Quilometragem herdada do último check-out do veículo
  const [kmBase, setKmBase] = useState(null) // { quilometragem, tipo_origem, primeiro_uso }
  const [kmCarregando, setKmCarregando] = useState(true)

  const kmHerdado = tipo === 'checkin' && kmBase && kmBase.quilometragem !== null
  const kmInicialReserva = tipo === 'checkout' && kmBase ? kmBase.quilometragem : null

  useEffect(() => {
    let cancelado = false

    async function carregarKm() {
      setKmCarregando(true)
      try {
        if (tipo === 'checkin') {
          // Km final do último check-out deste veículo (de qualquer usuário)
          const { data } = await api.get('/vistorias/ultima-quilometragem/', {
            params: { veiculo: reserva.veiculo, reserva: reserva.id },
          })
          if (cancelado) return
          setKmBase(data)
          if (data.quilometragem !== null && data.quilometragem !== undefined) {
            setQuilometragem(String(data.quilometragem))
          }
        } else {
          // No check-out, mostra o km inicial registrado no check-in desta reserva
          const { data } = await api.get('/vistorias/', {
            params: { reserva: reserva.id, tipo: 'checkin' },
          })
          if (cancelado) return
          const lista = data.results ?? data
          const checkin = Array.isArray(lista) ? lista[0] : null
          setKmBase({ quilometragem: checkin ? checkin.quilometragem : null })
        }
      } catch {
        if (!cancelado) setKmBase(null)
      } finally {
        if (!cancelado) setKmCarregando(false)
      }
    }

    carregarKm()
    return () => {
      cancelado = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reserva.id, tipo])

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

    if (!unidade) {
      setError('Selecione a unidade onde o check-in/check-out está sendo realizado.')
      return
    }

    if (tipo === 'checkout' && quilometragem === '') {
      setError('Informe a quilometragem final (km) do veículo.')
      return
    }

    if (tipo === 'checkin' && !kmHerdado && quilometragem === '') {
      setError(
        'Este é o primeiro uso deste veículo no sistema: informe a quilometragem inicial (km).'
      )
      return
    }

    if (
      tipo === 'checkout' &&
      kmInicialReserva !== null &&
      Number(quilometragem) < Number(kmInicialReserva)
    ) {
      setError(
        `A quilometragem final não pode ser menor que a inicial registrada no check-in (${kmInicialReserva} km).`
      )
      return
    }

    setStep('sending')
    try {
      // Uma ÚNICA requisição: o backend cria a vistoria, grava as fotos e
      // muda o status da reserva dentro da mesma transação. Se algo falhar,
      // nada é gravado e o usuário pode tentar de novo normalmente.
      const formData = new FormData()
      formData.append('reserva', reserva.id)
      formData.append('tipo', tipo)
      formData.append('unidade', unidade)
      formData.append('observacoes', observacoes || '')
      if (quilometragem !== '') {
        formData.append('quilometragem', String(Number(quilometragem)))
      }

      fotos.forEach((foto) => {
        formData.append('fotos', foto.file)
        formData.append('descricoes', foto.descricao || '')
        formData.append('observacoes_fotos', foto.observacao || '')
      })

      await api.post('/vistorias/registrar/', formData)

      onDone()
    } catch (err) {
      setStep('form')
      setError(extrairMensagemErro(err))
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
          <span>Unidade</span>
          <select value={unidade} onChange={(e) => setUnidade(e.target.value)} required>
            <option value="">Selecione a unidade…</option>
            {UNIDADES.map((u) => (
              <option key={u.value} value={u.value}>
                {u.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>{tipo === 'checkin' ? 'Quilometragem inicial (km)' : 'Quilometragem final (km)'}</span>
          <input
            type="number"
            min={tipo === 'checkout' && kmInicialReserva !== null ? kmInicialReserva : 0}
            step="1"
            inputMode="numeric"
            value={kmCarregando ? '' : quilometragem}
            onChange={(e) => setQuilometragem(e.target.value)}
            readOnly={kmHerdado}
            disabled={kmCarregando}
            placeholder={
              kmCarregando
                ? 'Carregando quilometragem…'
                : tipo === 'checkin'
                  ? 'Informe o km inicial deste veículo'
                  : 'Ex.: 45210'
            }
            required={tipo === 'checkout' || !kmHerdado}
          />

          {tipo === 'checkin' && !kmCarregando && kmHerdado && (
            <small className="muted-note">
              Preenchido automaticamente com o km{' '}
              {kmBase.tipo_origem === 'checkout' ? 'final do último check-out' : 'do último registro'}{' '}
              deste veículo ({Number(kmBase.quilometragem).toLocaleString('pt-BR')} km).
            </small>
          )}

          {tipo === 'checkin' && !kmCarregando && !kmHerdado && (
            <small className="muted-note">
              Primeiro uso deste veículo no sistema: informe a quilometragem inicial. Nos
              próximos check-ins ela será herdada automaticamente do check-out anterior.
            </small>
          )}

          {tipo === 'checkout' && !kmCarregando && kmInicialReserva !== null && (
            <small className="muted-note">
              Km inicial registrado no check-in: {Number(kmInicialReserva).toLocaleString('pt-BR')} km.
              O valor final não pode ser menor que isso.
            </small>
          )}
        </label>

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
          <button type="submit" className="btn btn-primary" disabled={step === 'sending' || kmCarregando}>
            {step === 'sending' ? 'Enviando…' : `Concluir ${tipo === 'checkin' ? 'check-in' : 'check-out'}`}
          </button>
        </div>
      </form>
    </Modal>
  )
}