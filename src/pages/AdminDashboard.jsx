import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import ConfirmDialog from '../components/ConfirmDialog'
import { useFeedback } from '../context/FeedbackContext'
import { formatDateTime } from '../utils/format'
import { mensagemErroApi } from '../utils/erros'

function totalDe(data) {
  return data?.count ?? (Array.isArray(data) ? data.length : data?.results?.length ?? 0)
}

function PainelAlertas({ titulo, alertas }) {
  return (
    <div className="alert-group">
      <h3>{titulo}</h3>
      <div className="alert-cards">
        {alertas.map((a) => (
          <Link
            key={a.rotulo}
            to={a.para}
            className={`alert-card alert-card-${a.valor > 0 ? a.tom : 'ok'}`}
          >
            <span className="alert-card-value">{a.valor}</span>
            <span className="alert-card-label">{a.rotulo}</span>
          </Link>
        ))}
      </div>
    </div>
  )
}

export default function AdminDashboard() {
  const { user } = useAuth()
  const feedback = useFeedback()

  const [reservas, setReservas] = useState([])
  const [totalReservasPendentes, setTotalReservasPendentes] = useState(0)
  const [frota, setFrota] = useState({ disponiveis: 0, emUso: 0, manutencao: 0, total: 0 })
  const [pendencias, setPendencias] = useState(null)
  const [loading, setLoading] = useState(true)
  const [processando, setProcessando] = useState(null)
  const [observacoes, setObservacoes] = useState({})
  const [pagina, setPagina] = useState(1)

  const [reservaNegacao, setReservaNegacao] = useState(null)

  const itensPorPagina = 3

  async function load() {
    setLoading(true)

    try {
      const contarVeiculos = (params) =>
        api.get('/veiculos/', { params }).then((res) => totalDe(res.data))

      const [reservasRes, pendenciasRes, disponiveis, emUso, manutencao, total] = await Promise.all([
        api.get('/reservas/', {
          params: { status: 'pendente' },
        }),
        api.get('/usuarios/pendencias/'),
        contarVeiculos({ status: 'disponivel' }),
        contarVeiculos({ status: 'em_uso' }),
        contarVeiculos({ status: 'manutencao' }),
        contarVeiculos({ incluir_inativos: true }),
      ])

      setReservas(
        reservasRes.data.results ?? reservasRes.data
      )
      setTotalReservasPendentes(totalDe(reservasRes.data))
      setFrota({ disponiveis, emUso, manutencao, total })
      setPendencias(pendenciasRes.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function handleDecisao(reserva, status, justificativa) {
    setProcessando(reserva.id)

    try {
      await api.patch(`/reservas/${reserva.id}/aprovar/`, {
        status,
        observacao_admin:
          justificativa ?? (observacoes[reserva.id] || ''),
      })

      setReservaNegacao(null)
      feedback.sucesso(status === 'aprovada' ? 'Reserva aprovada.' : 'Reserva negada.')

      await load()
    } catch (err) {
      feedback.erro(mensagemErroApi(err, 'Não foi possível processar a decisão.'))
    } finally {
      setProcessando(null)
    }
  }

  function confirmarNegacao(reserva) {
    setReservaNegacao(reserva)
  }

  const alertasCnh = pendencias ? [
    {
      rotulo: 'Aguardando análise',
      valor: pendencias.cnh.pendentes_analise,
      para: '/cnh-pendentes',
      tom: 'info',
    },
    {
      rotulo: 'Vencidas',
      valor: pendencias.cnh.vencidas,
      para: '/usuarios?cnh_situacao=vencida',
      tom: 'danger',
    },
    {
      rotulo: `Vencendo em até ${pendencias.cnh.dias_alerta} dias`,
      valor: pendencias.cnh.proximas_vencimento,
      para: '/usuarios?cnh_situacao=proxima_vencimento',
      tom: 'warning',
    },
    {
      rotulo: 'Sem CNH válida',
      valor: pendencias.cnh.sem_cnh_valida,
      para: '/usuarios?cnh_situacao=sem_cnh,rejeitada',
      tom: 'warning',
    },
  ] : []

  const alertasTermo = pendencias ? [
    {
      rotulo: 'Aguardando análise',
      valor: pendencias.termo.pendentes_analise,
      para: '/termos-pendentes',
      tom: 'info',
    },
    {
      rotulo: 'Vencidos',
      valor: pendencias.termo.vencidos,
      para: '/usuarios?termo_situacao=vencido&incluir_inativos=true',
      tom: 'danger',
    },
    {
      rotulo: 'Sem termo válido',
      valor: pendencias.termo.sem_termo_valido,
      para: '/usuarios?termo_situacao=sem_termo,rejeitado&incluir_inativos=true',
      tom: 'warning',
    },
    {
      rotulo: 'Contas inativas',
      valor: pendencias.contas_inativas,
      para: '/usuarios?ativo=false',
      tom: 'neutral',
    },
  ] : []

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

  const indicadoresFrota = [
    ['Disponíveis', frota.disponiveis],
    ['Em uso', frota.emUso],
    ['Em manutenção', frota.manutencao],
    ['Total', frota.total],
  ]

  return (
    <div className="page">
      <div className="page-header">
        <h1>Olá, {user?.nome?.split(' ')[0]}</h1>
      </div>

      <div className="admin-dashboard-layout">
        <div className="panel">
          <div className="panel-header">
            <h2>
              Aprovações
              {!loading && totalReservasPendentes > 0 && (
                <span className="page-count">
                  {totalReservasPendentes} pendente{totalReservasPendentes !== 1 ? 's' : ''}
                </span>
              )}
            </h2>
            <Link to="/aprovacoes" className="link">
              Ver todas
            </Link>
          </div>

          {!loading && totalReservasPendentes > reservas.length && (
            <p className="muted-note">
              Exibindo {reservas.length} de {totalReservasPendentes}.
            </p>
          )}

          {loading ? (
            <div className="skeleton-list" />
          ) : reservas.length === 0 ? (
            <p className="muted-note">Nenhuma solicitação pendente.</p>
          ) : (
            <>
              <div className="reservation-list">
                {reservasPagina.map((r) => (
                  <div key={r.id} className="reservation-card">
                    <div className="reservation-card-main">
                      <div>
                        <strong>{r.veiculo_info || `Veículo #${r.veiculo}`}</strong>
                        <p className="muted-note">
                          {r.usuario_nome || `Usuário #${r.usuario}`}
                          {r.usuario_matricula ? ` · Matrícula ${r.usuario_matricula}` : ''}
                        </p>
                      </div>
                    </div>

                    <div className="reservation-dates">
                      <div>
                        <small>Retirada</small>
                        <span>{formatDateTime(r.data_inicio)}</span>
                      </div>
                      <div>
                        <small>Devolução prevista</small>
                        <span>{formatDateTime(r.data_fim)}</span>
                      </div>
                    </div>

                    {r.pernoite && (
                      <p className="muted-note">
                        Pernoite: SIM
                        {r.unidade_pernoite ? ` · ${r.unidade_pernoite}` : ''}
                      </p>
                    )}

                    <p className="reservation-motivo">
                      <strong>Motivo:</strong> {r.motivo}
                    </p>
                    <p className="muted-note">
                      Destino: {r.destino || 'não informado'} · {r.passageiros} passageiro(s)
                      {r.pernoite &&
                        ` · Pernoite${r.unidade_pernoite ? `: ${r.unidade_pernoite}` : ''}`}
                    </p>

                    <div className="reservation-decision">
                      <input
                        type="text"
                        aria-label="Observação para o solicitante"
                        value={observacoes[r.id] || ''}
                        onChange={(e) =>
                          setObservacoes((o) => ({ ...o, [r.id]: e.target.value }))
                        }
                        placeholder="Observação (opcional)"
                      />
                      <div className="reservation-actions">
                        <button
                          className="btn btn-ghost-danger btn-sm"
                          disabled={processando === r.id}
                          onClick={() => confirmarNegacao(r)}
                        >
                          Negar
                        </button>
                        <button
                          className="btn btn-primary btn-sm"
                          disabled={processando === r.id}
                          onClick={() => handleDecisao(r, 'aprovada')}
                        >
                          {processando === r.id ? 'Processando…' : 'Aprovar'}
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {totalPaginas > 1 && (
                <div className="pagination">
                  <button
                    className="btn btn-ghost btn-sm"
                    disabled={pagina === 1}
                    onClick={() => mudarPagina(pagina - 1)}
                  >
                    Anterior
                  </button>
                  <span className="muted-note">
                    Página {pagina} de {totalPaginas}
                  </span>
                  <button
                    className="btn btn-ghost btn-sm"
                    disabled={pagina === totalPaginas}
                    onClick={() => mudarPagina(pagina + 1)}
                  >
                    Próxima
                  </button>
                </div>
              )}
            </>
          )}
        </div>

        <div className="admin-stats">
          <h3 className="admin-stats-title">Frota</h3>
          {indicadoresFrota.map(([rotulo, valor]) => (
            <div key={rotulo} className="stat-card">
              <span className="stat-label">{rotulo}</span>
              <span className="stat-value">{loading ? '—' : valor}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2>Pendências</h2>
        </div>

        {loading ? (
          <div className="skeleton-list" />
        ) : !pendencias ? (
          <p className="muted-note">Não foi possível carregar os alertas.</p>
        ) : (
          <div className="alert-groups">
            <PainelAlertas titulo="CNH" alertas={alertasCnh} />
            <PainelAlertas titulo="Termos e contas" alertas={alertasTermo} />
          </div>
        )}
      </div>

      {reservaNegacao && (
        <ConfirmDialog
          title="Negar solicitação"
          message="O solicitante verá a justificativa. A negação não pode ser desfeita nesta tela."
          confirmLabel="Negar"
          tone="danger"
          requireReason
          reasonPlaceholder="Motivo da negação"
          initialReason={observacoes[reservaNegacao.id] || ''}
          loading={processando === reservaNegacao.id}
          onConfirm={(motivo) => handleDecisao(reservaNegacao, 'negada', motivo)}
          onCancel={() => setReservaNegacao(null)}
        >
          <div className="admin-note">
            <strong>{reservaNegacao.veiculo_info || `Veículo #${reservaNegacao.veiculo}`}</strong>
            <br />
            <span>
              Solicitado por {reservaNegacao.usuario_nome || `usuário #${reservaNegacao.usuario}`}
            </span>
            <br />
            <span>
              {formatDateTime(reservaNegacao.data_inicio)}
              {' → '}
              {formatDateTime(reservaNegacao.data_fim)}
            </span>
          </div>
        </ConfirmDialog>
      )}
    </div>
  )
}
