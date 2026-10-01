import { InvitationStatus } from './InvitationStatus'
import { RoleEditor } from './RoleEditor'
import { FormEvent, useState } from 'react'
import type { Member } from '../types'

type Props = {
  base: string
  changeRoles: (id: string, roles: string[]) => Promise<void>
  members: Member[]
  createMember: (form: FormData) => Promise<void>
  createGrant: (form: FormData) => Promise<void>
}

export function AdminPage({ base, members, createMember, createGrant, changeRoles }: Props) {
  const [busy, setBusy] = useState(false)
  async function submitMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    setBusy(true)
    try {
      await createMember(new FormData(form))
      form.reset()
    } catch {
      // The parent displays the request error.
    } finally { setBusy(false) }
  }

  async function submitGrant(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    try {
      await createGrant(new FormData(event.currentTarget))
    } catch {
      // The parent displays the request error.
    }
  }

  return (
    <>
      <section>
        <h2>Cuentas y permisos</h2>
        <div className="columns">
          <form onSubmit={submitMember}>
            <h3>Invitar al club</h3>
            <label>
              Nombre
              <input name="name" required />
            </label>
            <label>
              Email
              <input name="email" type="email" required />
            </label>
            <label>
              Rol
              <select name="role">
                <option value="athlete">Deportista</option>
                <option value="coach">Entrenador</option>
              </select>
            </label>
            <button disabled={busy}>{busy ? 'Enviando…' : 'Enviar invitación'}</button>
          </form>

          <form onSubmit={submitGrant}>
            <h3>Autorizar entrenador</h3>
            <label>
              Entrenador
              <select name="coach" required>
                {members.filter(member => member.active && member.roles.includes('coach')).map(member => (
                  <option key={member.id} value={member.id}>{member.name}</option>
                ))}
              </select>
            </label>
            <label>
              Deportista
              <select name="athlete" required>
                {members.filter(member => member.active && member.athlete_id).map(member => (
                  <option key={member.id} value={member.athlete_id!}>
                    {member.name}
                  </option>
                ))}
              </select>
            </label>
            <button>Conceder acceso</button>
          </form>
        </div>
        <InvitationStatus base={base} />
        {members.map(member => <RoleEditor key={member.id} member={member} save={changeRoles} />)}
      </section>


    </>
  )
}
