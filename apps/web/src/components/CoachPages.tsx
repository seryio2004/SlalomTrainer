import { DisciplinePrescription, readDiscipline } from './DisciplinePrescription'
import { FormEvent, useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { availableDays, dayLabel } from '../planningTypes'
import type { Planning } from '../planningTypes'
import { useResource } from '../useResource'
import { dateTime, place, trainingTypes } from '../format'
import { PrescriptionEditor, PrescriptionDetails } from './PrescriptionEditor'
import type { Prescription, PrescriptionBlock, Athlete, Group, Session, Summary } from '../types'
import { FollowUp } from './FollowUp'
import { Calendar } from './Calendar'
import { PrescriptionLibrary } from './PrescriptionLibrary'
import { SessionEditor } from './SessionEditor'

type CalendarPageProps = {
  sessions: Session[]
  summary: Summary | null
  create: () => void
  loadSummary: (id: string) => Promise<void>
  editSession: (id: string, body: object) => Promise<void>
  cancelSession: (id: string, version: number) => Promise<void>
}

export function CoachCalendarPage({
  sessions,
  summary,
  create,
  loadSummary,
  editSession,
  cancelSession,
}: CalendarPageProps) {
  return (
    <>
      <Calendar items={sessions} />
      <section>
        <div className="section-head">
          <div>
            <p className="eyebrow">Club</p>
            <h2>Entrenos programados</h2>
          </div>
          <button onClick={create}>+ Nuevo entreno</button>
        </div>

        {sessions.length ? sessions.map(session => (
          <article className="item" key={session.id}>
            <div className="section-head">
              <div>
                <h3>{session.title}</h3>
                <p className="muted">
                  {dateTime(session.scheduled_start)} · {session.group_name ?? 'Individual'}
                </p>
              </div>
              <span className={`badge ${session.status === 'cancelled' ? 'status-cancelled' : ''}`}>
                {session.status === 'cancelled' ? 'Cancelado' : place(session.venue)}
              </span>
            </div>
            <details className="session-content">
              <summary>Contenido del entreno</summary>
            <PrescriptionDetails blocks={session.prescription.blocks} />
            <p>{session.prescription.instructions || 'Sin instrucciones adicionales.'}</p>
            {!!session.prescription.steps?.length && (
              <ol>
                {session.prescription.steps.map((step, index) => (
                  <li key={index}>{step}</li>
                ))}
              </ol>
            )}
            </details>
            {session.status !== 'cancelled' && session.version && (
              <SessionEditor
                session={session}
                save={editSession}
                cancel={cancelSession}
              />
            )}
            <button className="text-button" onClick={() => loadSummary(session.id)}>
              Ver seguimiento →
            </button>
            {summary?.id === session.id && (
              <div className="record">
                <p>
                  Completados: {summary.counts.completed} ·
                  Parciales: {summary.counts.partial} ·
                  No realizados: {summary.counts.skipped} ·
                  Pendientes: {summary.counts.planned}
                </p>
                <p>
                  RPE medio: {summary.mean_rpe?.toFixed(1) ?? 'sin datos'} (n={summary.rpe_sample}) · Molestias: {summary.pain_count} · Sin feedback: {summary.without_feedback}<br />
                  Carga registrada: {summary.known_load ?? 'sin datos'} ·
                  Registros con datos: {summary.load_coverage} / {summary.assigned}
                </p>
              </div>
            )}
          </article>
        )) : (
          <p className="muted">Aún no has programado entrenos.</p>
        )}
      </section>
    </>
  )
}

type OrganizePageProps = {
  base: string
  initialDay: string
  athletes: Athlete[]
  groups: Group[]
  publish: (data: object) => Promise<void>
}

export function OrganizePage({ base, initialDay, athletes, groups, publish }: OrganizePageProps) {
  const formRef = useRef<HTMLFormElement>(null)
  const [loadedPrescription, setLoadedPrescription] = useState<Prescription | null>(null)
  const [loadVersion, setLoadVersion] = useState(0)
  const [blocks, setBlocks] = useState<PrescriptionBlock[]>([])
  const [venue, setVenue] = useState('club')
  const [trainingType, setTrainingType] = useState('water')
  const [groupId, setGroupId] = useState('')
  const [athleteIds, setAthleteIds] = useState<string[]>([])
  const [planDayId, setPlanDayId] = useState(initialDay)
  const [scheduledLocal, setScheduledLocal] = useState('')
  const [preview, setPreview] = useState<{ body: object; athletes: Athlete[] } | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const planning = useResource<Planning>(`${base}/planning`)
  const days = planning.data ? availableDays(planning.data) : []
  const needsSteps = venue === 'home' || (trainingType !== 'water' && trainingType !== 'rest')

  useEffect(() => {
    const day = planning.data?.days.find(item => item.id === initialDay)
    if (day) setScheduledLocal(`${day.local_date}T17:00`)
  }, [planning.data, initialDay])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const date = new Date(scheduledLocal)
    if (Number.isNaN(date.getTime())) {
      setError('Indica una fecha y hora válidas')
      return
    }
    const body = {
      title: form.get('title'),
      training_type: form.get('type'),
      venue,
      scheduled_start: date.toISOString(),
      planned_minutes: Number(form.get('minutes')),
      instructions: form.get('instructions'),
      objective: form.get('objective'), blocks, details: readDiscipline(form),
      steps: String(form.get('steps') ?? '')
        .split('\n')
        .map(step => step.trim())
        .filter(Boolean),
      athlete_ids: athleteIds,
      group_id: groupId || null,
      plan_day_id: planDayId || null,
    }
    setBusy(true)
    setError('')
    try {
      const result = await api<{ athletes: Athlete[] }>(`${base}/sessions/preview`, {
        method: 'POST', body: JSON.stringify(body),
      })
      setPreview({ body, athletes: result.athletes })
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'No se pudo previsualizar')
    } finally {
      setBusy(false)
    }
  }

  async function confirmPublication() {
    if (!preview) return
    setBusy(true)
    try {
      await publish({ ...preview.body, preview_athlete_ids: preview.athletes.map(item => item.id) })
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'No se pudo publicar')
      setPreview(null)
    } finally {
      setBusy(false)
    }
  }

  function toggleAthlete(id: string, checked: boolean) {
    setAthleteIds(current => checked
      ? [...current, id]
      : current.filter(athleteId => athleteId !== id))
  }

  return (
    <section className="form-section">
      <p className="eyebrow">Planificación</p>
      <h2>Nuevo entreno</h2>
      {(error || planning.error) && <p className="error" role="alert">{error || planning.error}</p>}
      <form ref={formRef} onSubmit={submit} onChange={() => setPreview(null)}>
        <fieldset className="form-group">
        <legend>1. Datos del entreno</legend>
        <label>
          Día de planificación
          <select value={planDayId} onChange={event => {
            setPlanDayId(event.target.value)
            const day = days.find(item => item.id === event.target.value)
            if (day) setScheduledLocal(`${day.local_date}T${scheduledLocal.slice(11) || '17:00'}`)
          }}>
            <option value="">Sesión independiente</option>
            {days.map(day => (
              <option key={day.id} value={day.id}>{dayLabel(planning.data!, day)}</option>
            ))}
          </select>
          <small>Crea temporadas, planes y días desde Planes y temporadas.</small>
        </label>
        <div className="form-row">
          <label>
            Título
            <input name="title" required />
          </label>
          <label>
            Tipo
            <select name="type" value={trainingType} onChange={event => setTrainingType(event.target.value)}>
              {Object.entries(trainingTypes).map(([value, label]) => (
                <option value={value} key={value}>{label}</option>
              ))}
            </select>
          </label>
        </div>

        <div className="form-row">
          <label>
            Fecha y hora · {Intl.DateTimeFormat().resolvedOptions().timeZone}
            <input
              name="start" type="datetime-local" required value={scheduledLocal}
              onChange={event => setScheduledLocal(event.target.value)}
            />
          </label>
          <label>
            Duración prevista (minutos)
            <input name="minutes" type="number" min="0" max="1440" required />
          </label>
        </div>

        </fieldset>
        <fieldset className="form-group">
        <legend>2. Contenido y lugar</legend>
        <fieldset>
          <legend>Lugar</legend>
          <label className="choice">
            <input
              type="radio"
              checked={venue === 'club'}
              onChange={() => setVenue('club')}
            />
            En el club
          </label>
          <label className="choice">
            <input
              type="radio"
              checked={venue === 'home'}
              onChange={() => setVenue('home')}
            />
            En casa
          </label>
        </fieldset>

        <PrescriptionLibrary base={base} read={() => {
          if (!formRef.current) return null
          const form = new FormData(formRef.current)
          return { title: form.get('title'), training_type: trainingType, venue,
            planned_minutes: Number(form.get('minutes')), instructions: form.get('instructions'), objective: form.get('objective'), blocks, details: readDiscipline(form),
            steps: String(form.get('steps') ?? '').split('\n').map(value => value.trim()).filter(Boolean), scheduled_start: new Date().toISOString() }
        }} load={value => {
          setLoadedPrescription(value); setLoadVersion(current => current + 1)
          setPreview(null); setVenue(value.venue ?? 'club'); setTrainingType(value.training_type ?? 'water'); setBlocks(value.blocks ?? [])
          for (const [key, text] of Object.entries({ title: value.title, minutes: value.planned_minutes, instructions: value.instructions, objective: value.objective, steps: value.steps?.join('\n') })) {
            const input = formRef.current?.elements.namedItem(key)
            if (input instanceof HTMLInputElement || input instanceof HTMLTextAreaElement) input.value = String(text ?? '')
          }
        }} add={exercise => {
          setPreview(null)
          setBlocks(current => current.length ? current.map((block, index) => index === current.length - 1 ? { ...block, exercises: [...block.exercises, exercise] } : block) : [{ id: crypto.randomUUID(), title: 'Principal', instructions: '', exercises: [exercise] }])
        }} />
        <DisciplinePrescription key={loadVersion} kind={trainingType} details={loadedPrescription?.details} />
        <label>Objetivo<textarea name="objective" maxLength={2000} /></label>
        <PrescriptionEditor blocks={blocks} change={value => { setBlocks(value); setPreview(null) }} />
        <label>
          Contenido e instrucciones generales
          <textarea name="instructions" rows={3} maxLength={4000} />
        </label>
        {needsSteps && (
          <label>
            Ejercicios e indicaciones, un paso por línea
            <textarea
              name="steps"
              defaultValue={loadedPrescription?.steps?.join('\n')}
              rows={5}
              placeholder={
                'Sentadilla | 3x12 reps | descanso 60s\n' +
                'Plancha | 3x30s | descanso 20s'
              }
              required={venue === 'home'}
            />
            <small>Formato: ejercicio | series x repeticiones o segundos | descanso en segundos.<br />Ejemplo: Sentadilla | 3x12 reps | descanso 60s. La guía usará automáticamente estas series y descansos.</small>
          </label>
        )}

        </fieldset>
        <fieldset className="form-group">
        <legend>3. Destinatarios</legend>
        <label>
          Grupo
          <select value={groupId} onChange={event => setGroupId(event.target.value)}>
            <option value="">Sin grupo</option>
            {groups.map(group => (
              <option key={group.id} value={group.id}>{group.name}</option>
            ))}
          </select>
        </label>

        <fieldset>
          <legend>Deportistas adicionales</legend>
          <div className="recipient-grid">
          {athletes.map(athlete => (
            <label className="choice" key={athlete.id}>
              <input
                type="checkbox"
                checked={athleteIds.includes(athlete.id)}
                onChange={event => toggleAthlete(athlete.id, event.target.checked)}
              />
              {athlete.name}
            </label>
          ))}
          </div>
          {!athletes.length && <p className="muted">No hay deportistas disponibles.</p>}
        </fieldset>
        </fieldset>
        <div className="form-actions">
        <button disabled={busy || planning.loading || (!groupId && !athleteIds.length)}>
          {busy ? 'Procesando…' : 'Previsualizar destinatarios'}
        </button>
        </div>
        {preview && (
          <div className="publication-preview" role="status">
            <h3>Se asignará a {preview.athletes.length} deportistas</h3>
            <ul>{preview.athletes.map(person => <li key={person.id}>{person.name}</li>)}</ul>
            <p className="muted">Cada persona recibirá una única asignación, aunque también esté seleccionada individualmente.</p>
            <button type="button" disabled={busy} onClick={confirmPublication}>
              Confirmar publicación
            </button>
          </div>
        )}
      </form>
    </section>
  )
}

type TeamPageProps = {
  base: string
  athletes: Athlete[]
  groups: Group[]
  openAthlete: (id: string) => Promise<void>
}

export function TeamPage({ base, athletes, groups, openAthlete }: TeamPageProps) {
  const [selectedGroups, setSelectedGroups] = useState<string[]>([])
  return (
    <>
      <section>
        <p className="eyebrow">Equipo</p>
        <h2>Deportistas</h2>
        <div className="people">
          {athletes.map(athlete => (
            <article className="person" key={athlete.id}>
              <span className="avatar">{athlete.name.charAt(0)}</span>
              <strong>{athlete.name}</strong>
              <button
                className="text-button"
                onClick={() => openAthlete(athlete.id)}
              >
                Abrir su vista →
              </button>
            </article>
          ))}
        </div>
        {!athletes.length && <p>No hay deportistas autorizados.</p>}
      </section>

      <section>
        <h2>Seguimiento por grupos</h2>
        {groups.map(group => <label className="choice" key={group.id}><input type="checkbox" checked={selectedGroups.includes(group.id)} onChange={event => setSelectedGroups(current => event.target.checked ? [...current, group.id] : current.filter(id => id !== group.id))} />{group.name}</label>)}
        {selectedGroups.length ? <FollowUp base={base} groupIds={selectedGroups} /> : <p>Selecciona grupos para consultar su seguimiento sin duplicar deportistas.</p>}
        <h2>Grupos autorizados</h2>
        {groups.map(group => (
          <article className="item" key={group.id}>
            <h3>{group.name}</h3>
            <p>{group.description}</p>
            <p className="muted">
              {group.athlete_ids
                .map(id => athletes.find(athlete => athlete.id === id)?.name)
                .filter(Boolean)
                .join(', ')}
            </p>
          </article>
        ))}
      </section>
    </>
  )
}
