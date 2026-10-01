import { FormEvent, useState } from 'react'
import { ResultsEditor } from './ResultsEditor'
import type { Assignment, SeriesResult } from '../types'

type Props = {
  item: Assignment
  submit: (body: object) => Promise<void>
  cancel: () => void
}

export function FeedbackForm({ item, submit, cancel }: Props) {
  const [status, setStatus] = useState(item.execution_data?.status ?? (item.status === 'planned' ? 'completed' : item.status))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [simple, setSimple] = useState(false)
  const [results, setResults] = useState<SeriesResult[]>(item.execution_data?.results ?? [])
  const correction = item.execution_state === 'submitted'
  const rest = item.training_type === 'rest'
  const [pain, setPain] = useState(item.execution_data?.has_pain ?? false)
  const completed = status !== 'skipped'
  const isWater = item.training_type === 'water'

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const value = (name: string) => String(form.get(name) ?? '').trim() || null
    const waterValue = (name: string) => completed && isWater ? value(name) : null

    const optionalNumber = (name: string) => value(name) === null ? null : Number(value(name))
    const operation = (event.nativeEvent as SubmitEvent).submitter?.getAttribute('data-operation') ?? (correction ? 'correct' : 'submit')
    setBusy(true); setError('')
    try {
    await submit({
      operation, version: item.version,
      reason: value('reason') ?? '', actual_date: value('actual_date'),
      technical_quality: simple ? item.execution_data?.technical_quality ?? null : optionalNumber('technical_quality'),
      muscle_fatigue: simple ? item.execution_data?.muscle_fatigue ?? null : optionalNumber('muscle_fatigue'),
      pain_intensity: pain ? optionalNumber('pain_intensity') : null,
      results: completed && !rest ? results : [],
      discipline: completed && !rest && ['running', 'ergometer', 'test', 'other'].includes(item.training_type) ? {
        meters: optionalNumber('meters'), seconds: optionalNumber('seconds'), elevation_m: optionalNumber('elevation_m'),
        model: value('model'), resistance: value('resistance'), watts: optionalNumber('watts'), cadence: optionalNumber('cadence'),
        protocol: value('protocol'), protocol_version: optionalNumber('protocol_version'),
        measure_name: value('measure_name'), measure_unit: value('measure_unit'), measure_value: optionalNumber('measure_value'),
      } : null,
      status,
      actual_minutes: completed && !rest ? optionalNumber('minutes') : null,
      rpe: completed && !rest ? optionalNumber('rpe') : null,
      feeling: completed ? optionalNumber('feeling') : null,
      has_pain: pain,
      pain_area: pain ? value('pain_area') : null,
      comment: value('comment'),
      sensations: waterValue('sensations'),
      work_done: waterValue('work_done'),
      best: waterValue('best'),
      worst: waterValue('worst'),
    })
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'No se pudo guardar; conserva el formulario y reintenta') }
    finally { setBusy(false) }
  }

  return (
    <form className="feedback" onSubmit={save}>
      <h3>{correction ? 'Corregir registro' : '¿Cómo fue el entreno?'}</h3>
      {error && <p className="error" role="alert">{error}</p>}
      <fieldset disabled={busy}>
      <label className="choice"><input type="checkbox" checked={simple} onChange={event => setSimple(event.target.checked)} />Preguntas cortas</label>
      <label>Fecha de realización<input type="date" name="actual_date" defaultValue={item.actual_date ?? new Date().toLocaleDateString('sv-SE')} /></label>
      {correction && <label>Motivo de la corrección<textarea name="reason" required maxLength={500} /></label>}

      <label>
        Resultado
        <select value={status} onChange={event => setStatus(event.target.value)}>
          <option value="completed">Completado</option>
          <option value="partial">Parcial</option>
          <option value="skipped">No realizado</option>
        </select>
      </label>

      {completed && (
        <>
          {!rest && <div className="form-row">
            <label>
              Minutos realizados
              <input
                name="minutes"
                type="number"
                min="0"
                max="1440"
                defaultValue={item.execution_data?.actual_minutes ?? undefined}
              />
            </label>
            <label>
              Esfuerzo percibido (RPE)
              <input name="rpe" type="number" min="1" max="10" defaultValue={item.execution_data?.rpe ?? undefined} />
            </label>
          </div>}

          <label>
            Sensaciones generales
            <select name="feeling" defaultValue={item.execution_data?.feeling ?? ''}>
              <option value="" disabled>Seleccionar</option>
              <option value="5">Muy buenas</option>
              <option value="4">Buenas</option>
              <option value="3">Normales</option>
              <option value="2">Cansado/a</option>
              <option value="1">Muy cansado/a</option>
            </select>
          </label>

          {!simple && <div className="form-row"><label>Calidad técnica (1–5)<input name="technical_quality" type="number" min="1" max="5" defaultValue={item.execution_data?.technical_quality ?? ''} /></label><label>Fatiga muscular (1–5)<input name="muscle_fatigue" type="number" min="1" max="5" defaultValue={item.execution_data?.muscle_fatigue ?? ''} /></label></div>}
          {!simple && !rest && <ResultsEditor item={item} results={results} change={setResults} />}
          {!rest && ['running', 'ergometer', 'test', 'other'].includes(item.training_type) && <fieldset><legend>Resultados específicos · opcionales</legend>
            {[['meters', 'Distancia (m)'], ['seconds', 'Tiempo (s)'], ...(item.training_type === 'running' ? [['elevation_m', 'Desnivel positivo (m)']] : []), ...(['ergometer', 'test'].includes(item.training_type) ? [['watts', 'Potencia (W)'], ['cadence', 'Cadencia']] : [])].map(([name, label]) => <label key={name}>{label}<input name={name} type="number" min="0" step="any" defaultValue={item.execution_data?.discipline?.[name] ?? ''} /></label>)}
            {['ergometer', 'test'].includes(item.training_type) && <><label>Modelo<input name="model" defaultValue={item.execution_data?.discipline?.model ?? ''} /></label><label>Resistencia / drag y escala<input name="resistance" defaultValue={item.execution_data?.discipline?.resistance ?? ''} /></label></>}
            {item.training_type === 'test' && <><label>Protocolo<textarea name="protocol" defaultValue={item.execution_data?.discipline?.protocol ?? ''} /></label><label>Versión del protocolo<input name="protocol_version" type="number" min="1" defaultValue={item.execution_data?.discipline?.protocol_version ?? ''} /></label></>}
            {item.training_type === 'other' && <><label>Medida<input name="measure_name" defaultValue={item.execution_data?.discipline?.measure_name ?? ''} /></label><label>Valor<input name="measure_value" type="number" step="any" defaultValue={item.execution_data?.discipline?.measure_value ?? ''} /></label><label>Unidad<input name="measure_unit" defaultValue={item.execution_data?.discipline?.measure_unit ?? ''} /></label></>}
          </fieldset>}
          {isWater && (
            <div className="water">
              <h4>Sesión de agua</h4>
              <label>
                Sensaciones
                <textarea name="sensations" defaultValue={item.execution_data?.sensations ?? ''} maxLength={1000} required />
              </label>
              <label>
                Qué se trabajó
                <textarea name="work_done" defaultValue={item.execution_data?.work_done ?? ''} maxLength={1000} required />
              </label>
              <label>
                Lo mejor del entreno
                <textarea name="best" defaultValue={item.execution_data?.best ?? ''} maxLength={1000} required />
              </label>
              <label>
                Lo peor del entreno
                <textarea name="worst" defaultValue={item.execution_data?.worst ?? ''} maxLength={1000} required />
              </label>
            </div>
          )}
        </>
      )}

      <label>
        ¿Tuviste molestias?
        <select
          value={pain ? 'yes' : 'no'}
          onChange={event => setPain(event.target.value === 'yes')}
        >
          <option value="no">No</option>
          <option value="yes">Sí</option>
        </select>
      </label>
      {pain && <label>Intensidad de molestias (0–10)<input name="pain_intensity" type="number" min="0" max="10" defaultValue={item.execution_data?.pain_intensity ?? ''} /></label>}
      {pain && (
        <label>
          Zona de molestia
          <input defaultValue={item.execution_data?.pain_area ?? ''} name="pain_area" maxLength={120} required />
        </label>
      )}
      <label>
        Comentario adicional
        <textarea defaultValue={item.execution_data?.comment ?? ''} name="comment" maxLength={2000} />
      </label>

      <div className="buttons">
        <button>{correction ? 'Guardar corrección' : 'Enviar registro'}</button>
        {!correction && <button type="submit" formNoValidate data-operation="draft" className="secondary">Guardar borrador</button>}
        <button type="button" className="secondary" onClick={cancel}>
          Cancelar
        </button>
      </div>
      </fieldset>
    </form>
  )
}
