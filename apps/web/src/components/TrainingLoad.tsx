import { useEffect, useId, useRef, useState } from 'react'
import { trainingTypes } from '../format'
import type { Assignment } from '../types'
import { summarizeLoad } from '../training/load'
import type { LoadBucket, LoadMetric } from '../training/load'
import './training-load.css'

const number = new Intl.NumberFormat('es-ES')

function dateLabel(value: string) {
  return new Date(`${value}T12:00:00`).toLocaleDateString('es-ES', {
    day: 'numeric', month: 'short',
  })
}

function bucketLabel(bucket: LoadBucket) {
  return bucket.start === bucket.end
    ? dateLabel(bucket.start)
    : `${dateLabel(bucket.start)} – ${dateLabel(bucket.end)}`
}

function bucketDescription(bucket: LoadBucket, unit: string) {
  if (!bucket.sessions) return 'Sin sesiones registradas'
  if (!bucket.known) return 'Sin datos suficientes para calcular este valor'
  const value = `${number.format(bucket.club + bucket.home)} ${unit}`
  const missing = bucket.sessions - bucket.known
  return missing ? `${value} · ${missing} sesiones sin datos` : value
}

function LoadChart({ buckets, unit }: { buckets: LoadBucket[]; unit: string }) {
  const container = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(600)
  const [selected, setSelected] = useState<number | null>(null)
  const titleId = useId()

  useEffect(() => {
    const element = container.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => {
      setWidth(Math.max(240, Math.floor(entry.contentRect.width)))
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  const left = 44
  const right = 12
  const top = 24
  const floor = 206
  const step = (width - left - right) / buckets.length
  const barWidth = Math.min(32, step * 0.64)
  const maximum = Math.max(1, ...buckets.map(bucket => bucket.club + bucket.home))
  const magnitude = 10 ** Math.floor(Math.log10(maximum / 4))
  const tickSize = Math.max(1, Math.ceil(maximum / 4 / magnitude) * magnitude)
  const ceiling = tickSize * 4
  const y = (value: number) => floor - (value / ceiling) * (floor - top)
  const labelEvery = Math.max(1, Math.ceil(buckets.length / (width < 440 ? 4 : 7)))
  const current = selected == null ? null : buckets[selected]

  return (
    <div ref={container} className="load-chart">
      <svg viewBox={`0 0 ${width} 244`} width="100%" height="244" aria-labelledby={titleId}>
        <title id={titleId}>Evolución de {unit === 'UA' ? 'carga' : 'duración'} registrada. Cada barra se puede seleccionar para consultar su detalle.</title>
        {[0, 1, 2, 3, 4].map(tick => {
          const value = ceiling * tick / 4
          return (
            <g key={tick} className="chart-grid" aria-hidden="true">
              <line x1={left} x2={width - right} y1={y(value)} y2={y(value)} />
              <text x={left - 8} y={y(value) + 4} textAnchor="end">
                {number.format(Math.round(value))}
              </text>
            </g>
          )
        })}
        {buckets.map((bucket, index) => {
          const x = left + step * (index + 0.5)
          const total = bucket.club + bucket.home
          const active = index === selected
          return (
            <g key={bucket.start}>
              <rect
                x={x - step / 2 + 1} y={top - 8}
                width={Math.max(1, step - 2)} height={floor - top + 12}
                rx="4" fill={active ? '#edf5fa' : 'transparent'}
                aria-hidden="true"
              />
              {bucket.club > 0 && (
                <rect className="chart-bar-club" x={x - barWidth / 2} y={y(bucket.club)}
                  width={barWidth} height={floor - y(bucket.club)} rx="2" aria-hidden="true" />
              )}
              {bucket.home > 0 && (
                <rect className="chart-bar-home" x={x - barWidth / 2} y={y(total)}
                  width={barWidth} height={y(bucket.club) - y(total)} rx="2" aria-hidden="true" />
              )}
              {bucket.sessions > bucket.known && (
                <circle cx={x} cy={floor + 7} r="2.5" fill="none" stroke="#617d91" aria-hidden="true" />
              )}
              <rect
                className="chart-hit-area" x={x - step / 2} y={top - 8}
                width={step} height={floor - top + 18}
                fill="transparent" tabIndex={0} role="button"
                aria-label={`${bucketLabel(bucket)}: ${bucketDescription(bucket, unit)}`}
                aria-pressed={active}
                onFocus={() => setSelected(index)}
                onMouseEnter={() => setSelected(index)}
                onClick={() => setSelected(index)}
                onKeyDown={event => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    setSelected(index)
                  }
                }}
              />
              {((index % labelEvery === 0 && index <= buckets.length - 1 - labelEvery)
                || index === buckets.length - 1) && (
                <text className="chart-date" x={x} y="237"
                  textAnchor={index === buckets.length - 1 ? 'end' : 'middle'} aria-hidden="true">
                  {dateLabel(bucket.start)}
                </text>
              )}
            </g>
          )
        })}
      </svg>
      <div className="chart-readout" aria-live="polite" aria-atomic="true">
        {current ? (
          <><strong>{bucketLabel(current)}</strong><span>{bucketDescription(current, unit)}</span></>
        ) : (
          <span>Selecciona una barra para consultar el detalle.</span>
        )}
      </div>
    </div>
  )
}

export function TrainingLoad({ assignments }: { assignments: Assignment[] }) {
  const [days, setDays] = useState(28)
  const [metric, setMetric] = useState<LoadMetric>('load')
  const summary = summarizeLoad(assignments, days, metric)
  const unit = metric === 'load' ? 'UA' : 'min'
  const largestType = Math.max(1, ...summary.byType.map(([, value]) => value))

  return (
    <section className="training-load" aria-labelledby="training-load-title">
      <div className="section-head load-heading">
        <div>
          <p className="eyebrow">Volumen e intensidad</p>
          <h2 id="training-load-title">Tu carga de entrenamiento</h2>
          <p className="muted load-period">{dateLabel(summary.firstDay)} – {dateLabel(summary.lastDay)}</p>
        </div>
        <div className="segmented-control" role="group" aria-label="Período de carga">
          {[7, 28, 84].map(value => (
            <button key={value} type="button" aria-pressed={days === value} onClick={() => setDays(value)}>
              {value} días
            </button>
          ))}
        </div>
      </div>

      <dl className="load-statistics">
        <div>
          <dt>{metric === 'load' ? 'Carga registrada' : 'Duración registrada'}</dt>
          <dd>{summary.known ? number.format(summary.total) : '—'} <small>{unit}</small></dd>
        </div>
        <div>
          <dt>Sesiones realizadas</dt>
          <dd>{summary.sessions}</dd>
        </div>
        <div>
          <dt>Tiempo registrado</dt>
          <dd>{summary.knownMinutes ? number.format(summary.minutes) : '—'} <small>min</small></dd>
        </div>
        <div>
          <dt>Sesiones con datos</dt>
          <dd>{summary.known}<small> / {summary.sessions}</small></dd>
        </div>
      </dl>

      <div className="load-visuals">
        <div className="load-timeline">
          <div className="load-chart-toolbar">
            <h3>{days > 28 ? 'Evolución semanal' : 'Evolución diaria'}</h3>
            <label className="chart-metric">
              <span className="sr-only">Métrica del gráfico</span>
              <select value={metric} onChange={event => setMetric(event.target.value as LoadMetric)}>
                <option value="load">Carga · UA</option>
                <option value="actual_minutes">Duración · min</option>
              </select>
            </label>
          </div>
          <div className="chart-legend">
            <span><i className="legend-club" />Club</span>
            <span><i className="legend-home" />Casa</span>
            {summary.missing > 0 && <span><i className="legend-missing" />Datos incompletos</span>}
          </div>
          {summary.known ? (
            <LoadChart key={`${days}-${metric}`} buckets={summary.buckets} unit={unit} />
          ) : (
            <div className="chart-empty">
              <strong>{summary.sessions ? 'Faltan datos para esta métrica' : 'Sin sesiones registradas en este período'}</strong>
              <p>{summary.sessions
                ? 'Completa la duración y el esfuerzo de tus sesiones para consultar este gráfico.'
                : 'Aquí aparecerán tus sesiones completadas y parciales dentro del período seleccionado.'}</p>
            </div>
          )}
        </div>
        <div className="load-distribution">
          <h3>Por modalidad</h3>
          <p className="muted">{metric === 'load' ? 'Carga acumulada' : 'Tiempo registrado'} en el período</p>
          {summary.byType.length ? (
            <ul>
              {summary.byType.map(([type, value]) => (
                <li key={type}>
                  <div><span>{trainingTypes[type] ?? type}</span><strong>{number.format(value)} <small>{unit}</small></strong></div>
                  <div className="distribution-track" aria-hidden="true">
                    <span style={{ width: `${value / largestType * 100}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          ) : <p className="muted">Aún no hay datos para comparar modalidades.</p>}
        </div>
      </div>
      <p className="load-method">
        Carga = minutos realizados × esfuerzo percibido (RPE), en unidades arbitrarias (UA).
        Agrupado por fecha programada, en la zona horaria del navegador.
        {summary.missing > 0 && ` ${summary.missing} sesiones sin datos suficientes quedan fuera del cálculo.`}
      </p>
      {summary.sessions > 0 && (
        <details className="chart-data">
          <summary>Consultar datos del gráfico</summary>
          <div className="table-scroll">
            <table>
              <caption>{metric === 'load' ? 'Carga' : 'Duración'} registrada por período, en {unit}</caption>
              <thead><tr><th>Período</th><th>Club</th><th>Casa</th><th>Cobertura</th></tr></thead>
              <tbody>
                {summary.buckets.map(bucket => (
                  <tr key={bucket.start}>
                    <th scope="row">{bucketLabel(bucket)}</th>
                    <td>{bucket.known ? number.format(bucket.club) : '—'}</td>
                    <td>{bucket.known ? number.format(bucket.home) : '—'}</td>
                    <td>{bucket.known} de {bucket.sessions} sesiones</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </section>
  )
}
