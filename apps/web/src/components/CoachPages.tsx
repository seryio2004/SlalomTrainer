import { FormEvent, useState } from 'react'
import { dateTime, place, trainingTypes } from '../format'
import type { Athlete, Group, Session, Summary } from '../types'
import { Calendar } from './Calendar'

type CalendarPageProps = {
  sessions: Session[]
  summary: Summary | null
  create: () => void
  loadSummary: (id: string) => Promise<void>
}

export function CoachCalendarPage({
  sessions,
  summary,
  create,
  loadSummary,
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
              <span className="badge">{place(session.venue)}</span>
            </div>
            <p>{session.prescription.instructions}</p>
            {!!session.prescription.steps?.length && (
              <ol>
                {session.prescription.steps.map((step, index) => (
                  <li key={index}>{step}</li>
                ))}
              </ol>
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
                  Carga registrada: {summary.known_load} ·
                  Registros con datos: {summary.load_coverage}
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
  athletes: Athlete[]
  groups: Group[]
  publish: (data: {
    title: FormDataEntryValue | null
    training_type: FormDataEntryValue | null
    venue: string
    scheduled_start: string
    planned_minutes: number
    instructions: FormDataEntryValue | null
    steps: string[]
    athlete_ids: string[]
    group_id: string | null
  }) => Promise<void>
}

export function OrganizePage({ athletes, groups, publish }: OrganizePageProps) {
  const [venue, setVenue] = useState('club')
  const [groupId, setGroupId] = useState('')
  const [athleteIds, setAthleteIds] = useState<string[]>([])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    const date = new Date(String(form.get('start')))

    if (Number.isNaN(date.getTime())) {
      throw new Error('Fecha inválida')
    }

    try {
      await publish({
        title: form.get('title'),
        training_type: form.get('type'),
        venue,
        scheduled_start: date.toISOString(),
        planned_minutes: Number(form.get('minutes')),
        instructions: form.get('instructions'),
        steps: String(form.get('steps') ?? '')
          .split('\n')
          .map(step => step.trim())
          .filter(Boolean),
        athlete_ids: athleteIds,
        group_id: groupId || null,
      })
    } catch {
      return
    }

    formElement.reset()
    setVenue('club')
    setGroupId('')
    setAthleteIds([])
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
      <form onSubmit={submit}>
        <div className="form-row">
          <label>
            Título
            <input name="title" required />
          </label>
          <label>
            Tipo
            <select name="type">
              {Object.entries(trainingTypes).map(([value, label]) => (
                <option value={value} key={value}>{label}</option>
              ))}
            </select>
          </label>
        </div>

        <div className="form-row">
          <label>
            Fecha y hora
            <input name="start" type="datetime-local" required />
          </label>
          <label>
            Duración prevista (minutos)
            <input name="minutes" type="number" min="0" max="1440" required />
          </label>
        </div>

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

        <label>
          Contenido e instrucciones generales
          <textarea name="instructions" rows={3} maxLength={4000} />
        </label>
        {venue === 'home' && (
          <label>
            Indicaciones detalladas, un paso por línea
            <textarea
              name="steps"
              rows={5}
              placeholder={
                'Movilidad de hombros durante 2 minutos.\n' +
                'Estiramiento de cadera: 30 segundos por lado.'
              }
              required
            />
            <small>
              Explica cada paso para que se pueda realizar sin entrenador presente.
            </small>
          </label>
        )}

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
        </fieldset>
        <button disabled={!groupId && !athleteIds.length}>Publicar entreno</button>
      </form>
    </section>
  )
}

type TeamPageProps = {
  athletes: Athlete[]
  groups: Group[]
  openAthlete: (id: string) => Promise<void>
}

export function TeamPage({ athletes, groups, openAthlete }: TeamPageProps) {
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
