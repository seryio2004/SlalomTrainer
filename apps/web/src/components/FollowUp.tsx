import { useState } from 'react'
import { useResource } from '../useResource'
import { trainingTypes } from '../format'
import type { SeriesResult } from '../types'

type Totals = { load_athletes: number; athletes: number; sessions: number; known_load: number | null; load_coverage: number; mean_load: number | null; mean_rpe: number | null; rpe_sample: number; pain_count: number }
type Metric = { date: string; meters?: number | null; seconds?: number | null; model?: string | null; resistance?: string | null; protocol?: string | null; protocol_version?: number | null; pace_seconds_km?: number | null; training_type: string }
type FollowUpData = {
  timezone: string; undated_executions: number; athletes: number
  compliance: Record<string, number>; compliance_denominator: number
  daily: (Totals & { date: string })[]
  weekly: (Totals & { week: string; previous_known_load: number | null; difference: number | null })[]
  strength: { exercise: string; exercise_id: string | null; known_volume_kg_reps: number | null; best_kg: number | null; records: (SeriesResult & { date: string; volume_kg_reps: number | null })[] }[]
  tests: { comparable: boolean; records: Metric[] }[]
  metrics: Metric[]
}
const value = (number: number | null | undefined) => number == null ? 'Sin datos' : new Intl.NumberFormat('es-ES', { maximumFractionDigits: 1 }).format(number)
export function FollowUp({ base, athleteId, groupIds }: { base: string; athleteId?: string; groupIds?: string[] }) {
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [kind, setKind] = useState('')
  const [exercise, setExercise] = useState('')
  const query = new URLSearchParams()
  if (athleteId) query.set('athlete_id', athleteId)
  groupIds?.forEach(id => query.append('group_ids', id))
  if (start) query.set('start', start)
  if (end) query.set('end', end)
  if (kind) query.set('training_type', kind)
  const resource = useResource<FollowUpData>(`${base}/follow-up?${query}`)
  const data = resource.data
  return <section><h2>Seguimiento y rendimiento</h2>
    <div className="form-row"><label>Desde<input type="date" value={start} onChange={event => setStart(event.target.value)} /></label><label>Hasta<input type="date" value={end} onChange={event => setEnd(event.target.value)} /></label></div>
    <label>Tipo<select value={kind} onChange={event => setKind(event.target.value)}><option value="">Todos</option>{Object.entries(trainingTypes).map(([key, text]) => <option value={key} key={key}>{text}</option>)}</select></label>
    {resource.loading && <p>Cargando seguimiento…</p>}{resource.error && <p className="error" role="alert">{resource.error}</p>}
    {data && <>
      <p>Zona del club: {data.timezone} · Deportistas: {data.athletes}</p>
      <p>Completadas: {data.compliance.completed} · Parciales: {data.compliance.partial} · Omitidas: {data.compliance.skipped} · Sin registrar: {data.compliance.unregistered} · Total vencidas: {data.compliance_denominator}</p>
      {!!data.undated_executions && <p>{data.undated_executions} registros históricos sin fecha real: fuera de los agregados de carga por fecha.</p>}
      <details open><summary>Carga semanal y comparación</summary>{data.weekly.length ? <div className="table-wrap"><table><thead><tr><th>Semana (lunes)</th><th>Carga conocida (UA)</th><th>Cobertura</th><th>Media por deportista (UA, n)</th><th>Anterior (UA)</th><th>Diferencia (UA)</th><th>RPE medio (n)</th></tr></thead><tbody>{data.weekly.map(row => <tr key={row.week}><td>{row.week}</td><td>{value(row.known_load)}</td><td>{row.load_coverage}/{row.sessions}</td><td>{value(row.mean_load)} (n={row.load_athletes}/{row.athletes})</td><td>{value(row.previous_known_load)}</td><td>{value(row.difference)}</td><td>{value(row.mean_rpe)} ({row.rpe_sample})</td></tr>)}</tbody></table></div> : <p>No hay ejecuciones fechadas en este período.</p>}</details>
      <details><summary>Carga diaria y molestias</summary>{data.daily.map(row => <p key={row.date}>{row.date} · {value(row.known_load)} UA · Cobertura {row.load_coverage}/{row.sessions} · Molestias: {row.pain_count}</p>)}</details>
      <details><summary>Fuerza y series</summary>
        <label>Ejercicio<select value={exercise} onChange={event => setExercise(event.target.value)}><option value="">Todos</option>{[...new Set(data.strength.map(row => row.exercise))].map(name => <option value={name} key={name}>{name}</option>)}</select></label>
        {!data.strength.length && <p>No hay series registradas.</p>}
        {data.strength.filter(row => !exercise || row.exercise === exercise).map((group, index) => <div key={index}><h4>{group.exercise}</h4><p>Volumen externo conocido: {value(group.known_volume_kg_reps)} kg × reps · Mejor carga en condiciones comparables: {value(group.best_kg)} kg</p><div className="table-wrap"><table><thead><tr><th>Fecha</th><th>Serie</th><th>Reps</th><th>kg</th><th>s</th><th>Lado</th><th>RIR</th><th>Volumen</th></tr></thead><tbody>{group.records.map((row, i) => <tr key={i}><td>{row.date}</td><td>{row.set_number}</td><td>{value(row.reps)}</td><td>{value(row.kg)}</td><td>{value(row.seconds)}</td><td>{row.side ?? 'Sin datos'}</td><td>{value(row.rir)}</td><td>{value(row.volume_kg_reps)}</td></tr>)}</tbody></table></div></div>)}
      </details>
      <details><summary>Tests por condiciones comparables</summary>{!data.tests.length && <p>No hay tests registrados.</p>}{data.tests.map((group, index) => <div key={index}><h4>{group.comparable ? 'Mismas condiciones de comparación' : 'Condiciones sin verificar'}</h4><p>{group.records[0].meters} m · {group.records[0].model ?? 'Modelo sin datos'} · {group.records[0].resistance ?? 'Resistencia sin datos'} · Protocolo {group.records[0].protocol ?? 'sin datos'} · v{group.records[0].protocol_version ?? '?'}</p>{group.records.map((row, i) => <p key={i}>{row.date} · {value(row.seconds)} s</p>)}</div>)}</details>
      <details><summary>Agua, carrera y ergómetro</summary>{!data.metrics.length && <p>No hay métricas específicas registradas.</p>}{data.metrics.map((row, index) => <p key={index}>{row.date} · {trainingTypes[row.training_type]} · {value(row.meters)} m · {value(row.seconds)} s · Ritmo: {value(row.pace_seconds_km)} s/km</p>)}</details>
    </>}
  </section>
}
