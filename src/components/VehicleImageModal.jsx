import { useEffect, useRef, useState } from 'react'
import Modal from './Modal'
import VehiclePlaceholder from './VehiclePlaceholder'
import api from '../services/api'
import { useFeedback } from '../context/FeedbackContext'
import { mensagemErroApi } from '../utils/erros'

// Pré-validação para resposta rápida; a validação definitiva (conteúdo real do arquivo) é do backend.
const TIPOS_ACEITOS = ['image/jpeg', 'image/png', 'image/webp']
const TAMANHO_MAXIMO_MB = 5

export default function VehicleImageModal({ veiculo, onClose, onUpdated }) {
  const feedback = useFeedback()
  const inputRef = useRef(null)
  const [arquivo, setArquivo] = useState(null)
  const [previa, setPrevia] = useState('')
  const [erro, setErro] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [removendo, setRemovendo] = useState(false)

  const temImagem = Boolean(veiculo.foto_url)
  const ocupado = enviando || removendo
  const identificacao = `${veiculo.marca} ${veiculo.modelo} · ${veiculo.placa}`

  useEffect(() => {
    if (!arquivo) {
      setPrevia('')
      return undefined
    }
    const url = URL.createObjectURL(arquivo)
    setPrevia(url)
    return () => URL.revokeObjectURL(url)
  }, [arquivo])

  function fechar() {
    if (!ocupado) onClose()
  }

  function escolherArquivo() {
    inputRef.current?.click()
  }

  function aoSelecionar(e) {
    const escolhido = e.target.files?.[0]
    e.target.value = ''
    if (!escolhido) return
    if (escolhido.type && !TIPOS_ACEITOS.includes(escolhido.type)) {
      setErro('Selecione uma imagem JPG, PNG ou WebP.')
      return
    }
    if (escolhido.size > TAMANHO_MAXIMO_MB * 1024 * 1024) {
      setErro(`A imagem deve ter no máximo ${TAMANHO_MAXIMO_MB} MB.`)
      return
    }
    setErro('')
    setArquivo(escolhido)
  }

  async function salvar() {
    if (!arquivo) return
    setEnviando(true)
    setErro('')
    try {
      const dados = new FormData()
      dados.append('imagem', arquivo)
      const { data } = await api.post(`/veiculos/${veiculo.id}/imagem/`, dados)
      feedback.sucesso(temImagem ? 'Imagem do veículo substituída.' : 'Imagem do veículo adicionada.')
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
    const confirmado = await feedback.confirmar({
      titulo: 'Remover imagem',
      mensagem: `Remover a imagem de ${identificacao}? O veículo continua cadastrado e passa a exibir o marcador padrão.`,
      confirmar: 'Remover imagem',
      cancelar: 'Voltar',
      tom: 'danger',
    })
    if (!confirmado) return
    setRemovendo(true)
    setErro('')
    try {
      const { data } = await api.delete(`/veiculos/${veiculo.id}/imagem/`)
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

  const imagemExibida = previa || veiculo.foto_url
  const legenda = previa
    ? 'Prévia da nova imagem (ainda não salva)'
    : temImagem
      ? 'Imagem atual'
      : 'Nenhuma imagem cadastrada'

  return (
    <Modal title="Imagem do veículo" onClose={fechar} width={560}>
      <div className="form-grid">
        <p className="muted-note">{identificacao}</p>

        <figure className="vehicle-image-preview">
          {imagemExibida ? (
            <img src={imagemExibida} alt={`Imagem de ${identificacao}`} />
          ) : (
            <VehiclePlaceholder />
          )}
          <figcaption>{legenda}</figcaption>
        </figure>

        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="sr-only"
          onChange={aoSelecionar}
          tabIndex={-1}
          aria-hidden="true"
        />

        <p className="muted-note">JPG, PNG ou WebP, até {TAMANHO_MAXIMO_MB} MB.</p>
        {erro && <div className="form-error" role="alert">{erro}</div>}

        <div className="modal-actions vehicle-image-actions">
          {temImagem && !arquivo && (
            <button
              type="button"
              className="btn btn-ghost-danger"
              onClick={remover}
              disabled={ocupado}
            >
              {removendo ? 'Removendo…' : 'Remover imagem'}
            </button>
          )}
          <span className="vehicle-image-actions-spacer" />
          <button type="button" className="btn btn-ghost" onClick={fechar} disabled={ocupado}>
            Cancelar
          </button>
          {arquivo ? (
            <>
              <button type="button" className="btn btn-ghost" onClick={escolherArquivo} disabled={ocupado}>
                Escolher outra
              </button>
              <button type="button" className="btn btn-primary" onClick={salvar} disabled={ocupado}>
                {enviando ? 'Enviando…' : temImagem ? 'Substituir imagem' : 'Salvar imagem'}
              </button>
            </>
          ) : (
            <button type="button" className="btn btn-primary" onClick={escolherArquivo} disabled={ocupado}>
              {temImagem ? 'Alterar imagem' : 'Adicionar imagem'}
            </button>
          )}
        </div>
      </div>
    </Modal>
  )
}
