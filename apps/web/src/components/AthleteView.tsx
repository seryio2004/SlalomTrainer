import { useState } from 'react'
import { dateTime, hour, place, trainingTypes } from '../format'
import type { Assignment, Dashboard } from '../types'
import { Calendar } from './Calendar'
import { FeedbackForm } from './FeedbackForm'

type Props = {
  dashboard: Dashboard
  editable: boolean
  report: (id: string, body: object) => Promise<void>
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

const statusNames: Record<string, string> = {
  completed: 'Completado',
  partial: 'Parcial',
  skipped: 'No realizado',
}

function WorkoutDetails({ item }: { item: Assignment }) {
  return (
    <>
      <div className="badges">
        <span className="badge">{place(item.venue)}</span>
        <span className="badge pale">{trainingTypes[item.training_type]}</span>
      </div>
      <p>{item.prescription.instructions || 'Sin instrucciones adicionales.'}</p>
      {!!item.prescription.steps?.length && (
        <div className="steps">
          <strong>Indicaciones paso a paso</strong>
          <ol>
            {item.prescription.steps.map((step, index) => (
              <li key={index}>{step}</li>
            ))}
          </ol>
        </div>
      )}
    </>
  )
}

function Fatigue({ dashboard }: { dashboard: Dashboard }) {
  const { band, available } = dashboard.fatigue
  const label = fatigueNames[band]

  return (
    <section>
      <p className="eyebrow">Seguimiento</p>
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

function History({ items }: { items: Assignment[] }) {
  return (
    <section>
      <p className="eyebrow">Registro</p>
      <h2>Historial de entrenos</h2>
      {items.length ? (
        <div className="history">
          {items.map(item => (
            <article className="item" key={item.id}>
              <div className="section-head">
                <h3>{item.title}</h3>
                <span className="badge pale">{statusNames[item.status]}</span>
              </div>
              <p className="muted">{dateTime(item.scheduled_start)}</p>
              <WorkoutDetails item={item} />
              {item.water_feedback?.sensations && (
                <div className="record">
                  <strong>Feedback de agua</strong>
                  <p>Sensaciones: {item.water_feedback.sensations}</p>
                  <p>Trabajo: {item.water_feedback.work_done}</p>
                  <p>Lo mejor: {item.water_feedback.best}</p>
                  <p>Lo peor: {item.water_feedback.worst}</p>
                </div>
              )}
              {item.comment && <p>Comentario: {item.comment}</p>}
            </article>
          ))}
        </div>
      ) : (
        <p className="muted">Todavía no hay entrenos registrados.</p>
      )}
    </section>
  )
}

export function AthleteView({ dashboard, editable, report }: Props) {
  const [openFeedbackId, setOpenFeedbackId] = useState('')
  const assignments = [...dashboard.assignments].sort(
    (a, b) => new Date(a.scheduled_start).getTime() - new Date(b.scheduled_start).getTime(),
  )
  const pending = assignments.filter(item => item.status === 'planned')
  const next = pending.find(
    item => new Date(item.scheduled_start).getTime() >= Date.now(),
  ) ?? pending[0]
  const history = assignments.filter(item => item.status !== 'planned').reverse()
  const later = pending.filter(item => item.id !== next?.id)

  function reportAction(item: Assignment) {
    if (!editable) {
      return null
    }

    return (
      <>
        <button onClick={() => setOpenFeedbackId(item.id)}>
          {item.id === next?.id ? 'Marcar completado' : 'Registrar entreno'}
        </button>
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
      <Calendar items={assignments} />

      <section className="next">
        <div className="section-head">
          <div>
            <p className="eyebrow">Próximo</p>
            <h2>Siguiente entreno</h2>
          </div>
          {next && <span className="time-pill">{hour(next.scheduled_start)}</span>}
        </div>
        {next ? (
          <>
            <p className="muted">{dateTime(next.scheduled_start)}</p>
            <h3>{next.title}</h3>
            <WorkoutDetails item={next} />
            {reportAction(next)}
          </>
        ) : (
          <p className="muted">No hay entrenamientos pendientes.</p>
        )}
      </section>

      <div className="columns">
        <Fatigue dashboard={dashboard} />
        <History items={history} />
      </div>

      {later.length > 0 && (
        <section>
          <h2>Más entrenos pendientes</h2>
          {later.map(item => (
            <article className="item" key={item.id}>
              <h3>{item.title}</h3>
              <p className="muted">{dateTime(item.scheduled_start)}</p>
              <WorkoutDetails item={item} />
              {reportAction(item)}
            </article>
          ))}
        </section>
      )}
    </>
  )
}
