import { FormEvent, useState } from 'react'
import type { Member } from '../types'

export function RoleEditor({ member, save }: { member: Member; save: (id: string, roles: string[]) => Promise<void> }) {
  const [roles, setRoles] = useState(member.roles)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setSaved(false)
    try { await save(member.id, roles); setSaved(true) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'No se pudieron guardar los roles') }
    finally { setBusy(false) }
  }
  return <details><summary>Roles de {member.name}</summary><form onSubmit={submit}><fieldset disabled={busy}>
    {Object.entries({ club_admin: 'Administrador', coach: 'Entrenador', athlete: 'Deportista' }).map(([key, label]) => <label className="choice" key={key}><input type="checkbox" checked={roles.includes(key)} onChange={event => setRoles(current => event.target.checked ? [...current, key] : current.filter(role => role !== key))} />{label}</label>)}
    <button disabled={!roles.length}>Guardar roles</button>
    {error && <p className="error" role="alert">{error}</p>}{saved && <p role="status">Roles actualizados.</p>}
  </fieldset></form></details>
}
