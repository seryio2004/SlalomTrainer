import type { PrescriptionBlock, ExerciseTarget } from '../types'

const measures = [
  ['sets', 'Series', 1], ['reps', 'Repeticiones', 0], ['kg', 'Carga (kg)', 0],
  ['seconds', 'Duración (s)', 0], ['meters', 'Distancia (m)', 0],
  ['rest_seconds', 'Descanso (s)', 0], ['rir', 'RIR', 0], ['target_rpe', 'RPE objetivo', 1],
] as const

export function PrescriptionEditor({ blocks, change }: {
  blocks: PrescriptionBlock[]; change: (value: PrescriptionBlock[]) => void
}) {
  function editBlock(index: number, patch: Partial<PrescriptionBlock>) {
    change(blocks.map((block, i) => i === index ? { ...block, ...patch } : block))
  }
  function editExercise(b: number, e: number, patch: Partial<ExerciseTarget>) {
    editBlock(b, { exercises: blocks[b].exercises.map((exercise, i) => i === e ? { ...exercise, ...patch } : exercise) })
  }
  return <fieldset disabled={false}>
    <legend>Bloques y ejercicios</legend>
    {blocks.map((block, b) => <fieldset key={block.id}>
      <legend>Bloque {b + 1}</legend>
      <label>Título del bloque<input value={block.title} required maxLength={160} onChange={event => editBlock(b, { title: event.target.value })} /></label>
      <label>Instrucciones del bloque<textarea value={block.instructions} maxLength={2000} onChange={event => editBlock(b, { instructions: event.target.value })} /></label>
      {block.exercises.map((exercise, e) => <fieldset key={exercise.id}>
        <legend>Ejercicio {e + 1}</legend>
        <label>Ejercicio<input required maxLength={160} value={exercise.name} onChange={event => editExercise(b, e, { name: event.target.value })} /></label>
        <div className="recipient-grid">
          {measures.map(([key, label, min]) => <label key={key}>{label}<input type="number" min={min} step={['kg', 'seconds', 'meters'].includes(key) ? 'any' : '1'} value={exercise[key] ?? ''} onChange={event => editExercise(b, e, { [key]: event.target.value === '' ? null : Number(event.target.value) })} /></label>)}
        </div>
        <label>Lado<select value={exercise.side ?? ''} onChange={event => editExercise(b, e, { side: event.target.value as ExerciseTarget['side'] || null })}>
          <option value="">Sin especificar</option><option value="bilateral">Bilateral</option><option value="left">Izquierdo</option><option value="right">Derecho</option><option value="alternating">Alterno</option>
        </select></label>
        <label>Convención de carga<select value={exercise.load_convention ?? ''} onChange={event => editExercise(b, e, { load_convention: event.target.value as ExerciseTarget['load_convention'] || null })}>
          <option value="">Sin especificar</option><option value="total">Total</option><option value="per_side">Por lado</option><option value="bodyweight">Peso corporal</option>
        </select></label>
        <label>Intensidad<input value={exercise.intensity ?? ''} onChange={event => editExercise(b, e, { intensity: event.target.value || null })} /></label>
        <label>Zona<input value={exercise.zone ?? ''} onChange={event => editExercise(b, e, { zone: event.target.value || null })} /></label>
        <label>Indicaciones<textarea value={exercise.instructions} maxLength={2000} onChange={event => editExercise(b, e, { instructions: event.target.value })} /></label>
        <button type="button" className="secondary" onClick={() => editBlock(b, { exercises: block.exercises.filter((_, i) => i !== e) })}>Retirar ejercicio</button>
        {e > 0 && <button type="button" className="secondary" onClick={() => {
          const exercises = [...block.exercises]; [exercises[e - 1], exercises[e]] = [exercises[e], exercises[e - 1]]; editBlock(b, { exercises })
        }}>Subir ejercicio</button>}
      </fieldset>)}
      <button type="button" onClick={() => editBlock(b, { exercises: [...block.exercises, { id: crypto.randomUUID(), name: '', instructions: '' }] })}>Añadir ejercicio</button>
      <button type="button" className="secondary" onClick={() => change(blocks.filter((_, i) => i !== b))}>Retirar bloque</button>
      {b > 0 && <button type="button" className="secondary" onClick={() => {
        const value = [...blocks]; [value[b - 1], value[b]] = [value[b], value[b - 1]]; change(value)
      }}>Subir bloque</button>}
    </fieldset>)}
    <button type="button" onClick={() => change([...blocks, { id: crypto.randomUUID(), title: '', instructions: '', exercises: [] }])}>Añadir bloque</button>
    <small>Los campos vacíos quedan sin especificar. Los pasos en casa deben incluir indicaciones detalladas.</small>
  </fieldset>
}

export function PrescriptionDetails({ blocks }: { blocks?: PrescriptionBlock[] }) {
  return <>{blocks?.map(block => <div key={block.id} className="record">
    <h4>{block.title}</h4><p>{block.instructions}</p>
    <ol>{block.exercises.map(exercise => <li key={exercise.id}>
      <strong>{exercise.name}</strong>{measures.map(([key, label]) => exercise[key] == null ? null : <span key={key}> · {label}: {exercise[key]}</span>)}
      {exercise.side && <span> · {({ bilateral: 'Bilateral', left: 'Izquierdo', right: 'Derecho', alternating: 'Alterno' })[exercise.side]}</span>}
      {exercise.load_convention && <span> · Carga: {({ total: 'total', per_side: 'por lado', bodyweight: 'peso corporal' })[exercise.load_convention]}</span>}
      {exercise.intensity && <p>Intensidad: {exercise.intensity}</p>}{exercise.zone && <p>Zona: {exercise.zone}</p>}
      <p>{exercise.instructions}</p>
    </li>)}</ol>
  </div>)}</>
}
