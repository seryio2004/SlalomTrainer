import { FormEvent, useState } from 'react'

type Props = { base: string }

export function CalendarExport({ base }: Props) {
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function download(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const query = new URLSearchParams()
    const start = String(form.get('start') ?? '')
    const end = String(form.get('end') ?? '')
    if (start) query.set('start', start)
    if (end) query.set('end', end)
    if (form.get('include_imported')) query.set('include_imported', 'true')

    setBusy(true)
    setMessage('')
    setError('')
    try {
      const response = await fetch(
        `/api/v1${base}/calendar/export.ics?${query.toString()}`,
        { credentials: 'same-origin' },
      )
      if (response.status === 204) {
        setMessage('No hay entrenamientos nuevos en este período. Si ya venían de Google, puedes incluirlos con la casilla.')
        return
      }
      if (!response.ok) {
        const body = await response.json().catch(() => null)
        throw new Error(typeof body?.detail === 'string'
          ? body.detail : 'No se pudo generar el calendario')
      }

      const url = URL.createObjectURL(await response.blob())
      const link = document.createElement('a')
      link.href = url
      link.download = 'entrenamientos-teitraining.ics'
      document.body.append(link)
      link.click()
      link.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
      setMessage('Archivo descargado. Impórtalo en Google Calendar.')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'No se pudo descargar el calendario')
    } finally {
      setBusy(false)
    }
  }

  return (
    <details className="disclosure calendar-export">
      <summary>Exportar a Google Calendar</summary>
      <p className="muted">
        Descarga tus entrenamientos pendientes en un archivo .ics. El período por defecto va
        de hoy hasta un año después.
      </p>
      <form onSubmit={download}>
        <div className="form-row">
          <label>
            Desde (opcional)
            <input type="date" name="start" />
          </label>
          <label>
            Hasta (opcional)
            <input type="date" name="end" />
          </label>
        </div>
        <label className="choice">
          <input type="checkbox" name="include_imported" />
          Incluir entrenamientos importados de Google Calendar
        </label>
        <p className="muted">
          Activa esta opción solo si vas a importarlos en otro calendario; en el original
          podrían aparecer duplicados.
        </p>
        <button disabled={busy}>{busy ? 'Preparando archivo…' : 'Descargar .ics'}</button>
      </form>
      {message && <p role="status" className="success">{message}</p>}
      {error && <p role="alert" className="error">{error}</p>}
      <p className="muted">
        Después, abre Google Calendar → Configuración → Importar y exportar y selecciona el archivo.
        {' '}<a href="https://support.google.com/calendar/answer/37118?hl=es" target="_blank" rel="noopener noreferrer">
          Instrucciones de Google
        </a>
      </p>
    </details>
  )
}
