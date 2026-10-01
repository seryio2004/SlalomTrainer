import { PrescriptionDetails } from './PrescriptionEditor'
import type { ReactNode } from 'react'
import { dateTime, hour, place, trainingTypes } from '../format'
import type { Assignment } from '../types'

const statusNames: Record<string, string> = {
  completed: 'Completado',
  partial: 'Parcial',
  skipped: 'No realizado',
  cancelled: 'Cancelado',
  planned: 'Pendiente',
}

export function WorkoutDetails({ item }: { item: Assignment }) {
  return (
    <>
      <div className="badges">
        <span className="badge">{place(item.venue)}</span>
        <span className="badge pale">{trainingTypes[item.training_type]}</span>
        <span className="workout-duration">{item.planned_minutes} min previstos</span>
      </div>
      {item.prescription.objective && <p>Objetivo: {item.prescription.objective}</p>}
      {item.prescription.details && <p>{Object.entries(item.prescription.details).filter(([, value]) => value != null).map(([key, value]) => `${({ water_subtype: 'Subtipo', runs: 'Mangas', meters: 'Distancia (m)', seconds: 'Tiempo (s)', target_rpe: 'RPE objetivo', model: 'Modelo', resistance: 'Resistencia', protocol: 'Protocolo', protocol_version: 'Versión' } as Record<string, string>)[key]}: ${value}`).join(' · ')}</p>}
      <PrescriptionDetails blocks={item.prescription.blocks} />
      <p>{item.prescription.instructions || 'Sin instrucciones adicionales.'}</p>
      {!!item.prescription.steps?.length && (
        <div className="steps">
          <strong>Indicaciones paso a paso</strong>
          <ol>
            {item.prescription.steps.map((step, index) => <li key={index}>{step}</li>)}
          </ol>
        </div>
      )}
    </>
  )
}

export function WorkoutRow({ item, action }: { item: Assignment; action?: ReactNode }) {
  const date = new Date(item.scheduled_start)
  return (
    <details className="workout-row">
      <summary>
        <time className="workout-date" dateTime={item.scheduled_start} aria-label={dateTime(item.scheduled_start)}>
          <strong>{date.getDate()}</strong>
          <span>{date.toLocaleDateString('es-ES', { month: 'short' })}</span>
        </time>
        <span className="workout-row-title">
          <strong>{item.title}</strong>
          <span>{hour(item.scheduled_start)} · {trainingTypes[item.training_type]} · {item.planned_minutes} min</span>
        </span>
        <span className={`workout-status status-${item.status}`}>{statusNames[item.status] ?? item.status}</span>
        <span className="workout-row-chevron" aria-hidden="true">⌄</span>
      </summary>
      <div className="workout-row-body">
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
        {item.actual_date && <p>Realizado el {item.actual_date}</p>}
        {item.execution_data?.results?.length ? <div className="record"><h4>Series realizadas</h4><ul>{item.execution_data.results.map((row, index) => <li key={index}>{row.name} · serie {row.set_number}{row.origin === 'added' ? ' · añadido' : ''}{row.reps != null ? ` · ${row.reps} reps` : ''}{row.kg != null ? ` · ${row.kg} kg` : ''}{row.seconds != null ? ` · ${row.seconds} s` : ''}{row.meters != null ? ` · ${row.meters} m` : ''}{row.rir != null ? ` · RIR ${row.rir}` : ''}{row.comment ? ` · ${row.comment}` : ''}</li>)}</ul></div> : null}
        {item.execution_data?.discipline && <div className="record"><h4>Resultados específicos</h4>{Object.entries(item.execution_data.discipline).filter(([, value]) => value != null).map(([key, value]) => <p key={key}>{({ meters: 'Distancia (m)', seconds: 'Tiempo (s)', elevation_m: 'Desnivel (m)', model: 'Modelo', resistance: 'Resistencia', watts: 'Potencia (W)', cadence: 'Cadencia', protocol: 'Protocolo', protocol_version: 'Versión', measure_name: 'Medida', measure_value: 'Valor', measure_unit: 'Unidad' } as Record<string, string>)[key] ?? key}: {value}</p>)}</div>}
        {!!item.prescription_revisions?.length && <details><summary>Original y adaptaciones</summary><p>{item.original_prescription?.instructions}</p><PrescriptionDetails blocks={item.original_prescription?.blocks} />{item.prescription_revisions.map(revision => <p key={revision.version}>Versión {revision.version} · {revision.reason} · {new Date(revision.at).toLocaleString('es-ES')}</p>)}</details>}
        {!!item.execution_revisions?.length && <details><summary>Correcciones anteriores</summary>{item.execution_revisions.map(revision => <div key={revision.version}><p>{revision.reason} · {new Date(revision.at).toLocaleString('es-ES')}</p><p>Duración anterior: {revision.data.actual_minutes ?? 'sin datos'} min · RPE anterior: {revision.data.rpe ?? 'sin datos'}</p></div>)}</details>}
        {item.comment && <p>Comentario: {item.comment}</p>}
        {action}
      </div>
    </details>
  )
}
