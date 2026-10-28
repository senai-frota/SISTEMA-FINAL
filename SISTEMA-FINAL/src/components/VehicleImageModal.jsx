import { useEffect, useRef, useState } from 'react'
import Modal from './Modal'
import VehicleCarousel, { fotosDoVeiculo } from './VehicleCarousel'
import api from '../services/api'
import { useFeedback } from '../context/FeedbackContext'
import { mensagemErroApi } from '../utils/erros'

const TIPOS_ACEITOS = ['image/jpeg', 'image/png', 'image/webp']
const TAMANHO_MAXIMO_MB = 5
const MAXIMO_FOTOS = 8

export default function VehicleImageModal({ veiculo, onClose, onUpdated }) {
  const feedback = useFeedback()
  const inputRef = useRef(null)
  const [arquivos, setArquivos] = useState([])
  const [erro, setErro] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [removendo, setRemovendo] = useState(false)
  const [fotoAtual, setFotoAtual] = useState(0)

  const fotos = fotosDoVeiculo(veiculo)
  const temImagem = fotos.length > 0
  const ocupado = enviando || removendo
  const identificacao = `${veiculo.marca} ${veiculo.modelo} · ${veiculo.placa}`
  const restantes = Math.max(0, MAXIMO_FOTOS - fotos.length)
  const arquivosRef = useRef(arquivos)
  arquivosRef.current = arquivos

  useEffect(() => () => {
    arquivosRef.current.forEach((item) => URL.revokeObjectURL(item.previa))
  }, [])

  function fechar() {
    if (!ocupado) onClose()
  }

  function escolherArquivo() {
    inputRef.current?.click()
  }

  function aoSelecionar(e) {
    const escolhidos = Array.from(e.target.files || [])
    e.target.value = ''
    if (!escolhidos.length) return
    const rejeitados = []
    const aceitos = []
    for (const arquivo of escolhidos) {
      if (arquivo.type && !TIPOS_ACEITOS.includes(arquivo.type)) {
        rejeitados.push('Selecione imagens JPG, PNG ou WebP.')
        continue
      }
      if (arquivo.size > TAMANHO_MAXIMO_MB * 1024 * 1024) {
        rejeitados.push(`Cada imagem deve ter no máximo ${TAMANHO_MAXIMO_MB} MB.`)
        continue
      }
      aceitos.push({ arquivo, previa: URL.createObjectURL(arquivo) })
    }
    const limite = Math.max(0, restantes - arquivos.length)
    if (aceitos.length > limite) {
      aceitos.slice(limite).forEach((item) => URL.revokeObjectURL(item.previa))
      rejeitados.push(`Cada veículo pode ter no máximo ${MAXIMO_FOTOS} fotos.`)
    }
    setArquivos((atuais) => [...atuais, ...aceitos.slice(0, limite)])
    setErro(rejeitados[0] || '')
  }

  function limparSelecao() {
    arquivos.forEach((item) => URL.revokeObjectURL(item.previa))
    setArquivos([])
  }

  async function salvar() {
    if (!arquivos.length) return
    setEnviando(true)
    setErro('')
    try {
      const dados = new FormData()
      arquivos.forEach((item) => dados.append('imagens', item.arquivo))
      const { data } = await api.post(`/veiculos/${veiculo.id}/imagem/`, dados)
      arquivos.forEach((item) => URL.revokeObjectURL(item.previa))
      setArquivos([])
      feedback.sucesso(
        arquivos.length > 1 ? 'Fotos do veículo adicionadas.' : 'Foto do veículo adicionada.'
      )
      onUpdated(data)
    } catch (err) {
      const mensagem = mensagemErroApi(err, 'Não foi possível enviar a imagem.')
      setErro(mensagem)
      feedback.erro(mensagem)
    } finally {
      setEnviando(false)
    }
  }

  async function remover() {
    const atual = fotos[Math.min(fotoAtual, Math.max(0, fotos.length - 1))]
    const confirmado = await feedback.confirmar({
      titulo: 'Remover imagem',
      mensagem: atual
        ? `Remover esta foto de ${identificacao}? As demais fotos são mantidas.`
        : `Remover a imagem de ${identificacao}? O veículo continua cadastrado e passa a exibir o marcador padrão.`,
      confirmar: 'Remover imagem',
      cancelar: 'Voltar',
      tom: 'danger',
    })
    if (!confirmado) return
    setRemovendo(true)
    setErro('')
    try {
      const params = atual?.id && atual.id !== 'capa' ? { foto: atual.id } : undefined
      const { data } = await api.delete(`/veiculos/${veiculo.id}/imagem/`, { params })
      feedback.sucesso('Imagem do veículo removida.')
      onUpdated(data)
    } catch (err) {
      const mensagem = mensagemErroApi(err, 'Não foi possível remover a imagem.')
      setErro(mensagem)
      feedback.erro(mensagem)
    } finally {
      setRemovendo(false)
    }
  }

  const previewsPendentes = arquivos.map((item) => ({ id: item.previa, url: item.previa }))
  const galeria = previewsPendentes.length ? previewsPendentes : fotos
  const legenda = arquivos.length
    ? `Prévia de ${arquivos.length} foto(s) ainda não salva(s)`
    : temImagem
      ? `${fotos.length} foto${fotos.length > 1 ? 's' : ''} cadastrada${fotos.length > 1 ? 's' : ''}`
      : 'Nenhuma imagem cadastrada'

  return (
    <Modal title="Fotos do veículo" onClose={fechar} width={560}>
      <div className="form-grid">
        <p className="muted-note">{identificacao}</p>

        <figure className="vehicle-image-preview">
          <VehicleCarousel
            fotos={galeria}
            alt={`Imagem de ${identificacao}`}
            objectFit="contain"
            className="vehicle-carousel-preview"
            onIndiceChange={setFotoAtual}
          />
          <figcaption>{legenda}</figcaption>
        </figure>

        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="sr-only"
          multiple
          onChange={aoSelecionar}
          tabIndex={-1}
          aria-hidden="true"
        />

        <p className="muted-note">
          JPG, PNG ou WebP, até {TAMANHO_MAXIMO_MB} MB. Até {MAXIMO_FOTOS} fotos por veículo.
        </p>
        {erro && <div className="form-error" role="alert">{erro}</div>}

        <div className="modal-actions vehicle-image-actions">
          {temImagem && !arquivos.length && (
            <button
              type="button"
              className="btn btn-ghost-danger"
              onClick={remover}
              disabled={ocupado}
            >
              {removendo ? 'Removendo…' : 'Remover foto'}
            </button>
          )}
          <span className="vehicle-image-actions-spacer" />
          <button type="button" className="btn btn-ghost" onClick={fechar} disabled={ocupado}>
            Cancelar
          </button>
          {arquivos.length ? (
            <>
              <button type="button" className="btn btn-ghost" onClick={limparSelecao} disabled={ocupado}>
                Desfazer seleção
              </button>
              <button type="button" className="btn btn-ghost" onClick={escolherArquivo} disabled={ocupado}>
                Adicionar mais
              </button>
              <button type="button" className="btn btn-primary" onClick={salvar} disabled={ocupado}>
                {enviando ? 'Enviando…' : 'Salvar fotos'}
              </button>
            </>
          ) : (
            <button
              type="button"
              className="btn btn-primary"
              onClick={escolherArquivo}
              disabled={ocupado || restantes === 0}
            >
              {temImagem ? 'Adicionar fotos' : 'Adicionar imagem'}
            </button>
          )}
        </div>
      </div>
    </Modal>
  )
}
