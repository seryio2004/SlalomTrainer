import { AdaptationForm } from './AdaptationForm'
import { useState } from 'react'
import { dateTime, hour } from '../format'
import type { Assignment, Dashboard } from '../types'
import { Calendar } from './Calendar'
import { PersonalExport } from './PersonalExport'
import { CalendarExport } from './CalendarExport'
import { GoogleCalendarSync } from './GoogleCalendarSync'
import { FeedbackForm } from './FeedbackForm'
import { RecoveryPage } from './RecoveryPage'
import { FollowUp } from './FollowUp'
import { TrainingLoad } from './TrainingLoad'
import { WorkoutDetails, WorkoutRow } from './WorkoutCard'

type Props = {
  dashboard: Dashboard
  editable: boolean
  base: string
  report: (id: string, body: object) => Promise<void>
  openWorkout: (id: string) => void
}

const fatigueNames: Record<string, string> = {
  very_low: 'Muy baja',
  low: 'Baja',
  moderate: 'Moderada',
  high: 'Alta',
  very_high: 'Muy alta',
}

const fatiguePositions: Record<string, string> = {
  very_low: '12%',
  low: '31%',
  moderate: '50%',
  high: '69%',
  very_high: '88%',
}

function Fatigue({ dashboard }: { dashboard: Dashboard }) {
  const { band, available } = dashboard.fatigue
  const label = fatigueNames[band]

  return (
    <section className="fatigue-panel">
      <p className="eyebrow">Estado actual</p>
      <h2>Fatiga actual</h2>
      {available ? (
        <>
          <p>
            Orientación según entrenos realizados y sensaciones recientes:{' '}
            <strong>{label}</strong>
          </p>
          <div className="fatigue" role="img" aria-label={`Fatiga ${label}`}>
            <span style={{ left: fatiguePositions[band] }} />
          </div>
          <div className="scale">
            <span>Menor fatiga</span>
            <span>Mayor fatiga</span>
          </div>
        </>
      ) : (
        <p className="muted">Aún no hay suficientes registros para mostrar una tendencia.</p>
      )}
    </section>
  )
}

export function AthleteView({ dashboard, editable, base, report, openWorkout }: Props) {
  const [openFeedbackId, setOpenFeedbackId] = useState('')
  const [showPending, setShowPending] = useState(false)
  const [showComplete, setShowComplete] = useState(false)
  const assignments = [...dashboard.assignments].sort(
    (a, b) => new Date(a.scheduled_start).getTime() - new Date(b.scheduled_start).getTime(),
  )
  const pending = assignments.filter(item => item.status === 'planned')
  const next = pending.find(
    item => new Date(item.scheduled_start).getTime() >= Date.now(),
  ) ?? pending[0]
  const later = pending.filter(item => item.id !== next?.id)
  const complete = [...assignments].reverse()

  function reportAction(item: Assignment) {
    if (!editable) {
      return item.status === 'planned' && !item.execution_state
        ? <AdaptationForm base={base} item={item} /> : null
    }

    return (
      <>
        <div className="workout-actions">
        {item.status === 'planned' && <button type="button" onClick={() => openWorkout(item.id)}>Realizar entreno</button>}
        <button type="button" className="secondary" onClick={() => setOpenFeedbackId(item.id)}>
          {item.execution_state === 'submitted' ? 'Corregir registro' : item.execution_state === 'draft' ? 'Continuar borrador' : 'Registrar entreno'}
        </button>
        </div>
        {openFeedbackId === item.id && (
          <FeedbackForm
            item={item}
            cancel={() => setOpenFeedbackId('')}
            submit={async body => {
              await report(item.id, body)
              setOpenFeedbackId('')
            }}
          />
        )}
      </>
    )
  }

  return (
    <>
      {editable && <PersonalExport base={base} />}
      <Calendar
        items={assignments}
        footer={editable ? (
          <>
            <GoogleCalendarSync base={base} />
            <CalendarExport base={base} />
          </>
        ) : undefined}
      />

      <section className="next">
        <div className="section-head">
          <div>
            <p className="eyebrow">Tu próxima sesión</p>
            <h2>Preparado para entrenar</h2>
          </div>
          {next && <span className="time-pill">{hour(next.scheduled_start)}</span>}
        </div>
        {next ? (
          <>
            <p className="next-date">{dateTime(next.scheduled_start)}</p>
            <h3>{next.title}</h3>
            <WorkoutDetails item={next} />
            {reportAction(next)}
          </>
        ) : (
          <p className="muted">No hay entrenamientos pendientes.</p>
        )}
      </section>

      <details
        className="workout-disclosure"
        onToggle={event => setShowPending(event.currentTarget.open)}
      >
        <summary>
          <span>Entrenos programados</span>
          <span className="badge pale">{later.length}</span>
        </summary>
        {showPending && (
          <div className="workout-disclosure-content">
            {later.length ? later.map(item => (
              <WorkoutRow key={item.id} item={item} action={reportAction(item)} />
            )) : <p className="muted">No hay más entrenos pendientes.</p>}
          </div>
        )}
      </details>

      <div className="athlete-follow-up-title">
        <p className="eyebrow">Seguimiento personal</p>
        <h2>Recuperación y evolución</h2>
      </div>
      <FollowUp base={base} athleteId={editable ? undefined : dashboard.athlete_id} />
      <TrainingLoad assignments={assignments} />
      <div className="athlete-follow-up">
        <Fatigue dashboard={dashboard} />
        <RecoveryPage
          embedded
          base={base}
          athleteId={editable ? undefined : dashboard.athlete_id}
        />
      </div>

      <details
        className="workout-disclosure"
        onToggle={event => setShowComplete(event.currentTarget.open)}
      >
        <summary>
          <span>Todos los entrenamientos</span>
          <span className="badge pale">{complete.length}</span>
        </summary>
        {showComplete && (
          <div className="workout-disclosure-content">
            {complete.length
              ? complete.map(item => <WorkoutRow key={item.id} item={item} action={!['cancelled', 'replaced'].includes(item.status) ? reportAction(item) : undefined} />)
              : <p className="muted">Todavía no hay entrenos asignados.</p>}
          </div>
        )}
      </details>
    </>
  )
}
