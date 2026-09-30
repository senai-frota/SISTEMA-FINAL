const PALETA = [
  'var(--color-info)',
  'var(--color-success)',
  'var(--status-pendente)',
  'var(--color-primary)',
  'var(--status-em_andamento)',
  'var(--color-accent)',
  'var(--color-text-soft)',
]

function corDe(item, indice) {
  return item.cor || PALETA[indice % PALETA.length]
}

function percentual(parte, total) {
  if (!total) return '0%'
  return `${(Math.round((parte * 1000) / total) / 10).toLocaleString('pt-BR')}%`
}

function SemDados({ texto = 'Sem dados para os filtros selecionados.' }) {
  return <p className="chart-empty">{texto}</p>
}

/** Rosca em SVG com legenda. itens: [{ rotulo, total, cor? }] */
export function Rosca({ itens, titulo, centro }) {
  const total = itens.reduce((soma, item) => soma + item.total, 0)
  if (!total) return <SemDados />

  const raio = 42
  const circunferencia = 2 * Math.PI * raio
  let acumulado = 0

  return (
    <div className="chart-donut">
      <svg
        viewBox="0 0 120 120"
        role="img"
        aria-label={`${titulo}: ${itens.map((i) => `${i.rotulo} ${i.total}`).join(', ')}`}
      >
        <circle cx="60" cy="60" r={raio} className="chart-donut-track" />
        {itens.map((item, indice) => {
          if (!item.total) return null
          const tamanho = (item.total / total) * circunferencia
          const segmento = (
            <circle
              key={item.rotulo}
              cx="60"
              cy="60"
              r={raio}
              fill="none"
              stroke={corDe(item, indice)}
              strokeWidth="16"
              strokeDasharray={`${tamanho} ${circunferencia - tamanho}`}
              strokeDashoffset={-acumulado}
              transform="rotate(-90 60 60)"
            >
              <title>{`${item.rotulo}: ${item.total}`}</title>
            </circle>
          )
          acumulado += tamanho
          return segmento
        })}
        <text x="60" y="58" textAnchor="middle" className="chart-donut-total">{total}</text>
        <text x="60" y="74" textAnchor="middle" className="chart-donut-label">{centro || 'total'}</text>
      </svg>
      <ul className="chart-legend">
        {itens.map((item, indice) => (
          <li key={item.rotulo}>
            <span className="chart-swatch" style={{ background: corDe(item, indice) }} />
            <span className="chart-legend-label">{item.rotulo}</span>
            <strong>{item.total}</strong>
            <small>{percentual(item.total, total)}</small>
          </li>
        ))}
      </ul>
    </div>
  )
}

/** Barras horizontais. itens: [{ rotulo, total, cor? }] */
export function Barras({ itens, unidade = '', vazio }) {
  const maximo = Math.max(0, ...itens.map((item) => item.total))
  if (!itens.length || !maximo) return <SemDados texto={vazio} />

  return (
    <ul className="chart-bars">
      {itens.map((item, indice) => (
        <li key={`${item.rotulo}-${indice}`}>
          <div className="chart-bars-head">
            <span title={item.rotulo}>{item.rotulo}</span>
            <strong>
              {item.total.toLocaleString('pt-BR')}
              {unidade}
            </strong>
          </div>
          <div className="chart-bars-track">
            <div
              className="chart-bars-fill"
              style={{ width: `${(item.total / maximo) * 100}%`, background: corDe(item, indice) }}
            />
          </div>
        </li>
      ))}
    </ul>
  )
}

const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']

function rotuloMes(valor) {
  const [ano, mes] = valor.split('-')
  return `${MESES[Number(mes) - 1]}/${ano.slice(2)}`
}

/** Colunas empilhadas por mês. meses: [{ mes: 'AAAA-MM', total, aprovadas, negadas }] */
export function ColunasMensais({ meses }) {
  const maximo = Math.max(0, ...meses.map((m) => m.total))
  if (!meses.length || !maximo) return <SemDados />

  const series = [
    { chave: 'aprovadas', rotulo: 'Aprovadas', cor: 'var(--status-aprovada)' },
    { chave: 'negadas', rotulo: 'Negadas', cor: 'var(--status-negada)' },
    { chave: 'outras', rotulo: 'Pendentes / canceladas', cor: 'var(--color-text-soft)' },
  ]

  return (
    <div className="chart-columns-wrap">
      <div className="chart-columns" role="img" aria-label="Reservas por mês">
        {meses.map((m) => {
          const valores = {
            aprovadas: m.aprovadas,
            negadas: m.negadas,
            outras: Math.max(0, m.total - m.aprovadas - m.negadas),
          }
          return (
            <div key={m.mes} className="chart-column" title={`${rotuloMes(m.mes)}: ${m.total} reserva(s)`}>
              <div className="chart-column-area">
                <div className="chart-column-stack" style={{ height: `${(m.total / maximo) * 100}%` }}>
                  <strong className="chart-column-total">{m.total}</strong>
                  <div className="chart-column-bar">
                    {series.map((serie) =>
                      valores[serie.chave] ? (
                        <span
                          key={serie.chave}
                          style={{ flexGrow: valores[serie.chave], background: serie.cor }}
                        />
                      ) : null
                    )}
                  </div>
                </div>
              </div>
              <small className="chart-column-label">{rotuloMes(m.mes)}</small>
            </div>
          )
        })}
      </div>
      <ul className="chart-legend chart-legend-inline">
        {series.map((serie) => (
          <li key={serie.chave}>
            <span className="chart-swatch" style={{ background: serie.cor }} />
            <span className="chart-legend-label">{serie.rotulo}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
