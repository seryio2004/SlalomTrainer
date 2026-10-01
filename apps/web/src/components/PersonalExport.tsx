import { useState } from 'react'
import { api } from '../api'

export function PersonalExport({ base }: { base: string }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  async function download() {
    setBusy(true); setError(''); setSaved(false)
    try {
      const data = await api<object>(`${base}/personal-data/export`, { method: 'POST' })
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }))
      const link = document.createElement('a'); link.href = url; link.download = 'teitraining-datos.json'; link.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
      setSaved(true)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'No se pudo exportar') }
    finally { setBusy(false) }
  }
  return <div><button type="button" disabled={busy} className="secondary" onClick={() => void download()}>Descargar mis datos deportivos</button>{error && <p className="error" role="alert">{error}</p>}{saved && <p role="status">Exportación preparada.</p>}</div>
}
