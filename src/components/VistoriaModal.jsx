import { useEffect, useRef, useState } from 'react'
import api from '../services/api'
import Modal from './Modal'
import { useFeedback } from '../context/FeedbackContext'
import { isMobileClient } from '../utils/device'

const FOTOS_OBRIGATORIAS = [
  { value: 'frente', label: 'Frente do veículo' },
  { value: 'tras', label: 'Traseira do veículo' },
  { value: 'lateral_esq', label: 'Lateral esquerda' },
  { value: 'lateral_dir', label: 'Lateral direita' },
  { value: 'painel', label: 'Painel / quilometragem' },
]

const UNIDADES = [
  { value: 'taguatinga', label: 'SENAI Taguatinga' },
  { value: 'gama', label: 'SENAI Gama' },
  { value: 'sobradinho', label: 'SENAI Sobradinho' },
  { value: 'sig', label: 'SENAI SIG' },
]

function extrairMensagemErro(err) {
  const data = err?.response?.data
  if (!data) {
    return err?.message === 'Network Error'
      ? 'Não foi possível falar com o servidor. Verifique se o backend está rodando.'
      : 'Não foi possível concluir a vistoria. Tente novamente.'
  }
  if (typeof data === 'string') return data
  if (data.detail) return Array.isArray(data.detail) ? data.detail[0] : data.detail
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

function lerGeoOpcional() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve(null)
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        resolve({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          precisao_metros: pos.coords.accuracy,
        })
      },
      () => resolve(null),
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 }
    )
  })
}

export default function VistoriaModal({ reserva, tipo, onClose, onDone }) {
  const { confirmar } = useFeedback()
  const mobile = isMobileClient()
  const cameraInputRef = useRef(null)

  const [observacoes, setObservacoes] = useState('')
  const [unidade, setUnidade] = useState('')
  const [quilometragem, setQuilometragem] = useState('')
  const [fotos, setFotos] = useState({}) // { [angulo]: { file, preview } }
  const [fotoAtualIdx, setFotoAtualIdx] = useState(0)
  const [etapa, setEtapa] = useState('dados') // dados | fotos | review | sending
  const [error, setError] = useState('')
  const [kmBase, setKmBase] = useState(null)
  const [kmCarregando, setKmCarregando] = useState(true)

  const kmHerdado = tipo === 'checkin' && kmBase && kmBase.quilometragem !== null
  const kmInicialReserva = tipo === 'checkout' && kmBase ? kmBase.quilometragem : null
  const titulo = tipo === 'checkin' ? 'Check-in do veículo' : 'Check-out do veículo'
  const anguloAtual = FOTOS_OBRIGATORIAS[fotoAtualIdx]
  const fotosConcluidas = FOTOS_OBRIGATORIAS.filter((f) => fotos[f.value]).length
  const todasFotosOk = fotosConcluidas === FOTOS_OBRIGATORIAS.length

  useEffect(() => {
    let cancelado = false
    async function carregarKm() {
      setKmCarregando(true)
      try {
        if (tipo === 'checkin') {
          const { data } = await api.get('/vistorias/ultima-quilometragem/', {
            params: { veiculo: reserva.veiculo, reserva: reserva.id },
          })
          if (cancelado) return
          setKmBase(data)
          if (data.quilometragem !== null && data.quilometragem !== undefined) {
            setQuilometragem(String(data.quilometragem))
          }
        } else {
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

  useEffect(() => {
    return () => {
      Object.values(fotos).forEach((f) => {
        if (f?.preview) URL.revokeObjectURL(f.preview)
      })
    }
  }, [fotos])

  function validarDados() {
    if (!unidade) return 'Selecione a unidade onde o check-in/check-out está sendo realizado.'
    if (tipo === 'checkout' && quilometragem === '') {
      return 'Informe a quilometragem final (km) do veículo.'
    }
    if (tipo === 'checkin' && !kmHerdado && quilometragem === '') {
      return 'Este é o primeiro uso deste veículo no sistema: informe a quilometragem inicial (km).'
    }
    if (
      tipo === 'checkout' &&
      kmInicialReserva !== null &&
      Number(quilometragem) < Number(kmInicialReserva)
    ) {
      return `A quilometragem final não pode ser menor que a inicial registrada no check-in (${kmInicialReserva} km).`
    }
    return ''
  }

  function avancarParaFotos() {
    const msg = validarDados()
    if (msg) {
      setError(msg)
      return
    }
    setError('')
    setEtapa('fotos')
  }

  function onCameraCapture(e) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setError('A captura deve ser uma imagem.')
      return
    }
    const angulo = anguloAtual.value
    setFotos((prev) => {
      if (prev[angulo]?.preview) URL.revokeObjectURL(prev[angulo].preview)
      return {
        ...prev,
        [angulo]: { file, preview: URL.createObjectURL(file) },
      }
    })
    setError('')
  }

  function refazerFoto() {
    const angulo = anguloAtual.value
    setFotos((prev) => {
      if (prev[angulo]?.preview) URL.revokeObjectURL(prev[angulo].preview)
      const next = { ...prev }
      delete next[angulo]
      return next
    })
    cameraInputRef.current?.click()
  }

  function proximaFoto() {
    if (!fotos[anguloAtual.value]) {
      setError('Capture a foto deste ângulo antes de continuar.')
      return
    }
    setError('')
    if (fotoAtualIdx < FOTOS_OBRIGATORIAS.length - 1) {
      setFotoAtualIdx((i) => i + 1)
    } else {
      setEtapa('review')
    }
  }

  function fotoAnterior() {
    setError('')
    if (fotoAtualIdx > 0) setFotoAtualIdx((i) => i - 1)
    else setEtapa('dados')
  }

  async function finalizar() {
    if (!todasFotosOk) {
      setError('Capture todas as fotos obrigatórias antes de finalizar.')
      return
    }
    const msg = validarDados()
    if (msg) {
      setError(msg)
      setEtapa('dados')
      return
    }

    const confirmado = await confirmar(
      tipo === 'checkin'
        ? {
            titulo: 'Confirmar check-in',
            mensagem: 'Confirmar check-in? O veículo passará para EM USO.',
            confirmar: 'Confirmar check-in',
          }
        : {
            titulo: 'Confirmar check-out',
            mensagem: 'Confirmar check-out? A utilização será encerrada e o veículo voltará para DISPONÍVEL.',
            confirmar: 'Confirmar check-out',
          }
    )
    if (!confirmado) return

    setEtapa('sending')
    setError('')
    try {
      const geo = await lerGeoOpcional()
      const formData = new FormData()
      formData.append('reserva', reserva.id)
      formData.append('tipo', tipo)
      formData.append('unidade', unidade)
      formData.append('observacoes', observacoes || '')
      if (quilometragem !== '') {
        formData.append('quilometragem', String(Number(quilometragem)))
      }
      if (geo) {
        formData.append('latitude', String(geo.latitude))
        formData.append('longitude', String(geo.longitude))
        if (geo.precisao_metros != null) {
          formData.append('precisao_metros', String(geo.precisao_metros))
        }
      }

      FOTOS_OBRIGATORIAS.forEach((item) => {
        const foto = fotos[item.value]
        formData.append('fotos', foto.file)
        formData.append('descricoes', item.value)
        formData.append('observacoes_fotos', '')
      })

      await api.post('/vistorias/registrar/', formData)
      onDone()
    } catch (err) {
      setEtapa('review')
      setError(extrairMensagemErro(err))
    }
  }

  if (!mobile) {
    return (
      <Modal title={titulo} onClose={onClose} width={480} mobileSheet>
        <div className="form-grid">
          <div className="form-error">
            {tipo === 'checkin' ? 'Check-in' : 'Check-out'} só pode ser realizado em
            smartphone ou tablet. Abra o sistema no celular para continuar.
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-primary btn-block" onClick={onClose}>
              Entendi
            </button>
          </div>
        </div>
      </Modal>
    )
  }

  return (
    <Modal title={titulo} onClose={onClose} width={560} mobileSheet>
      <div className="form-grid vistoria-flow">
        <p className="muted-note">
          {reserva.veiculo_info || `Veículo #${reserva.veiculo}`}
          {reserva.veiculo_placa ? ` · ${reserva.veiculo_placa}` : ''}
        </p>

        {etapa === 'dados' && (
          <>
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
              <span>
                {tipo === 'checkin' ? 'Quilometragem inicial (km)' : 'Quilometragem final (km)'}
              </span>
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
                  Preenchido com o KM atual do veículo (
                  {Number(kmBase.quilometragem).toLocaleString('pt-BR')} km).
                </small>
              )}
              {tipo === 'checkout' && !kmCarregando && kmInicialReserva !== null && (
                <small className="muted-note">
                  Km inicial no check-in: {Number(kmInicialReserva).toLocaleString('pt-BR')} km.
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

            {error && <div className="form-error">{error}</div>}

            <div className="modal-actions">
              <button type="button" className="btn btn-ghost" onClick={onClose}>
                Cancelar
              </button>
              <button
                type="button"
                className="btn btn-primary"
                disabled={kmCarregando}
                onClick={avancarParaFotos}
              >
                Continuar para fotos
              </button>
            </div>
          </>
        )}

        {etapa === 'fotos' && (
          <>
            <div className="camera-step">
              <p className="camera-step-count">
                Foto {fotoAtualIdx + 1} de {FOTOS_OBRIGATORIAS.length}
              </p>
              <h4 className="camera-step-title">{anguloAtual.label}</h4>
              <p className="muted-note">
                Abra a câmera e tire a foto agora. Não use imagens da galeria.
              </p>

              {fotos[anguloAtual.value]?.preview ? (
                <div className="camera-preview">
                  <img src={fotos[anguloAtual.value].preview} alt={anguloAtual.label} />
                </div>
              ) : (
                <div className="camera-placeholder">Aguardando captura…</div>
              )}

              <input
                ref={cameraInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                className="sr-only"
                onChange={onCameraCapture}
              />

              <div className="camera-actions">
                {!fotos[anguloAtual.value] ? (
                  <button
                    type="button"
                    className="btn btn-primary btn-block"
                    onClick={() => cameraInputRef.current?.click()}
                  >
                    Abrir câmera
                  </button>
                ) : (
                  <>
                    <button type="button" className="btn btn-ghost btn-block" onClick={refazerFoto}>
                      Refazer foto
                    </button>
                    <button type="button" className="btn btn-primary btn-block" onClick={proximaFoto}>
                      {fotoAtualIdx < FOTOS_OBRIGATORIAS.length - 1
                        ? 'Próxima foto'
                        : 'Revisar e finalizar'}
                    </button>
                  </>
                )}
              </div>
            </div>

            {error && <div className="form-error">{error}</div>}

            <div className="modal-actions">
              <button type="button" className="btn btn-ghost" onClick={fotoAnterior}>
                Voltar
              </button>
            </div>
          </>
        )}

        {(etapa === 'review' || etapa === 'sending') && (
          <>
            <div className="camera-step">
              <p className="camera-step-count">
                {fotosConcluidas} de {FOTOS_OBRIGATORIAS.length} fotos concluídas
              </p>
              <div className="photo-grid photo-grid-review">
                {FOTOS_OBRIGATORIAS.map((item) => (
                  <div key={item.value} className="photo-item">
                    <img src={fotos[item.value]?.preview} alt={item.label} />
                    <small>{item.label}</small>
                  </div>
                ))}
              </div>
            </div>

            {error && <div className="form-error">{error}</div>}

            <div className="modal-actions">
              <button
                type="button"
                className="btn btn-ghost"
                disabled={etapa === 'sending'}
                onClick={() => {
                  setFotoAtualIdx(0)
                  setEtapa('fotos')
                }}
              >
                Revisar fotos
              </button>
              <button
                type="button"
                className="btn btn-primary"
                disabled={etapa === 'sending' || !todasFotosOk}
                onClick={finalizar}
              >
                {etapa === 'sending'
                  ? 'Enviando…'
                  : tipo === 'checkin'
                    ? 'Finalizar check-in'
                    : 'Finalizar check-out'}
              </button>
            </div>
          </>
        )}
      </div>
    </Modal>
  )
}
