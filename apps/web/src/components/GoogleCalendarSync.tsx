import { FormEvent, useEffect, useState } from 'react'
import { api } from '../api'
import { useResource } from '../useResource'

type Connection = {
  configured: boolean
  connected: boolean
  status: string
  calendar_id: string | null
  calendar_name: string | null
  pending: number
  last_error: string | null
}
type Calendar = { id: string; name: string; primary: boolean }

export function GoogleCalendarSync({ base }: { base: string }) {
  const endpoint = `${base}/google-calendar`
  const connection = useResource<Connection>(endpoint)
  const [calendars, setCalendars] = useState<Calendar[]>([])
  const [selected, setSelected] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const connected = connection.data?.connected
  const active = connection.data?.status === 'active'
  const reload = connection.reload

  useEffect(() => {
    if (!connected) return
    api<{ calendars: Calendar[] }>(`${endpoint}/calendars`)
      .then(result => {
        setCalendars(result.calendars)
        setSelected(current => current ||
          result.calendars.find(item => item.primary)?.id || result.calendars[0]?.id || '')
      })
      .catch(reason => setError(
        reason instanceof Error ? reason.message : 'No se pudieron cargar los calendarios',
      ))
  }, [connected, endpoint])

  useEffect(() => {
    if (!active) return
    const timer = window.setInterval(() => void reload().catch(() => {}), 10000)
    return () => window.clearInterval(timer)
  }, [active, reload])

  async function connect() {
    setBusy(true)
    setError('')
    try {
      const result = await api<{ url: string }>(`${endpoint}/connect`, { method: 'POST' })
      window.location.assign(result.url)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'No se pudo iniciar la conexión')
      setBusy(false)
    }
  }

  async function choose(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const result = await api<{ queued: number; linked_existing: number }>(
        `${endpoint}/calendar`,
        { method: 'POST', body: JSON.stringify({ calendar_id: selected }) },
      )
      await reload()
      setMessage(
        `Calendario conectado. ${result.linked_existing} sesiones existentes enlazadas y ` +
        `${result.queued} pendientes de envío.`,
      )
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'No se pudo elegir el calendario')
    } finally {
      setBusy(false)
    }
  }

  async function synchronize() {
    setError('')
    if (await connection.mutate(`${endpoint}/sync`)) {
      setMessage('Sincronización solicitada. Los cambios se enviarán automáticamente.')
    }
  }

  async function disconnect() {
    setError('')
    if (await connection.mutate(endpoint, undefined, 'DELETE')) {
      setCalendars([])
      setSelected('')
      setMessage('Calendario desconectado')
    }
  }

  const callbackResult = new URLSearchParams(window.location.search).get('google')

  return (
    <details className="disclosure calendar-export">
      <summary>Sincronización automática con Google Calendar</summary>
      {callbackResult === 'denied' && <p role="status">No se concedió acceso a Google Calendar.</p>}
      {callbackResult === 'failed' && <p role="alert" className="error">La conexión con Google no se completó.</p>}
      {connection.error && <p role="alert" className="error">{connection.error}</p>}
      {error && <p role="alert" className="error">{error}</p>}
      {message && <p role="status" className="success">{message}</p>}
      {connection.loading && !connection.data && <p>Cargando conexión…</p>}
      {connection.data && !connection.data.configured && (
        <p className="muted">La conexión automática aún no está configurada en este servidor.</p>
      )}
      {connection.data?.configured && !connected && (
        <>
          <p className="muted">Autoriza tu cuenta de Google para enviar nuevas sesiones automáticamente.</p>
          <button type="button" disabled={busy} onClick={() => void connect()}>
            {busy ? 'Conectando…' : 'Conectar Google Calendar'}
          </button>
        </>
      )}
      {connected && (
        <>
          {connection.data?.last_error && (
            <p role="alert" className="error">{connection.data.last_error}</p>
          )}
          {connection.data?.status === 'reconnect_required' && (
            <button type="button" disabled={busy} onClick={() => void connect()}>
              Volver a conectar
            </button>
          )}
          {calendars.length > 0 && (
            <form className="inline-form" onSubmit={choose}>
              <label>
                Calendario de destino
                <select value={selected} onChange={event => setSelected(event.target.value)}>
                  {calendars.map(item => (
                    <option key={item.id} value={item.id}>
                      {item.name}{item.primary ? ' · Principal' : ''}
                    </option>
                  ))}
                </select>
              </label>
              <button disabled={busy || !selected}>Guardar calendario</button>
            </form>
          )}
          {active && (
            <>
              <p>
                Conectado a <strong>{connection.data?.calendar_name}</strong>.
                {connection.data?.pending ? ` ${connection.data.pending} envíos pendientes.` : ' Todo al día.'}
              </p>
              <button type="button" className="secondary" onClick={() => void synchronize()}>
                Revisar cambios ahora
              </button>
            </>
          )}
          <details className="disclosure calendar-disconnect">
            <summary>Desconectar Google Calendar</summary>
            <p>Detiene nuevos envíos. Los eventos ya creados seguirán en Google Calendar.</p>
            <button type="button" className="secondary" onClick={() => void disconnect()}>
              Confirmar desconexión
            </button>
          </details>
        </>
      )}
    </details>
  )
}
