import { useEffect, useState } from 'react'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import StatusBadge from '../components/StatusBadge'
import Modal from '../components/Modal'
import { formatDateTime } from '../utils/format'

export default function AdminDashboard() {
  const { user } = useAuth()

  const [reservas, setReservas] = useState([])
  const [veiculos, setVeiculos] = useState([])
  const [loading, setLoading] = useState(true)
  const [processando, setProcessando] = useState(null)
  const [observacoes, setObservacoes] = useState({})
  const [pagina, setPagina] = useState(1)

  const [reservaNegacao, setReservaNegacao] = useState(null)

  const itensPorPagina = 3

  async function load() {
    setLoading(true)

    try {
      const [reservasRes, veiculosRes] = await Promise.all([
        api.get('/reservas/', {
          params: { status: 'pendente' },
        }),
        api.get('/veiculos/'),
      ])

      setReservas(
        reservasRes.data.results ?? reservasRes.data
      )

      setVeiculos(
        veiculosRes.data.results ?? veiculosRes.data
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function handleDecisao(reserva, status) {
    setProcessando(reserva.id)

    try {
      await api.patch(`/reservas/${reserva.id}/aprovar/`, {
        status,
        observacao_admin:
          observacoes[reserva.id] || '',
      })

      setReservaNegacao(null)

      await load()
    } finally {
      setProcessando(null)
    }
  }

  function confirmarNegacao(reserva) {
    setReservaNegacao(reserva)
  }

  const disponiveis = veiculos.filter(
    (v) => v.status === 'disponivel'
  ).length

  const emUso = veiculos.filter(
    (v) => v.status === 'em_uso'
  ).length

  const manutencao = veiculos.filter(
    (v) => v.status === 'manutencao'
  ).length

  const totalVeiculos = veiculos.length

  const totalPaginas = Math.max(
    1,
    Math.ceil(reservas.length / itensPorPagina)
  )

  const inicio = (pagina - 1) * itensPorPagina

  const reservasPagina = reservas.slice(
    inicio,
    inicio + itensPorPagina
  )

  function mudarPagina(novaPagina) {
    if (
      novaPagina < 1 ||
      novaPagina > totalPaginas
    ) {
      return
    }

    setPagina(novaPagina)
  }

  return (
    <div className="page">

      {/* CABEÇALHO */}
      <div className="page-header">
        <div>
          <h1>
            Olá, {user?.nome?.split(' ')[0]}
          </h1>

          <p className="page-subtitle">
            Aqui está o resumo administrativo da frota hoje.
          </p>
        </div>
      </div>

      {/* CONTEÚDO PRINCIPAL */}
      <div className="admin-dashboard-layout">

        {/* APROVAÇÕES */}
        <div className="panel">

          <div className="panel-header">
            <div>
              <h2>Aprovações</h2>

              <p className="muted-note">
                Solicitações de reserva aguardando decisão.
              </p>
            </div>

            <span className="stat-value stat-value-sm">
              {loading
                ? '—'
                : `${reservas.length} pendente${
                    reservas.length !== 1
                      ? 's'
                      : ''
                  }`}
            </span>
          </div>

          {loading ? (
            <div className="skeleton-list" />
          ) : reservas.length === 0 ? (
            <p className="muted-note">
              Não há solicitações pendentes no momento.
            </p>
          ) : (
            <>
              <div className="reservation-list">

                {reservasPagina.map((r) => (
                  <div
                    key={r.id}
                    className="reservation-card"
                  >

                    <div className="reservation-card-main">

                      <div>
                        <strong>
                          {r.veiculo_info ||
                            `Veículo #${r.veiculo}`}
                        </strong>

                        <p className="muted-note">
                          Solicitado por{' '}
                          {r.usuario_nome ||
                            `usuário #${r.usuario}`}

                          {r.usuario_matricula
                            ? ` · Matrícula ${r.usuario_matricula}`
                            : ''}
                        </p>
                      </div>

                      <StatusBadge
                        status={r.status}
                      />

                    </div>

                    <div className="reservation-dates">

                      <div>
                        <small>
                          Retirada
                        </small>

                        <span>
                          {formatDateTime(
                            r.data_inicio
                          )}
                        </span>
                      </div>

                      <div>
                        <small>
                          Devolução prevista
                        </small>

                        <span>
                          {formatDateTime(
                            r.data_fim
                          )}
                        </span>
                      </div>

                    </div>

                    <p className="reservation-motivo">
                      <strong>Motivo:</strong>{' '}
                      {r.motivo}
                    </p>

                    <p className="muted-note">
                      Destino:{' '}
                      {r.destino ||
                        'não informado'}{' '}
                      · {r.passageiros}{' '}
                      passageiro(s)
                    </p>

                    <label className="field">

                      <span>
                        Observação
                      </span>

                      <input
                        value={
                          observacoes[r.id] || ''
                        }
                        onChange={(e) =>
                          setObservacoes(
                            (o) => ({
                              ...o,
                              [r.id]:
                                e.target.value,
                            })
                          )
                        }
                        placeholder="Observação opcional"
                      />

                    </label>

                    <div className="reservation-actions">

                      {/* NEGAR */}
                      <button
                        className="btn btn-ghost-danger btn-sm"
                        disabled={
                          processando === r.id
                        }
                        onClick={() =>
                          confirmarNegacao(r)
                        }
                      >
                        Negar
                      </button>

                      {/* APROVAR */}
                      <button
                        className="btn btn-primary btn-sm"
                        disabled={
                          processando === r.id
                        }
                        onClick={() =>
                          handleDecisao(
                            r,
                            'aprovada'
                          )
                        }
                      >
                        {processando === r.id
                          ? 'Processando…'
                          : 'Aprovar'}
                      </button>

                    </div>

                  </div>
                ))}

              </div>

              {totalPaginas > 1 && (
                <div className="pagination">

                  <button
                    className="btn btn-ghost btn-sm"
                    disabled={pagina === 1}
                    onClick={() =>
                      mudarPagina(
                        pagina - 1
                      )
                    }
                  >
                    Anterior
                  </button>

                  <span className="muted-note">
                    Página {pagina} de{' '}
                    {totalPaginas}
                  </span>

                  <button
                    className="btn btn-ghost btn-sm"
                    disabled={
                      pagina === totalPaginas
                    }
                    onClick={() =>
                      mudarPagina(
                        pagina + 1
                      )
                    }
                  >
                    Próxima
                  </button>

                </div>
              )}

            </>
          )}

        </div>

        {/* INFORMAÇÕES DA FROTA */}
        <div className="admin-stats">

          <div className="stat-card">
            <span className="stat-label">
              Veículos disponíveis
            </span>

            <span className="stat-value">
              {loading
                ? '—'
                : disponiveis}
            </span>
          </div>

          <div className="stat-card">
            <span className="stat-label">
              Veículos em uso
            </span>

            <span className="stat-value">
              {loading
                ? '—'
                : emUso}
            </span>
          </div>

          <div className="stat-card">
            <span className="stat-label">
              Em manutenção
            </span>

            <span className="stat-value">
              {loading
                ? '—'
                : manutencao}
            </span>
          </div>

          <div className="stat-card">
            <span className="stat-label">
              Total da frota
            </span>

            <span className="stat-value">
              {loading
                ? '—'
                : totalVeiculos}
            </span>
          </div>

        </div>

      </div>

      {/* MODAL DE CONFIRMAÇÃO */}
      {reservaNegacao && (
        <Modal
          title="Negar solicitação"
          onClose={() =>
            setReservaNegacao(null)
          }
          width={500}
        >

          <div className="form-grid">

            <p>
              Tem certeza que deseja negar esta
              solicitação de reserva?
            </p>

            <div className="admin-note">

              <strong>
                {reservaNegacao.veiculo_info ||
                  `Veículo #${reservaNegacao.veiculo}`}
              </strong>

              <br />

              <span>
                Solicitado por{' '}
                {reservaNegacao.usuario_nome ||
                  `usuário #${reservaNegacao.usuario}`}
              </span>

              <br />

              <span>
                {formatDateTime(
                  reservaNegacao.data_inicio
                )}
                {' → '}
                {formatDateTime(
                  reservaNegacao.data_fim
                )}
              </span>

            </div>

            <p className="muted-note">
              Esta ação não poderá ser desfeita
              através desta tela.
            </p>

            <div className="modal-actions">

              <button
                type="button"
                className="btn btn-ghost"
                onClick={() =>
                  setReservaNegacao(null)
                }
                disabled={
                  processando ===
                  reservaNegacao.id
                }
              >
                Cancelar
              </button>

              <button
                type="button"
                className="btn btn-ghost-danger"
                onClick={() =>
                  handleDecisao(
                    reservaNegacao,
                    'negada'
                  )
                }
                disabled={
                  processando ===
                  reservaNegacao.id
                }
              >
                {processando ===
                reservaNegacao.id
                  ? 'Processando…'
                  : 'Sim, negar solicitação'}
              </button>

            </div>

          </div>

        </Modal>
      )}

    </div>
  )
}