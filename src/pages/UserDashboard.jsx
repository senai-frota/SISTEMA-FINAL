import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import StatusBadge from '../components/StatusBadge'
import { formatDateTime } from '../utils/format'

export default function Dashboard() {
  const { user, isAdmin } = useAuth()
  const [loading, setLoading] = useState(true)
  const [veiculos, setVeiculos] = useState([])
  const [reservas, setReservas] = useState([])
  const [pendentesAdmin, setPendentesAdmin] = useState(0)
  const [termoStatus, setTermoStatus] = useState(null)

  useEffect(() => {
    let active = true
    async function load() {
      try {
        const requests = [
          api.get('/veiculos/', { params: { status: 'disponivel' } }),
          api.get('/reservas/'),
        ]
        const [veiculosRes, reservasRes] = await Promise.all(requests)
        if (!active) return
        setVeiculos(veiculosRes.data.results ?? veiculosRes.data)
        setReservas(reservasRes.data.results ?? reservasRes.data)

        if (isAdmin) {
          const pendentesRes = await api.get('/reservas/', { params: { status: 'pendente' } })
          const list = pendentesRes.data.results ?? pendentesRes.data
          if (active) setPendentesAdmin(list.length)
        } else {
          const termoRes = await api.get('/termos/meu-status/')
          if (active) setTermoStatus(termoRes.data)
        }
      } finally {
        if (active) setLoading(false)
      }
    }
    load()
    return () => {
      active = false
    }
  }, [isAdmin])

  const ativa = reservas.find((r) => ['aprovada', 'em_andamento'].includes(r.status))
  const pendentes = reservas.filter((r) => r.status === 'pendente').length
  const podeReservar = isAdmin || termoStatus?.pode_reservar
  const termo = termoStatus?.termo

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Olá, {user?.nome?.split(' ')[0]}</h1>
          <p className="page-subtitle">Aqui está o resumo da frota hoje.</p>
        </div>
        <Link className="btn btn-primary" to={podeReservar ? '/veiculos' : '/termos'}>
          Nova solicitação
        </Link>
      </div>

      {!loading && !isAdmin && !podeReservar && (
        <div className="termo-banner">
          <span>
            {!termo
              ? 'Você ainda não enviou seu Termo de Responsabilidade. Envie para poder reservar veículos.'
              : termo.status === 'pendente'
              ? 'Seu Termo de Responsabilidade está aguardando análise do administrador.'
              : termo.status === 'rejeitado'
              ? 'Seu Termo de Responsabilidade foi rejeitado. Envie um novo para poder reservar veículos.'
              : 'Seu Termo de Responsabilidade venceu. Envie um novo para poder reservar veículos.'}
          </span>
          <Link className="btn btn-primary btn-sm" to="/termos">
            {termo ? 'Ver termo' : 'Enviar termo'}
          </Link>
        </div>
      )}

      <div className="stat-grid">
        <div className="stat-card">
          <span className="stat-label">Veículos disponíveis</span>
          <span className="stat-value">{loading ? '—' : veiculos.length}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Minhas solicitações pendentes</span>
          <span className="stat-value">{loading ? '—' : pendentes}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Reserva ativa</span>
          <span className="stat-value stat-value-sm">
            {loading ? '—' : ativa ? ativa.veiculo_info || 'Em andamento' : 'Nenhuma'}
          </span>
        </div>
        {isAdmin && (
          <Link to="/aprovacoes" className="stat-card stat-card-accent">
            <span className="stat-label">Aguardando aprovação</span>
            <span className="stat-value">{loading ? '—' : pendentesAdmin}</span>
          </Link>
        )}
        {!isAdmin && (
          <Link
            to="/termos"
            className={`stat-card ${!podeReservar ? 'stat-card-accent' : ''}`}
          >
            <span className="stat-label">Termo de Responsabilidade</span>
            <span className="stat-value stat-value-sm">
              {loading
                ? '—'
                : podeReservar
                ? `Válido · ${termo.dias_restantes} dia(s)`
                : termo
                ? 'Pendente/expirado'
                : 'Não enviado'}
            </span>
          </Link>
        )}
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2>Veículos disponíveis agora</h2>
          <Link to="/veiculos" className="link">
            Ver todos
          </Link>
        </div>
        {loading ? (
          <div className="skeleton-list" />
        ) : veiculos.length === 0 ? (
          <p className="muted-note">Nenhum veículo disponível no momento.</p>
        ) : (
          <div className="mini-vehicle-grid">
            {veiculos.slice(0, 4).map((v) => (
              <div key={v.id} className="mini-vehicle-card">
                <div className="mini-vehicle-thumb">
                  {v.foto_url ? <img src={v.foto_url} alt={v.modelo} /> : <span>▣</span>}
                </div>
                <div>
                  <strong>
                    {v.marca} {v.modelo}
                  </strong>
                  <small>{v.placa}</small>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2>{isAdmin ? 'Últimas reservas' : 'Minhas últimas reservas'}</h2>
          <Link to="/reservas" className="link">
            Ver todas
          </Link>
        </div>
        {loading ? (
          <div className="skeleton-list" />
        ) : reservas.length === 0 ? (
          <p className="muted-note">Nenhuma reserva registrada ainda.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Veículo</th>
                <th>Retirada</th>
                <th>Devolução</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {reservas.slice(0, 5).map((r) => (
                <tr key={r.id}>
                  <td>{r.veiculo_info || `Veículo #${r.veiculo}`}</td>
                  <td>{formatDateTime(r.data_inicio)}</td>
                  <td>{formatDateTime(r.data_fim)}</td>
                  <td>
                    <StatusBadge status={r.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}