import type { Assignment, SeriesResult } from '../types'

const measures = [['reps', 'Repeticiones'], ['kg', 'Carga (kg)'], ['seconds', 'Tiempo (s)'], ['meters', 'Distancia (m)'], ['rir', 'RIR'], ['rpe', 'RPE de serie']] as const
export function ResultsEditor({ item, results, change }: { item: Assignment; results: SeriesResult[]; change: (value: SeriesResult[]) => void }) {
  const exercises = item.prescription.blocks?.flatMap(block => block.exercises) ?? []
  function edit(index: number, patch: Partial<SeriesResult>) { change(results.map((row, i) => i === index ? { ...row, ...patch } : row)) }
  return <fieldset><legend>Resultados por serie · opcionales</legend>
    {results.map((row, index) => <fieldset key={index}><legend>{row.name} · serie {row.set_number}</legend>
      {row.origin !== 'prescribed' && <label>Ejercicio realizado<input required value={row.name} onChange={event => edit(index, { name: event.target.value })} /></label>}
      <label>Número de serie<input type="number" min="1" max="100" value={row.set_number} onChange={event => edit(index, { set_number: Number(event.target.value) })} /></label>
      <div className="recipient-grid">{measures.map(([key, label]) => <label key={key}>{label}<input type="number" min={key === 'rpe' ? 1 : 0} max={key === 'rpe' || key === 'rir' ? 10 : undefined} step={['kg', 'seconds', 'meters'].includes(key) ? 'any' : '1'} value={row[key] ?? ''} onChange={event => edit(index, { [key]: event.target.value === '' ? null : Number(event.target.value) })} /></label>)}</div>
      <label>Lado<select value={row.side ?? ''} onChange={event => edit(index, { side: event.target.value as SeriesResult['side'] || null })}><option value="">Sin especificar</option><option value="bilateral">Bilateral</option><option value="left">Izquierdo</option><option value="right">Derecho</option><option value="alternating">Alterno</option></select></label>
      <label>Convención de carga<select value={row.load_convention ?? ''} onChange={event => edit(index, { load_convention: event.target.value as SeriesResult['load_convention'] || null })}><option value="">Sin especificar</option><option value="total">Total</option><option value="per_side">Por lado</option><option value="bodyweight">Peso corporal</option></select></label>
      <label>Comentario<textarea value={row.comment ?? ''} onChange={event => edit(index, { comment: event.target.value || null })} /></label>
      <button type="button" className="secondary" onClick={() => change(results.filter((_, i) => i !== index))}>Retirar resultado</button>
    </fieldset>)}
    {exercises.map(exercise => <button type="button" key={exercise.id} className="secondary" onClick={() => change([...results, { item_id: exercise.id, exercise_id: exercise.exercise_id ?? null, name: exercise.name, origin: 'prescribed', set_number: 1 + results.filter(row => row.item_id === exercise.id).length, side: exercise.side ?? null, load_convention: exercise.load_convention ?? null }])}>Añadir serie de {exercise.name}</button>)}
    <button type="button" className="secondary" onClick={() => change([...results, { name: '', origin: 'added', set_number: 1 }])}>Registrar ejercicio añadido</button>
  </fieldset>
}
