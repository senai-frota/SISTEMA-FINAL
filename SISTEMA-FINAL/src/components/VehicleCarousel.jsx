import { useEffect, useState } from 'react'
import VehiclePlaceholder from './VehiclePlaceholder'

export function fotosDoVeiculo(veiculo) {
  if (!veiculo) return []
  if (Array.isArray(veiculo.fotos) && veiculo.fotos.length) {
    return veiculo.fotos.filter((foto) => foto?.url)
  }
  if (veiculo.foto_url) return [{ id: 'capa', url: veiculo.foto_url }]
  return []
}

export default function VehicleCarousel({
  veiculo,
  fotos,
  alt = '',
  className = '',
  objectFit = 'cover',
  onIndiceChange,
}) {
  const lista = fotos || fotosDoVeiculo(veiculo)
  const [indice, setIndice] = useState(0)
  const [toqueX, setToqueX] = useState(null)

  useEffect(() => {
    setIndice(0)
    onIndiceChange?.(0)
  }, [lista.map((foto) => foto.url).join('|')])

  if (!lista.length) {
    return (
      <div className={`vehicle-carousel ${className}`.trim()}>
        <VehiclePlaceholder />
      </div>
    )
  }

  const total = lista.length
  const atual = Math.min(indice, total - 1)
  const varias = total > 1
  const rotulo = alt || 'Foto do veículo'

  function ir(delta) {
    setIndice((i) => {
      const proximo = (i + delta + total) % total
      onIndiceChange?.(proximo)
      return proximo
    })
  }

  function aoToqueInicio(e) {
    setToqueX(e.changedTouches?.[0]?.clientX ?? null)
  }

  function aoToqueFim(e) {
    if (toqueX == null || !varias) return
    const dx = (e.changedTouches?.[0]?.clientX ?? toqueX) - toqueX
    if (dx > 40) ir(-1)
    if (dx < -40) ir(1)
    setToqueX(null)
  }

  return (
    <div
      className={`vehicle-carousel ${className}`.trim()}
      onTouchStart={aoToqueInicio}
      onTouchEnd={aoToqueFim}
    >
      <img
        src={lista[atual].url}
        alt={varias ? `${rotulo} (${atual + 1} de ${total})` : rotulo}
        style={{ objectFit }}
      />
      {varias && (
        <>
          <button
            type="button"
            className="vehicle-carousel-nav vehicle-carousel-prev"
            aria-label="Foto anterior"
            onClick={(e) => {
              e.stopPropagation()
              ir(-1)
            }}
          >
            ‹
          </button>
          <button
            type="button"
            className="vehicle-carousel-nav vehicle-carousel-next"
            aria-label="Próxima foto"
            onClick={(e) => {
              e.stopPropagation()
              ir(1)
            }}
          >
            ›
          </button>
          <div className="vehicle-carousel-indicator" aria-live="polite">
            {atual + 1}/{total}
          </div>
        </>
      )}
    </div>
  )
}
