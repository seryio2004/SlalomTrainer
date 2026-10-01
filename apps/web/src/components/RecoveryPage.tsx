import { FormEvent, useState } from 'react'
import { useResource } from '../useResource'
import { dateTime } from '../format'

type ScoreField = 'sleep' | 'fatigue' | 'soreness' | 'motivation' | 'energy' | 'pain'
type Values = Record<ScoreField, number | null> & {
  pain_area: string | null
  comment: string | null
}
type Recovery = Values & {
  id: string
  local_date: string
  version: number
  updated_at: string
  revisions: (Values & { version: number; reason: string; corrected_at: string })[]
}
type RecoveryData = { timezone: string; today: string; records: Recovery[] }

const scores: { field: ScoreField; title: string; options: string[] }[] = [
  { field: 'sleep', title: 'Calidad del sueño', options: ['Muy mala', 'Mala', 'Normal', 'Buena', 'Muy buena'] },
  { field: 'fatigue', title: 'Fatiga', options: ['Ninguna', 'Leve', 'Moderada', 'Alta', 'Muy alta'] },
  { field: 'soreness', title: 'Agujetas', options: ['Ningunas', 'Leves', 'Moderadas', 'Altas', 'Muy altas'] },
  { field: 'motivation', title: 'Motivación', options: ['Muy baja', 'Baja', 'Normal', 'Alta', 'Muy alta'] },
  { field: 'energy', title: 'Energía', options: ['Muy baja', 'Baja', 'Normal', 'Alta', 'Muy alta'] },
]

function RecoveryForm({
  record, saving, save,
}: {
  record?: Recovery
  saving: boolean
  save: (body: object) => Promise<void>
}) {
  const [pain, setPain] = useState(record?.pain == null ? '' : String(record.pain))

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const optionalNumber = (field: string) => form.get(field) ? Number(form.get(field)) : null
    const body = {
      version: record?.version ?? 0,
      sleep: optionalNumber('sleep'),
      fatigue: optionalNumber('fatigue'),
      soreness: optionalNumber('soreness'),
      motivation: optionalNumber('motivation'),
      energy: optionalNumber('energy'),
      pain: optionalNumber('pain'),
      pain_area: Number(pain) > 0 ? String(form.get('pain_area') ?? '').trim() || null : null,
      comment: String(form.get('comment') ?? '').trim() || null,
      reason: String(form.get('reason') ?? '').trim(),
    }
    await save(body)
  }

  return (
    <form onSubmit={submit}>
      <div className="form-row">
        {scores.map(score => (
          <label key={score.field}>
            {score.title}
            <select name={score.field} defaultValue={record?.[score.field] ?? ''}>
              <option value="">Sin valorar</option>
              {score.options.map((label, index) => (
                <option key={label} value={index + 1}>{label}</option>
              ))}
            </select>
          </label>
        ))}
        <label>
          Dolor
          <select name="pain" value={pain} onChange={event => setPain(event.target.value)}>
            <option value="">Sin valorar</option>
            <option value="0">Sin dolor</option>
            {Array.from({ length: 10 }, (_, index) => (
              <option key={index + 1} value={index + 1}>
                {index + 1}{index === 0 ? ' · Muy leve' : index === 9 ? ' · Máximo' : ''}
              </option>
            ))}
          </select>
        </label>
      </div>
      {Number(pain) > 0 && (
        <label>
          Zona de dolor (opcional)
          <input name="pain_area" maxLength={120} defaultValue={record?.pain_area ?? ''} />
        </label>
      )}
      <label>
        Comentario
        <textarea name="comment" maxLength={2000} defaultValue={record?.comment ?? ''} />
      </label>
      {record && (
        <label>
          Motivo de la corrección
          <input name="reason" maxLength={500} required />
        </label>
      )}
      <button disabled={saving}>
        {saving ? 'Guardando…' : record ? 'Guardar corrección' : 'Guardar recuperación'}
      </button>
    </form>
  )
}

function RecoveryEditor({
  base, selectedDate, selectDate, onSaved,
}: {
  base: string
  selectedDate: string
  selectDate: (date: string) => void
  onSaved: () => Promise<void>
}) {
  const query = selectedDate
    ? `?start=${selectedDate}&end=${selectedDate}`
    : ''
  const { data, error, loading, saving, mutate, reload } = useResource<RecoveryData>(`${base}/recovery${query}`)
  const date = selectedDate || data?.today || ''
  const record = data?.records.find(item => item.local_date === date)
  const [message, setMessage] = useState('')

  return (
    <>
      {error && (
        <div>
          <p role="alert" className="error">{error}</p>
          <button className="secondary" onClick={() => void reload().catch(() => {})}>
            Recargar registro
          </button>
        </div>
      )}
      {loading && !data && <p>Cargando registro…</p>}
      {message && <p role="status" className="success">{message}</p>}
      {data && (
        <>
          <label className="date-field">
            Día del registro · {data.timezone}
            <input
              type="date"
              value={date}
              max={data.today}
              onChange={event => {
                selectDate(event.target.value)
                setMessage('')
              }}
            />
          </label>
          <RecoveryForm
            key={`${date}-${record?.version ?? 0}`}
            record={record}
            saving={saving}
            save={async body => {
              if (await mutate(`${base}/recovery/${date}`, body, 'PUT')) {
                setMessage('Recuperación guardada')
                await onSaved().catch(() => {})
              }
            }}
          />
        </>
      )}
    </>
  )
}

export function RecoveryPage({ base, athleteId, embedded = false }: {
  base: string
  athleteId?: string
  embedded?: boolean
}) {
  const [editorOpen, setEditorOpen] = useState(!embedded)
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [selectedDate, setSelectedDate] = useState('')
  const [message, setMessage] = useState('')
  const query = new URLSearchParams()
  if (start) query.set('start', start)
  if (end) query.set('end', end)
  const endpoint = athleteId ? `${base}/athletes/${athleteId}/recovery` : `${base}/recovery`
  const { data, error, loading, reload } = useResource<RecoveryData>(
    `${endpoint}?${query.toString()}`,
  )
  const todayRecord = data?.records.find(record => record.local_date === data.today)

  return (
    <>
      <section className="recovery-panel">
        <div className="section-head">
          <h2>Recuperación diaria</h2>
          <button className="secondary" onClick={() => void reload().catch(() => {})}>
            Actualizar
          </button>
        </div>
        <p className="muted">
          Sueño, energía y sensaciones por día. Los campos son opcionales y un día sin registro queda sin datos.
        </p>
        {error && <p role="alert" className="error">{error}</p>}
        {message && <p role="status" className="success">{message}</p>}
        {loading && !data && <p>Cargando registros…</p>}
        {!start && !end && data && (
          <dl className="recovery-overview">
            {scores.filter(score => ['sleep', 'energy', 'fatigue'].includes(score.field)).map(score => (
              <div key={score.field}>
                <dt>{score.title} · hoy</dt>
                <dd>{todayRecord?.[score.field] == null
                  ? 'Sin registro'
                  : score.options[todayRecord[score.field]! - 1]}</dd>
              </div>
            ))}
          </dl>
        )}
        {!athleteId && (
          <details
            className="recovery-editor"
            open={editorOpen}
            onToggle={event => setEditorOpen(event.currentTarget.open)}
          >
            <summary>Registrar o corregir recuperación</summary>
            <RecoveryEditor
              base={base}
              selectedDate={selectedDate}
              selectDate={setSelectedDate}
              onSaved={reload}
            />
          </details>
        )}
      </section>
      <section className="recovery-history-panel">
        <p className="eyebrow">Sensaciones y descanso</p>
        <h2>Evolución de la recuperación</h2>
        <div className="form-row">
          <label>Desde<input type="date" value={start} onChange={event => setStart(event.target.value)} /></label>
          <label>Hasta<input type="date" value={end} onChange={event => setEnd(event.target.value)} /></label>
        </div>
        <p className="muted">Por defecto se muestran los últimos tres meses. Cada consulta admite hasta un año.</p>
        {data?.records.length ? (
          <div className="table-scroll">
            <table>
              <caption>Valoraciones declaradas, ordenadas de más recientes a más antiguas</caption>
              <thead>
                <tr><th>Día</th>{scores.map(score => <th key={score.field}>{score.title}</th>)}<th>Dolor</th></tr>
              </thead>
              <tbody>
                {data.records.map(item => (
                  <tr key={item.id}>
                    <td>{item.local_date}</td>
                    {scores.map(score => (
                      <td key={score.field}>
                        {item[score.field] == null ? 'Sin datos' : score.options[item[score.field]! - 1]}
                      </td>
                    ))}
                    <td>{item.pain ?? 'Sin datos'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <p>No hay registros en este período.</p>}
        {data?.records.map(item => (
          <details className="disclosure" key={item.id}>
            <summary>{item.local_date} · Detalle y correcciones</summary>
            <p>{item.comment || 'Sin comentario.'}</p>
            {item.pain_area && <p>Zona: {item.pain_area}</p>}
            <p className="muted">Último guardado: {dateTime(item.updated_at)}</p>
            {!athleteId && (
              <button className="secondary" onClick={() => {
                setSelectedDate(item.local_date)
                setEditorOpen(true)
                setMessage('Registro seleccionado para corregir en el formulario superior')
              }}>Corregir este día</button>
            )}
            {item.revisions.map(revision => (
              <div className="record" key={revision.version}>
                <strong>Corrección del {dateTime(revision.corrected_at)}</strong>
                <p>Motivo: {revision.reason}</p>
                <p>Comentario anterior: {revision.comment || 'Sin comentario'}</p>
                <ul>
                  {scores.map(score => (
                    <li key={score.field}>
                      {score.title}: {revision[score.field] == null
                        ? 'Sin datos' : score.options[revision[score.field]! - 1]}
                    </li>
                  ))}
                  <li>Dolor: {revision.pain ?? 'Sin datos'}{revision.pain_area ? ` · ${revision.pain_area}` : ''}</li>
                </ul>
              </div>
            ))}
          </details>
        ))}
      </section>
    </>
  )
}
