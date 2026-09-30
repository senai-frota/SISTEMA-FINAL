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

  return (
    <div className="page">
      <div className="page-header">
        <h1>Olá, {user?.nome?.split(' ')[0]}</h1>
        <Link className="btn btn-primary" to="/veiculos">
          Reservar veículo
        </Link>
      </div>

      {(!user?.is_active || (user?.termo && !user.termo.pode_reservar)) && (
        <div className="admin-note form-error">
          <strong>Conta / Termo:</strong>{' '}
          {user?.termo?.mensagem || 'Sua conta está inativa. Renove o termo de responsabilidade.'}{' '}
          <Link className="link" to="/meu-termo">
            Renovar termo
          </Link>
        </div>
      )}

      {user?.cnh && (!user.cnh.pode_reservar || user.cnh.proxima_do_vencimento) && (
        <div className={`admin-note ${!user.cnh.pode_reservar ? 'form-error' : ''}`}>
          <strong>CNH:</strong> {user.cnh.mensagem}{' '}
          <Link className="link" to="/minha-cnh">
            Gerenciar CNH
          </Link>
        </div>
      )}

      <div className="stat-grid">
        <div className="stat-card">
          <span className="stat-label">Solicitações pendentes</span>
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
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2>
            Veículos disponíveis
            {!loading && <span className="page-count page-count-neutral">{veiculos.length}</span>}
          </h2>
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
          <p className="muted-note">Nenhuma reserva ainda.</p>
        ) : (
          <>
            <div className="table-desktop-only table-scroll">
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
            </div>
            <div className="mobile-card-list">
              {reservas.slice(0, 5).map((r) => (
                <article key={r.id} className="mobile-entity-card">
                  <div className="mobile-entity-card-head">
                    <strong>{r.veiculo_info || `Veículo #${r.veiculo}`}</strong>
                    <StatusBadge status={r.status} />
                  </div>
                  <p className="muted-note">
                    {formatDateTime(r.data_inicio)} → {formatDateTime(r.data_fim)}
                  </p>
                </article>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}