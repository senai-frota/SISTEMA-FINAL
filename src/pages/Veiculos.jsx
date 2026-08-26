import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import EmptyState from '../components/EmptyState'
import VehicleFormModal from '../components/VehicleFormModal'
import ReservationFormModal from '../components/ReservationFormModal'
import Modal from '../components/Modal'
import { COMBUSTIVEL_LABELS } from '../utils/format'

const STATUS_LABELS = {
  disponivel: 'Disponível',
  em_uso: 'Em uso',
  manutencao: 'Em manutenção',
  inativo: 'Inativo',
}

export default function Veiculos() {
  const { isAdmin } = useAuth()

  const [veiculos, setVeiculos] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFiltro, setStatusFiltro] = useState('')
  const [editing, setEditing] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [reservando, setReservando] = useState(null)

  const [veiculoParaRemover, setVeiculoParaRemover] = useState(null)
  const [removendo, setRemovendo] = useState(false)
  const [podeReservar, setPodeReservar] = useState(true)
  const [reservasUsuario, setReservasUsuario] = useState([])

  const [reativandoId, setReativandoId] = useState(null)

  useEffect(() => {
    if (isAdmin) return
    let active = true
    api.get('/termos/meu-status/').then(({ data }) => {
      if (active) setPodeReservar(!!data.pode_reservar)
    })
    return () => {
      active = false
    }
  }, [isAdmin])

  async function load() {
    setLoading(true)

    try {
      const params = {}

      if (search) params.search = search
      if (statusFiltro) params.status = statusFiltro

      const requests = [api.get('/veiculos/', { params })]

      if (!isAdmin) {
        requests.push(api.get('/reservas/'))
      }

      const responses = await Promise.all(requests)
      const veiculosRes = responses[0]

      setVeiculos(veiculosRes.data.results ?? veiculosRes.data)

      if (!isAdmin && responses[1]) {
        const reservasRes = responses[1]
        setReservasUsuario(reservasRes.data.results ?? reservasRes.data)
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const t = setTimeout(load, 300)

    return () => clearTimeout(t)

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, statusFiltro])

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

      setVeiculoParaRemover(null)

      await load()
    } finally {
      setRemovendo(false)
    }
  }

  async function handleReativar(veiculo) {
    setReativandoId(veiculo.id)

    try {
      await api.post(`/veiculos/${veiculo.id}/reativar/`)

      await load()
    } finally {
      setReativandoId(null)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Veículos</h1>

          <p className="page-subtitle">
            Consulte a frota e solicite a reserva de um veículo.
          </p>
        </div>

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

      {!isAdmin && !podeReservar && (
        <div className="termo-banner">
          <span>
            Você precisa ter um Termo de Responsabilidade aprovado e válido para reservar
            veículos.
          </span>
          <Link className="btn btn-primary btn-sm" to="/termos">
            Enviar termo
          </Link>
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
        <EmptyState
          icon="▣"
          title="Nenhum veículo encontrado"
          description="Ajuste os filtros ou cadastre um novo veículo."
        />
      ) : (
        <div className="vehicle-grid">
          {veiculos.map((v) => {
            const jaSolicitado = !isAdmin && reservasUsuario.some(
              (reserva) => reserva.veiculo === v.id && reserva.status === 'pendente'
            )

            return (
            <div
              key={v.id}
              className="vehicle-card"
            >
              <div className="vehicle-card-thumb">
                {v.foto_url ? (
                  <img
                    src={v.foto_url}
                    alt={v.modelo}
                  />
                ) : (
                  <span>▣</span>
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
                </div>
              </div>

              <div className="vehicle-card-actions">
                {v.status === 'disponivel' && (
                  <>
                    <button
                      className="btn btn-primary btn-sm"
                      disabled={
                        !isAdmin && (
                          !podeReservar || jaSolicitado
                        )
                      }
                      title={
                        !isAdmin && !podeReservar
                          ? 'Envie e tenha seu Termo de Responsabilidade aprovado para reservar.'
                          : jaSolicitado
                          ? 'A reserva deste veículo já foi enviada para análise.'
                          : undefined
                      }
                      onClick={() => {
                        if (!jaSolicitado) setReservando(v)
                      }}
                    >
                      {jaSolicitado ? 'Em análise' : 'Reservar'}
                    </button>

                    {jaSolicitado && (
                      <small className="muted-note">
                        A reserva deste veículo já está aguardando análise.
                      </small>
                    )}
                  </>
                )}

                {isAdmin && v.status === 'inativo' && (
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() => handleReativar(v)}
                    disabled={reativandoId === v.id}
                  >
                    {reativandoId === v.id
                      ? 'Reativando…'
                      : 'Reativar'}
                  </button>
                )}

                {isAdmin && v.status !== 'inativo' && (
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
            )
          })}
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

      {reservando && (
        <ReservationFormModal
          veiculo={reservando}
          onClose={() =>
            setReservando(null)
          }
          onSaved={async () => {
            setReservando(null)
            await load()
          }}
        />
      )}

      {veiculoParaRemover && (
        <Modal
          title="Remover veículo"
          onClose={fecharConfirmacaoRemocao}
          width={500}
        >
          <div className="form-grid">
            <p>
              Tem certeza que deseja remover este veículo?
            </p>

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

            <p className="muted-note">
              O veículo não será apagado — ele fica marcado como
              inativo e some da lista dos funcionários. Reservas e
              vistorias já feitas continuam no histórico, e você pode
              reativá-lo depois clicando em "Reativar".
            </p>

            <div className="modal-actions">
              <button
                type="button"
                className="btn btn-ghost"
                onClick={fecharConfirmacaoRemocao}
                disabled={removendo}
              >
                Cancelar
              </button>

              <button
                type="button"
                className="btn btn-ghost-danger"
                onClick={handleDelete}
                disabled={removendo}
              >
                {removendo
                  ? 'Removendo…'
                  : 'Remover veículo'}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
