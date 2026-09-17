import { useEffect, useState } from 'react'
import api from '../services/api'
import EmptyState from '../components/EmptyState'
import { formatDate } from '../utils/format'

const MESES = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
]

const DIAS_SEMANA = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']

const NIVEL_LABELS = {
  sem_reservas: 'Sem reservas',
  baixa: 'Baixa',
  media: 'Média',
  alta: 'Alta',
}

export default function RelatorioCalendario() {
  const hoje = new Date()
  const [mes, setMes] = useState(hoje.getMonth() + 1)
  const [ano, setAno] = useState(hoje.getFullYear())
  const [dados, setDados] = useState(null)
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState('')

  async function load() {
    setLoading(true)
    setErro('')
    try {
      const { data } = await api.get('/reservas/relatorio/calendario/', {
        params: { mes, ano },
      })
      setDados(data)
    } catch (err) {
      setDados(null)
      setErro(
        err.response?.data?.detail ||
          'Não foi possível carregar o relatório de calendário.'
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mes, ano])

  function mudarMes(delta) {
    let novoMes = mes + delta
    let novoAno = ano
    if (novoMes < 1) {
      novoMes = 12
      novoAno -= 1
    } else if (novoMes > 12) {
      novoMes = 1
      novoAno += 1
    }
    setMes(novoMes)
    setAno(novoAno)
  }

  const primeiroDiaSemana = new Date(ano, mes - 1, 1).getDay()

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Relatório de calendário</h1>
          <p className="page-subtitle">
            Veja quais dias tiveram mais ou menos reservas no mês.
          </p>
        </div>
      </div>

      <div className="toolbar calendar-toolbar">
        <button className="btn btn-ghost btn-sm" onClick={() => mudarMes(-1)}>
          ‹ Mês anterior
        </button>
        <strong className="calendar-mes-atual">
          {MESES[mes - 1]} de {ano}
        </strong>
        <button className="btn btn-ghost btn-sm" onClick={() => mudarMes(1)}>
          Próximo mês ›
        </button>
      </div>

      {loading ? (
        <div className="skeleton-list" />
      ) : erro ? (
        <EmptyState icon="⚠" title="Não foi possível carregar" description={erro} />
      ) : dados ? (
        <>
          <div className="stat-grid">
            <div className="stat-card">
              <span className="stat-label">Total de reservas no mês</span>
              <span className="stat-value">{dados.total_reservas_no_periodo}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Média diária</span>
              <span className="stat-value">{dados.media_diaria}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Dia com mais reservas</span>
              <span className="stat-value stat-value-sm">
                {dados.dia_com_mais_reservas
                  ? `${formatDate(dados.dia_com_mais_reservas.data)} · ${dados.dia_com_mais_reservas.total_reservas} reserva(s)`
                  : '—'}
              </span>
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <div>
                <h2>Calendário de movimento</h2>
                <p className="muted-note">
                  Cada dia mostra quantas reservas estavam em uso naquela data.
                </p>
              </div>
            </div>

            <div className="calendar-legend">
              {Object.entries(NIVEL_LABELS).map(([nivel, label]) => (
                <span key={nivel} className="calendar-legend-item">
                  <span className={`calendar-dot nivel-${nivel}`} />
                  {label}
                </span>
              ))}
            </div>

            <div className="calendar-grid">
              {DIAS_SEMANA.map((d) => (
                <div key={d} className="calendar-day-header">
                  {d}
                </div>
              ))}

              {Array.from({ length: primeiroDiaSemana }).map((_, i) => (
                <div key={`blank-${i}`} className="calendar-day calendar-day-empty" />
              ))}

              {dados.dias.map((dia) => (
                <div key={dia.data} className={`calendar-day nivel-${dia.nivel}`}>
                  <span className="calendar-day-number">{Number(dia.data.slice(-2))}</span>
                  <span className="calendar-day-count">
                    {dia.total_reservas} reserva{dia.total_reservas !== 1 ? 's' : ''}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </>
      ) : null}
    </div>
  )
}
