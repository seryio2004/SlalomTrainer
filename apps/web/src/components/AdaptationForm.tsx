import { DisciplinePrescription, readDiscipline } from './DisciplinePrescription'
import { FormEvent, useState } from 'react'
import { api } from '../api'
import type { Assignment, PrescriptionBlock } from '../types'
import { PrescriptionEditor, PrescriptionDetails } from './PrescriptionEditor'

export function AdaptationForm({ base, item }: { base: string; item: Assignment }) {
  const [current, setCurrent] = useState(item)
  const [blocks, setBlocks] = useState<PrescriptionBlock[]>(item.prescription.blocks ?? [])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    setBusy(true); setError(''); setSaved(false)
    try {
      const updated = await api<Assignment>(`${base}/assignments/${item.id}/prescription`, { method: 'PUT', body: JSON.stringify({
        version: current.version, reason: data.get('reason'), prescription: {
          title: current.title, training_type: current.training_type, venue: current.venue,
          scheduled_start: current.scheduled_start, planned_minutes: Number(data.get('minutes')),
          instructions: data.get('instructions'), objective: data.get('objective'), blocks, details: readDiscipline(data),
          steps: String(data.get('steps') ?? '').split('\n').map(step => step.trim()).filter(Boolean),
        },
      }) })
      setCurrent(updated); setSaved(true)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'No se pudo adaptar') }
    finally { setBusy(false) }
  }
  return <details><summary>Adaptar prescripción individual</summary>
    {error && <p className="error" role="alert">{error}</p>}
    {saved && <p role="status">Adaptación guardada para esta persona.</p>}
    <form onSubmit={save}><fieldset disabled={busy}>
      <label>Motivo<textarea name="reason" required maxLength={500} /></label>
      <DisciplinePrescription kind={current.training_type} details={current.prescription.details} />
      <label>Objetivo<textarea name="objective" defaultValue={current.prescription.objective} maxLength={2000} /></label>
      <label>Duración prevista (min)<input type="number" name="minutes" min="0" max="1440" defaultValue={current.planned_minutes} required /></label>
      <label>Instrucciones<textarea name="instructions" defaultValue={current.prescription.instructions} maxLength={4000} /></label>
      <label>Pasos, uno por línea<textarea name="steps" defaultValue={current.prescription.steps?.join('\n')} required={current.venue === 'home'} /></label>
      <PrescriptionEditor blocks={blocks} change={setBlocks} />
      <button>Guardar adaptación</button>
    </fieldset></form>
    <details><summary>Prescripción original</summary><p>{current.original_prescription?.instructions}</p><PrescriptionDetails blocks={current.original_prescription?.blocks} /></details>
    {current.prescription_revisions?.map(revision => <p key={revision.version}>Revisión {revision.version} · {new Date(revision.at).toLocaleString('es-ES')} · {revision.reason}</p>)}
  </details>
}
