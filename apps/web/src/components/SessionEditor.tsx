import { DisciplinePrescription, readDiscipline } from './DisciplinePrescription'
import { FormEvent, useState } from 'react'
import { trainingTypes } from '../format'
import { PrescriptionEditor } from './PrescriptionEditor'
import type { PrescriptionBlock, Session } from '../types'

function localDateTime(value: string) {
  const date = new Date(value)
  const pad = (number: number) => String(number).padStart(2, '0')
  return [
    date.getFullYear(),
    pad(date.getMonth() + 1),
    pad(date.getDate()),
  ].join('-') + `T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

type Props = {
  session: Session
  save: (id: string, body: object) => Promise<void>
  cancel: (id: string, version: number) => Promise<void>
}

export function SessionEditor({ session, save, cancel }: Props) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [blocks, setBlocks] = useState<PrescriptionBlock[]>(session.prescription.blocks ?? [])
  const [trainingType, setTrainingType] = useState(session.training_type)
  const [venue, setVenue] = useState(session.venue)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const start = new Date(String(form.get('start')))
    if (Number.isNaN(start.getTime())) {
      setError('Indica una fecha y hora válidas')
      return
    }
    setBusy(true)
    setError('')
    try {
      await save(session.id, {
        version: session.version,
        title: form.get('title'),
        training_type: form.get('type'),
        venue,
        scheduled_start: start.toISOString(),
        planned_minutes: Number(form.get('minutes')),
        instructions: form.get('instructions'),
        objective: form.get('objective'), blocks, details: readDiscipline(form),
        steps: String(form.get('steps') ?? '').split('\n').map(step => step.trim()).filter(Boolean),
      })
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'No se pudo guardar')
    } finally {
      setBusy(false)
    }
  }

  async function confirmCancel() {
    if (!window.confirm('¿Cancelar este entreno para todos sus deportistas?')) return
    setBusy(true)
    setError('')
    try {
      await cancel(session.id, session.version!)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'No se pudo cancelar')
    } finally {
      setBusy(false)
    }
  }

  return (
    <details className="session-editor">
      <summary>Editar o cancelar entreno</summary>
      <form onSubmit={submit}>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="form-row">
          <label>Título<input name="title" defaultValue={session.title} required /></label>
          <label>Tipo
            <select name="type" value={trainingType} onChange={event => setTrainingType(event.target.value)}>
              {Object.entries(trainingTypes).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>
        </div>
        <div className="form-row">
          <label>Fecha y hora
            <input name="start" type="datetime-local" defaultValue={localDateTime(session.scheduled_start)} required />
          </label>
          <label>Duración prevista (minutos)
            <input name="minutes" type="number" min="0" max="1440" defaultValue={session.planned_minutes} required />
          </label>
        </div>
        <label>Lugar
          <select value={venue} onChange={event => setVenue(event.target.value)}>
            <option value="club">En el club</option>
            <option value="home">En casa</option>
          </select>
        </label>
        <DisciplinePrescription kind={trainingType} details={session.prescription.details} />
        <label>Objetivo<textarea name="objective" maxLength={2000} defaultValue={session.prescription.objective} /></label>
        <PrescriptionEditor blocks={blocks} change={setBlocks} />
        <label>Contenido e instrucciones
          <textarea name="instructions" rows={3} maxLength={4000} defaultValue={session.prescription.instructions} />
        </label>
        <label>Indicaciones paso a paso, una por línea
          <textarea name="steps" rows={4} required={venue === 'home'} defaultValue={session.prescription.steps?.join('\n') ?? ''} />
          <small>Formato para la guía: ejercicio | series x repeticiones o segundos | descanso. Ejemplo: Sentadilla | 3x12 reps | descanso 60s.</small>
        </label>
        <div className="session-editor-actions">
          <button disabled={busy}>Guardar cambios</button>
          <button type="button" className="secondary" disabled={busy} onClick={confirmCancel}>
            Cancelar entreno
          </button>
        </div>
      </form>
    </details>
  )
}
