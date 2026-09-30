import { useEffect, useState } from 'react'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import EmptyState from '../components/EmptyState'
import VehicleFormModal from '../components/VehicleFormModal'
import ReservationFormModal from '../components/ReservationFormModal'
import ConfirmDialog from '../components/ConfirmDialog'
import VehicleImageModal from '../components/VehicleImageModal'
import VehiclePlaceholder from '../components/VehiclePlaceholder'
import { useFeedback } from '../context/FeedbackContext'
import { COMBUSTIVEL_LABELS, formatDate } from '../utils/format'

const STATUS_LABELS = {
  disponivel: 'Disponível',
  em_uso: 'Em uso',
  manutencao: 'Em manutenção',
  inativo: 'Inativo',
}

export default function Veiculos() {
  const { isAdmin, user } = useAuth()
  const feedback = useFeedback()

  const cnh = user?.cnh
  const termo = user?.termo
  const cnhBloqueada = cnh ? !cnh.pode_reservar : true
  const contaBloqueada = !user?.is_active || (termo ? !termo.pode_reservar : true)

  const [veiculos, setVeiculos] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFiltro, setStatusFiltro] = useState('')
  const [editing, setEditing] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [reservando, setReservando] = useState(null)

  const [veiculoParaRemover, setVeiculoParaRemover] = useState(null)
  const [removendo, setRemovendo] = useState(false)
  const [mostrarInativos, setMostrarInativos] = useState(false)
  const [veiculoImagem, setVeiculoImagem] = useState(null)

  async function load() {
    setLoading(true)

    try {
      const params = {}

      if (search) params.search = search
      if (statusFiltro) params.status = statusFiltro
      if (isAdmin && mostrarInativos) params.incluir_inativos = true

      const { data } = await api.get('/veiculos/', { params })

      setVeiculos(data.results ?? data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const t = setTimeout(load, 300)

    return () => clearTimeout(t)

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, statusFiltro, mostrarInativos, isAdmin])

  function abrirConfirmacaoRemocao(veiculo) {
    setVeiculoParaRemover(veiculo)
  }

  function fecharConfirmacaoRemocao() {
    if (removendo) return

    setVeiculoParaRemover(null)
  }

  async function handleDelete() {
    if (!veiculoParaRemover) return

    setRemovendo(true)

    try {
      await api.delete(
        `/veiculos/${veiculoParaRemover.id}/`
      )

      feedback.sucesso(`Veículo ${veiculoParaRemover.placa} removido.`)
      setVeiculoParaRemover(null)

      await load()
    } catch (err) {
      const data = err.response?.data
      feedback.erro(
        (typeof data?.detail === 'string' && data.detail) ||
          data?.non_field_errors?.[0] ||
          'Não foi possível remover o veículo. Tente novamente.'
      )
    } finally {
      setRemovendo(false)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Veículos</h1>

        {isAdmin && (
          <button
            className="btn btn-primary"
            onClick={() => {
              setEditing(null)
              setShowForm(true)
            }}
          >
            + Novo veículo
          </button>
        )}
      </div>

      {!isAdmin && contaBloqueada && (
        <div className="admin-note form-error">
          <strong>Conta / Termo:</strong>{' '}
          {termo?.mensagem || 'Conta inativa ou sem termo válido.'}{' '}
          <a className="link" href="/meu-termo">
            Renovar termo
          </a>
        </div>
      )}

      {!isAdmin && cnh && (cnhBloqueada || cnh.proxima_do_vencimento) && (
        <div className={`admin-note ${cnhBloqueada ? 'form-error' : ''}`}>
          <strong>CNH:</strong> {cnh.mensagem}{' '}
          <a className="link" href="/minha-cnh">
            Gerenciar CNH
          </a>
        </div>
      )}

      <div className="toolbar">
        <input
          className="search-input"
          placeholder="Buscar por placa, modelo ou marca…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <select
          value={statusFiltro}
          onChange={(e) => setStatusFiltro(e.target.value)}
        >
          <option value="">Todos os status</option>

          {Object.entries(STATUS_LABELS)
            .filter(([value]) => isAdmin || value !== 'inativo')
            .map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
        </select>

        {isAdmin && (
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={mostrarInativos}
              onChange={(e) => setMostrarInativos(e.target.checked)}
            />
            <span>Mostrar inativos</span>
          </label>
        )}
      </div>

      {loading ? (
        <div className="skeleton-grid">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="skeleton-card"
            />
          ))}
        </div>
      ) : veiculos.length === 0 ? (
        <EmptyState icon="▣" title="Nenhum veículo encontrado" />
      ) : (
        <div className="vehicle-grid">
          {veiculos.map((v) => (
            <div
              key={v.id}
              className="vehicle-card"
            >
              <div className="vehicle-card-thumb">
                {v.foto_url ? (
                  <img
                    src={v.foto_url}
                    alt={`${v.marca} ${v.modelo}`}
                  />
                ) : (
                  <VehiclePlaceholder />
                )}

                <span
                  className={`chip chip-${v.status}`}
                >
                  {STATUS_LABELS[v.status]}
                </span>
              </div>

              <div className="vehicle-card-body">
                <h3>
                  {v.marca} {v.modelo}
                </h3>

                <p className="vehicle-plate">
                  {v.placa}
                </p>

                <div className="vehicle-meta">
                  <span>{v.ano}</span>
                  <span>•</span>
                  <span>{v.cor}</span>
                  <span>•</span>
                  <span>
                    {
                      COMBUSTIVEL_LABELS[
                        v.tipo_combustivel
                      ]
                    }
                  </span>
                  <span>•</span>
                  <span>
                    {v.capacidade} lugares
                  </span>
                  {typeof v.km_atual === 'number' && (
                    <>
                      <span>•</span>
                      <span>{v.km_atual.toLocaleString('pt-BR')} km</span>
                    </>
                  )}
                  {v.data_ultima_manutencao && (
                    <>
                      <span>•</span>
                      <span>
                        Manut. {formatDate(v.data_ultima_manutencao)}
                      </span>
                    </>
                  )}
                </div>
              </div>

              <div className="vehicle-card-actions">
                {!isAdmin && v.status === 'disponivel' && (
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() =>
                      setReservando(v)
                    }
                  >
                    Reservar
                  </button>
                )}

                {isAdmin && (
                  <>
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => {
                        setEditing(v)
                        setShowForm(true)
                      }}
                    >
                      Editar
                    </button>

                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => setVeiculoImagem(v)}
                    >
                      Imagem
                    </button>

                    <button
                      className="btn btn-ghost-danger btn-sm"
                      onClick={() =>
                        abrirConfirmacaoRemocao(v)
                      }
                    >
                      Remover
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {showForm && (
        <VehicleFormModal
          veiculo={editing}
          onClose={() =>
            setShowForm(false)
          }
          onSaved={() => {
            setShowForm(false)
            load()
          }}
        />
      )}

      {isAdmin && veiculoImagem && (
        <VehicleImageModal
          veiculo={veiculoImagem}
          onClose={() => setVeiculoImagem(null)}
          onUpdated={(atualizado) => {
            setVeiculos((lista) =>
              lista.map((item) => (item.id === atualizado.id ? atualizado : item))
            )
            setVeiculoImagem(null)
          }}
        />
      )}

      {!isAdmin && reservando && (
        <ReservationFormModal
          veiculo={reservando}
          cnhBloqueada={cnhBloqueada}
          cnhMensagem={cnh?.mensagem}
          contaBloqueada={contaBloqueada}
          contaMensagem={termo?.mensagem}
          onClose={() =>
            setReservando(null)
          }
          onSaved={() =>
            setReservando(null)
          }
        />
      )}

      {veiculoParaRemover && (
        <ConfirmDialog
          title="Remover veículo"
          message="O veículo será inativado e deixará de aparecer na frota."
          confirmLabel="Remover"
          loadingLabel="Removendo…"
          tone="danger"
          loading={removendo}
          onConfirm={handleDelete}
          onCancel={fecharConfirmacaoRemocao}
        >
          <div className="admin-note">
            <strong>
              {veiculoParaRemover.marca}{' '}
              {veiculoParaRemover.modelo}
            </strong>

            <br />

            <span>
              Placa: {veiculoParaRemover.placa}
            </span>
          </div>
        </ConfirmDialog>
      )}
    </div>
  )
}