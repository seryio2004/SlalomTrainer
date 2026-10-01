import { useEffect, useRef, useState } from 'react'
import { dateTime } from '../format'
import type { Assignment } from '../types'
import { parseExercisePrescription, stepsFromPrescription } from '../training/exercisePrescription'
import { FeedbackForm } from './FeedbackForm'
import { WorkoutDetails } from './WorkoutCard'
import './workout-session.css'

type Timer = {
  remaining: number
  running: boolean
  start: (seconds: number) => void
  pause: () => void
  resume: () => void
  reset: () => void
}

function useCountdown(onComplete?: () => void): Timer {
  const [remaining, setRemaining] = useState(0)
  const [running, setRunning] = useState(false)
  const deadline = useRef(0)
  const completion = useRef(onComplete)
  completion.current = onComplete

  useEffect(() => {
    if (!running) return

    const tick = () => {
      const secondsLeft = Math.max(0, Math.ceil((deadline.current - Date.now()) / 1000))
      setRemaining(secondsLeft)
      if (secondsLeft === 0) {
        setRunning(false)
        completion.current?.()
      }
    }

    tick()
    const interval = window.setInterval(tick, 250)
    return () => window.clearInterval(interval)
  }, [running])

  return {
    remaining,
    running,
    start(seconds) {
      const duration = Math.min(3600, Math.max(1, Math.floor(seconds)))
      deadline.current = Date.now() + duration * 1000
      setRemaining(duration)
      setRunning(true)
    },
    pause() {
      setRemaining(Math.max(0, Math.ceil((deadline.current - Date.now()) / 1000)))
      setRunning(false)
    },
    resume() {
      if (remaining <= 0) return
      deadline.current = Date.now() + remaining * 1000
      setRunning(true)
    },
    reset() {
      setRunning(false)
      setRemaining(0)
    },
  }
}

function formatTime(seconds: number) {
  const minutes = Math.floor(seconds / 60)
  const remainder = seconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`
}

function TimerControls({ timer }: { timer: Timer }) {
  if (!timer.remaining) return null
  return timer.running ? (
    <button type="button" className="secondary" onClick={timer.pause}>Pausar</button>
  ) : (
    <button type="button" onClick={timer.resume}>Reanudar</button>
  )
}

function GuidedTool({ item, timersEnabled }: { item: Assignment; timersEnabled: boolean }) {
  const steps = stepsFromPrescription(item.prescription.instructions, item.prescription.steps)
  const structured = item.prescription.blocks?.flatMap(block => block.exercises) ?? []
  const exercises = structured.length ? structured.map(exercise => ({
    instruction: [exercise.name, exercise.instructions].filter(Boolean).join(' · '),
    sets: exercise.sets ?? 1, repetitions: exercise.reps ?? null,
    seconds: exercise.seconds ?? null, restSeconds: exercise.rest_seconds ?? 0,
  })) : steps.map(parseExercisePrescription)
  const [stepIndex, setStepIndex] = useState(0)
  const [setIndex, setSeriesIndex] = useState(0)
  const [phase, setPhase] = useState<'ready' | 'work' | 'rest' | 'done'>('ready')
  const timer = useCountdown(() => finishCurrentPhase())
  const current = exercises[stepIndex]

  function startExercise() {
    if (!current) return
    setPhase('work')
    if (timersEnabled && current.seconds) timer.start(current.seconds)
  }

  useEffect(() => {
    startExercise()
  }, [])

  function finishCurrentPhase() {
    if (phase === 'work' && current && setIndex < current.sets - 1) {
      if (current.restSeconds > 0) {
        setPhase('rest')
        timer.start(current.restSeconds)
        return
      }
      setSeriesIndex(setIndex + 1)
      setPhase('work')
      if (current.seconds) timer.start(current.seconds)
      return
    }

    if (phase === 'rest' && current && setIndex < current.sets - 1) {
      setSeriesIndex(setIndex + 1)
      setPhase('work')
      if (current.seconds) timer.start(current.seconds)
      return
    }

    setStepIndex(stepIndex + 1)
    setSeriesIndex(0)
    setPhase(stepIndex + 1 >= exercises.length ? 'done' : 'ready')
  }

  function startGuide() {
    timer.reset()
    setStepIndex(0)
    setSeriesIndex(0)
    setPhase('ready')
  }

  function finishRepSet() {
    if (!current) return
    if (timersEnabled && setIndex < current.sets - 1 && current.restSeconds > 0) {
      setPhase('rest')
      timer.start(current.restSeconds)
    } else if (setIndex < current.sets - 1) {
      setSeriesIndex(setIndex + 1)
    } else {
      setStepIndex(stepIndex + 1)
      setSeriesIndex(0)
      setPhase(stepIndex + 1 >= exercises.length ? 'done' : 'ready')
    }
  }

  function skipPhase() {
    timer.reset()
    if (phase === 'rest') {
      finishCurrentPhase()
      return
    }
    setStepIndex(stepIndex + 1)
    setSeriesIndex(0)
    setPhase(stepIndex + 1 >= exercises.length ? 'done' : 'ready')
  }

  return (
    <section className="guided-tool">
      <div className="tool-heading">
        <p className="eyebrow">Modo de ejecución</p>
        <h2>Entrenamiento guiado</h2>
        <p>Los tiempos, series y repeticiones salen de las indicaciones de esta sesión.</p>
      </div>

      {exercises.length ? (
        <>
          <ol className="guided-step-list" aria-label="Ejercicios de la sesión">
            {exercises.map((exercise, step) => (
              <li key={`${step}-${exercise.instruction}`} className={step === stepIndex ? 'current' : ''}>
                <span>{step + 1}</span>
                <div>
                  <strong>{exercise.instruction || `Ejercicio ${step + 1}`}</strong>
                  <small>
                    {exercise.sets} {exercise.sets === 1 ? 'serie' : 'series'}
                    {exercise.repetitions ? ` × ${exercise.repetitions} repeticiones` : ''}
                    {timersEnabled && exercise.seconds ? ` × ${exercise.seconds} s` : ''}
                    {timersEnabled && exercise.restSeconds ? ` · ${exercise.restSeconds} s de descanso` : ''}
                  </small>
                </div>
              </li>
            ))}
          </ol>

          {phase === 'done' ? (
            <div className="guided-finished" role="status">
              <h3>Sesión guiada completada</h3>
              <p>Registra el entreno y tu feedback al terminar.</p>
              <button type="button" onClick={startGuide}>Repetir guía</button>
            </div>
          ) : current ? (
            <div className="guided-active" aria-live="polite">
              <p className="eyebrow">
                Ejercicio {stepIndex + 1} de {exercises.length} · Serie {setIndex + 1} de {current.sets}
              </p>
              <h3>{current.instruction || `Ejercicio ${stepIndex + 1}`}</h3>
              <p className="guided-prescription">
                {current.repetitions
                  ? `Completa ${current.repetitions} repeticiones${current.sets > 1 ? ` · serie ${setIndex + 1} de ${current.sets}` : ''}.`
                  : current.seconds
                    ? 'Sigue el cronómetro y mantén el ejercicio hasta que termine.'
                    : 'Sigue la indicación del entrenador y avanza cuando termines.'}
              </p>
              {timersEnabled && current.restSeconds > 0 && <p className="muted">Descanso entre series: {current.restSeconds} s</p>}
              <div className="timer-display" role="timer" aria-label={`${phase === 'rest' ? 'Descanso' : 'Tiempo del ejercicio'}: ${formatTime(timer.remaining)}`}>
                <span>{phase === 'rest' ? 'Descanso' : timersEnabled && current.seconds ? 'Tiempo de ejercicio' : 'Sin tiempo fijado'}</span>
                <strong>{formatTime(timer.remaining)}</strong>
              </div>
              <div className="timer-controls">
                {phase === 'ready' && timersEnabled && current.seconds && (
                  <button type="button" onClick={startExercise}>
                    {current.seconds ? 'Iniciar serie' : current.repetitions ? 'Empezar serie' : 'Empezar ejercicio'}
                  </button>
                )}
                {phase === 'work' && timersEnabled && current.seconds && <TimerControls timer={timer} />}
                {phase === 'ready' && (!timersEnabled || !current.seconds) && (
                  <button type="button" onClick={startExercise}>Empezar ejercicio</button>
                )}
                {phase === 'work' && (!timersEnabled || !current.seconds) && (
                  <button type="button" onClick={finishRepSet}>
                    {current.repetitions ? 'Serie completada' : 'Continuar'}
                  </button>
                )}
                {phase === 'rest' && <TimerControls timer={timer} />}
                {(phase === 'work' || phase === 'rest') && timersEnabled && (
                  <button type="button" className="secondary" onClick={skipPhase}>
                    Saltar {phase === 'rest' ? 'descanso' : 'ejercicio'}
                  </button>
                )}
              </div>
            </div>
          ) : null}

          <p className="tool-note">{timersEnabled ? 'Las series, repeticiones y descansos siguen la prescripción del entrenador. Comprueba el material y el espacio antes de empezar.' : 'Usa las indicaciones de la sesión y avanza manualmente. Comprueba el material y el espacio antes de empezar.'}</p>
        </>
      ) : (
        <div className="guided-empty">
          <p>El entrenador todavía no ha añadido ejercicios paso a paso a esta sesión.</p>
          <p>Consulta las instrucciones generales de arriba. Puedes realizarla manualmente y registrar el feedback al terminar.</p>
        </div>
      )}
    </section>
  )
}

export function WorkoutSession({
  assignments,
  selectedId,
  onSelect,
  onReport,
}: {
  assignments: Assignment[]
  selectedId: string
  onSelect: (id: string) => void
  onReport: (id: string, body: object) => Promise<void>
}) {
  const pending = assignments
    .filter(item => item.status === 'planned')
    .sort((a, b) => new Date(a.scheduled_start).getTime() - new Date(b.scheduled_start).getTime())
  const item = pending.find(session => session.id === selectedId) ?? pending[0]
  const [showFeedback, setShowFeedback] = useState(false)
  const [started, setStarted] = useState(false)

  if (!item) {
    return (
      <section className="workout-session-empty">
        <h2>Sin entrenamientos pendientes</h2>
        <p>Cuando tengas una sesión programada, podrás realizarla desde aquí.</p>
      </section>
    )
  }

  if (!started) {
    return (
      <section className="workout-start-menu">
        <p className="eyebrow">Realizar entreno</p>
        <h2>Elige tu sesión</h2>
        <label className="session-switcher">
          Entrenamiento pendiente
          <select value={item.id} onChange={event => onSelect(event.target.value)}>
            {pending.map(session => (
              <option key={session.id} value={session.id}>
                {session.title} · {dateTime(session.scheduled_start)}
              </option>
            ))}
          </select>
        </label>
        <div className="workout-start-preview">
          <p className="eyebrow">{item.training_type === 'water' ? 'Sesión de agua' : 'Sesión fuera del agua'}</p>
          <h3>{item.title}</h3>
          <p className="muted">{dateTime(item.scheduled_start)} · {item.planned_minutes} min previstos</p>
          <WorkoutDetails item={item} />
        </div>
        <button type="button" className="start-workout-button" onClick={() => setStarted(true)}>
          Empezar entreno
        </button>
      </section>
    )
  }

  return (
    <div className="workout-session" key={item.id}>
      <section className="session-intro session-active-heading">
        <div>
          <p className="eyebrow">Entreno en curso</p>
          <h2>{item.title}</h2>
        </div>
        <button type="button" className="secondary" onClick={() => setStarted(false)}>
          Cambiar sesión
        </button>
      </section>
      {item.training_type !== 'rest' && (
        <GuidedTool key={item.id} item={item} timersEnabled={item.training_type !== 'water'} />
      )}
      <section className="session-finish">
        <p className="eyebrow">Al terminar</p>
        <h2>Registrar entreno</h2>
        <p className="muted">Completar la guía no registra automáticamente la sesión.</p>
        {showFeedback ? (
          <FeedbackForm item={item} cancel={() => setShowFeedback(false)} submit={body => onReport(item.id, body)} />
        ) : (
          <button type="button" onClick={() => setShowFeedback(true)}>Marcar como completado y dar feedback</button>
        )}
      </section>
    </div>
  )
}
