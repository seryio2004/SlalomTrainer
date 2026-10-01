import { FormEvent, useState } from 'react'
import { api } from '../api'

export function AccountAccess() {
  const [token] = useState(() => {
    const value = new URLSearchParams(window.location.hash.slice(1)).get('access_token') ?? ''
    if (value) window.history.replaceState(null, '', window.location.pathname + window.location.search)
    return value
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setBusy(true); setError(''); setMessage('')
    try {
      const result = await api<{ message: string }>(token ? '/auth/accept' : '/auth/recovery', {
        method: 'POST', body: JSON.stringify(token ? { token, password: form.get('password') } : { email: form.get('email') }),
      })
      setMessage(result.message)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'No se pudo actualizar el acceso') }
    finally { setBusy(false) }
  }
  return <details open={!!token}><summary>{token ? 'Aceptar invitación o recuperar acceso' : 'He olvidado mi contraseña'}</summary>
    {error && <p className="error" role="alert">{error}</p>}{message && <p role="status">{message}</p>}
    <form onSubmit={submit}><fieldset disabled={busy || !!message}>
      {token ? <label>Contraseña (mínimo 12 caracteres)<input type="password" name="password" minLength={12} maxLength={128} autoComplete="new-password" required /><small>Si ya tienes cuenta y estás aceptando una invitación, usa tu contraseña actual.</small></label> : <label>Email<input name="email" type="email" autoComplete="email" required /></label>}
      <button>{busy ? 'Procesando…' : token ? 'Actualizar acceso' : 'Enviar enlace'}</button>
    </fieldset></form>
  </details>
}
