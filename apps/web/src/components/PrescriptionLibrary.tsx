import { useState } from 'react'
import { useResource } from '../useResource'
import type { ExerciseTarget, Prescription } from '../types'

type Template = { id: string; prescription: Prescription; version: number; active: boolean }
type Exercise = { id: string; name: string; instructions: string; measurement: string; reference: boolean; active: boolean; version: number }
export function PrescriptionLibrary({ base, read, load, add }: {
  base: string; read: () => object | null; load: (value: Prescription) => void; add: (value: ExerciseTarget) => void
}) {
  const templates = useResource<Template[]>(`${base}/templates`)
  const exercises = useResource<Exercise[]>(`${base}/exercises`)
  const [selected, setSelected] = useState('')
  const [name, setName] = useState('')
  const [measurement, setMeasurement] = useState('repetitions')
  const [reference, setReference] = useState(false)
  const [message, setMessage] = useState('')
  const template = templates.data?.find(row => row.id === selected)
  async function save(revise: boolean) {
    const prescription = read()
    if (!prescription) return
    if (await templates.mutate(`${base}/templates${revise && template ? `/${template.id}` : ''}`, { prescription, version: revise ? template?.version : 0 }, revise ? 'PUT' : 'POST')) setMessage('Plantilla guardada. Las sesiones publicadas conservan su contenido.')
  }
  return <details><summary>Biblioteca de plantillas y ejercicios</summary>
    {(templates.error || exercises.error) && <p className="error" role="alert">{templates.error || exercises.error}</p>}
    {message && <p role="status">{message}</p>}
    {templates.loading || exercises.loading ? <p>Cargando biblioteca…</p> : <>
      <label>Plantilla<select value={selected} onChange={event => setSelected(event.target.value)}><option value="">Seleccionar</option>{templates.data?.filter(row => row.active).map(row => <option key={row.id} value={row.id}>{row.prescription.title} · v{row.version}</option>)}</select></label>
      <button type="button" disabled={!template} onClick={() => template && load(template.prescription)}>Usar plantilla</button>
      <button type="button" disabled={templates.saving} onClick={() => void save(false)}>Guardar contenido como nueva plantilla</button>
      <button type="button" disabled={!template || templates.saving} onClick={() => void save(true)}>Crear revisión de la plantilla seleccionada</button>
      <button type="button" disabled={!template || templates.saving} onClick={() => template && void templates.mutate(`${base}/templates`, { prescription: { ...template.prescription, scheduled_start: new Date().toISOString() } })}>Duplicar plantilla</button>
      {!templates.data?.length && <p>No hay plantillas todavía.</p>}
      <h4>Catálogo de ejercicios</h4>
      <label>Nuevo ejercicio<input value={name} maxLength={160} onChange={event => setName(event.target.value)} /></label>
      <label>Medición<select value={measurement} onChange={event => setMeasurement(event.target.value)}><option value="repetitions">Repeticiones</option><option value="time">Tiempo</option><option value="distance">Distancia</option><option value="other">Otra</option></select></label>
      <label className="choice"><input type="checkbox" checked={reference} onChange={event => setReference(event.target.checked)} />Ejercicio de referencia</label>
      <button type="button" disabled={!name.trim() || exercises.saving} onClick={async () => { if (await exercises.mutate(`${base}/exercises`, { name, measurement, reference })) setName('') }}>Crear ejercicio</button>
      {!exercises.data?.length && <p>No hay ejercicios en el catálogo.</p>}
      {exercises.data?.map(exercise => <div key={exercise.id}><span>{exercise.name}{exercise.reference ? ' · referencia' : ''}{!exercise.active ? ' · archivado' : ''}</span>
        {exercise.active && <button type="button" onClick={() => add({ id: crypto.randomUUID(), exercise_id: exercise.id, name: exercise.name, instructions: exercise.instructions })}>Añadir al último bloque</button>}
        <button type="button" className="secondary" disabled={exercises.saving} onClick={() => void exercises.mutate(`${base}/exercises/${exercise.id}`, { ...exercise, id: undefined, active: !exercise.active }, 'PUT')}>{exercise.active ? 'Archivar' : 'Reactivar'}</button>
      </div>)}
    </>}
  </details>
}
