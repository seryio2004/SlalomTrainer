import { FormEvent, useState } from 'react'
import type { Period, Planning } from '../planningTypes'
import type { Session } from '../types'
import { useResource } from '../useResource'
import { dateTime } from '../format'

type Props = {
  base: string
  admin: boolean
  coach: boolean
  sessions: Session[]
  organize: (dayId: string) => void
}

type PeriodFormProps = {
  title: string
  parent?: Period
  season?: boolean
  saving: boolean
  create: (body: object) => Promise<boolean>
}

function PeriodForm({ title, parent, season, saving, create }: PeriodFormProps) {
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const element = event.currentTarget
    const form = new FormData(element)
    const body = {
      name: form.get('name'),
      starts_on: form.get('starts_on'),
      ends_on: form.get('ends_on'),
      objectives: form.get('objectives'),
      ...(season ? {
        age_reference_date: form.get('age_reference_date'),
        status: form.get('status'),
      } : {}),
    }
    if (await create(body)) element.reset()
  }

  return (
    <details className="disclosure">
      <summary>{title}</summary>
      <form onSubmit={submit}>
        <label>Nombre<input name="name" maxLength={160} required /></label>
        <div className="form-row">
          <label>
            Inicio
            <input
              name="starts_on" type="date" required
              min={parent?.starts_on} max={parent?.ends_on}
              defaultValue={parent?.starts_on}
            />
          </label>
          <label>
            Fin
            <input
              name="ends_on" type="date" required
              min={parent?.starts_on} max={parent?.ends_on}
              defaultValue={parent?.ends_on}
            />
          </label>
        </div>
        {season && (
          <div className="form-row">
            <label>
              Fecha de referencia para las edades
              <input name="age_reference_date" type="date" required />
            </label>
            <label>
              Estado
              <select name="status">
                <option value="draft">Borrador</option>
                <option value="active">Activa</option>
              </select>
            </label>
          </div>
        )}
        <label>Objetivos<textarea name="objectives" maxLength={2000} /></label>
        <button disabled={saving}>{saving ? 'Guardando…' : title}</button>
      </form>
    </details>
  )
}

function PeriodDetails({ period }: { period: Period }) {
  return (
    <div className="period-details">
      <p className="muted">{period.starts_on} — {period.ends_on}</p>
      {period.objectives && <p>{period.objectives}</p>}
    </div>
  )
}

export function PlanningPage({ base, admin, coach, sessions, organize }: Props) {
  const { data, error, loading, saving, mutate, reload } = useResource<Planning>(`${base}/planning`)
  const [seasonId, setSeasonId] = useState('')
  const [phaseId, setPhaseId] = useState('')
  const [planId, setPlanId] = useState('')
  const [cycleId, setCycleId] = useState('')

  if (!data) {
    return (
      <section>
        {loading ? <p>Cargando planificación…</p> : (
          <><p role="alert" className="error">{error}</p><button onClick={() => void reload().catch(() => {})}>Reintentar</button></>
        )}
      </section>
    )
  }

  const season = data.seasons.find(item => item.id === seasonId)
    ?? data.seasons.find(item => item.status === 'active') ?? data.seasons[0]
  const phases = data.phases.filter(item => item.season_id === season?.id)
  const phase = phases.find(item => item.id === phaseId) ?? phases[0]
  const plans = data.plans.filter(item => item.phase_id === phase?.id)
  const plan = plans.find(item => item.id === planId) ?? plans[0]
  const cycles = data.microcycles.filter(item => item.plan_id === plan?.id)
  const cycle = cycles.find(item => item.id === cycleId) ?? cycles[0]
  const days = data.days.filter(item => item.microcycle_id === cycle?.id)
  const open = season && season.status !== 'closed'
  const editablePlan = open && plan?.status !== 'archived'

  function create(resource: string, body: object) {
    return mutate(`${base}/planning/${resource}`, body)
  }

  return (
    <>
      {error && <p className="error" role="alert">{error}</p>}
      <section>
        <h2>Temporada y fase</h2>
        <p className="muted">Organiza el trabajo por períodos. Zona horaria del club: {data.timezone}.</p>
        {season ? (
          <>
            <div className="form-row">
              <label>
                Temporada
                <select value={season.id} onChange={event => {
                  setSeasonId(event.target.value)
                  setPhaseId('')
                  setPlanId('')
                  setCycleId('')
                }}>
                  {data.seasons.map(item => (
                    <option key={item.id} value={item.id}>
                      {item.name} · {item.status === 'closed' ? 'Cerrada' : item.status === 'active' ? 'Activa' : 'Borrador'}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Fase
                <select value={phase?.id ?? ''} onChange={event => {
                  setPhaseId(event.target.value)
                  setPlanId('')
                  setCycleId('')
                }}>
                  {!phases.length && <option value="">Todavía no hay fases</option>}
                  {phases.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
                </select>
              </label>
            </div>
            <PeriodDetails period={phase ?? season} />
            {!open && <p className="note">Temporada cerrada. Puedes consultar su planificación.</p>}
            {admin && season.status === 'draft' && (
              <button disabled={saving} onClick={() => void mutate(
                `${base}/planning/seasons/${season.id}`, { status: 'active' }, 'PATCH',
              )}>Activar temporada</button>
            )}
            {admin && open && (
              <details className="disclosure">
                <summary>Cerrar esta temporada</summary>
                <p>Se bloquearán nuevas sesiones y cambios de planificación. El histórico seguirá disponible.</p>
                <button className="secondary" disabled={saving} onClick={() => void mutate(
                  `${base}/planning/seasons/${season.id}`, { status: 'closed' }, 'PATCH',
                )}>Confirmar cierre</button>
              </details>
            )}
          </>
        ) : <p>No hay temporadas. Un administrador debe crear la primera.</p>}
        {admin && <PeriodForm title="Crear temporada" season saving={saving} create={body => create('seasons', body)} />}
        {admin && open && (
          <PeriodForm
            key={season.id} title="Añadir fase" parent={season} saving={saving}
            create={body => create('phases', { ...body, season_id: season.id })}
          />
        )}
      </section>

      {coach && phase && (
        <section>
          <h2>Planes y microciclos</h2>
          {plan ? (
            <>
              <div className="form-row">
                <label>
                  Plan
                  <select value={plan.id} onChange={event => {
                    setPlanId(event.target.value)
                    setCycleId('')
                  }}>
                    {plans.map(item => (
                      <option key={item.id} value={item.id}>
                        {item.name}{item.status === 'archived' ? ' · Archivado' : ''}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Microciclo
                  <select value={cycle?.id ?? ''} onChange={event => setCycleId(event.target.value)}>
                    {!cycles.length && <option value="">Todavía no hay microciclos</option>}
                    {cycles.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
                  </select>
                </label>
              </div>
              <PeriodDetails period={cycle ?? plan} />
              {editablePlan && (
                <details className="disclosure">
                  <summary>Archivar plan</summary>
                  <p>El plan quedará disponible para consulta y no admitirá nuevas publicaciones.</p>
                  <button className="secondary" disabled={saving} onClick={() => void create(`plans/${plan.id}/archive`, {})}>
                    Confirmar archivo
                  </button>
                </details>
              )}
            </>
          ) : <p>No tienes planes en esta fase.</p>}
          {open && (
            <PeriodForm
              key={phase.id} title="Crear plan" parent={phase} saving={saving}
              create={body => create('plans', { ...body, phase_id: phase.id })}
            />
          )}
          {plan && editablePlan && (
            <PeriodForm
              key={plan.id} title="Añadir microciclo" parent={plan} saving={saving}
              create={body => create('microcycles', { ...body, plan_id: plan.id })}
            />
          )}
        </section>
      )}

      {coach && cycle && (
        <section>
          <h2>Días de {cycle.name}</h2>
          {days.length ? days.map(day => (
            <article className="item" key={day.id}>
              <div className="section-head">
                <h3>{day.local_date}</h3>
                {editablePlan && <button onClick={() => organize(day.id)}>Programar entreno</button>}
              </div>
              {sessions.filter(session => session.plan_day_id === day.id).map(session => (
                <p key={session.id}>{dateTime(session.scheduled_start)} · {session.title}</p>
              ))}
              {!sessions.some(session => session.plan_day_id === day.id) && <p className="muted">Sin sesiones.</p>}
            </article>
          )) : <p>Añade los días que vas a planificar.</p>}
          {editablePlan && (
            <form className="inline-form" key={cycle.id} onSubmit={async event => {
              event.preventDefault()
              const form = new FormData(event.currentTarget)
              await create('days', { microcycle_id: cycle.id, local_date: form.get('date') })
            }}>
              <label>
                Fecha del día
                <input name="date" type="date" min={cycle.starts_on} max={cycle.ends_on} required />
              </label>
              <button disabled={saving}>Añadir día</button>
            </form>
          )}
        </section>
      )}
    </>
  )
}
