import { FormEvent } from 'react'
import type { Member } from '../types'

type Props = {
  members: Member[]
  createMember: (form: FormData) => Promise<void>
  createGrant: (form: FormData) => Promise<void>
}

export function AdminPage({ members, createMember, createGrant }: Props) {
  async function submitMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    try {
      await createMember(new FormData(form))
      form.reset()
    } catch {
      // The parent displays the request error.
    }
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
            <h3>Crear cuenta de prueba</h3>
            <label>
              Nombre
              <input name="name" required />
            </label>
            <label>
              Email
              <input name="email" type="email" required />
            </label>
            <label>
              Contraseña inicial
              <input name="password" type="password" minLength={12} required />
            </label>
            <label>
              Rol
              <select name="role">
                <option value="athlete">Deportista</option>
                <option value="coach">Entrenador</option>
              </select>
            </label>
            <button>Crear cuenta</button>
          </form>

          <form onSubmit={submitGrant}>
            <h3>Autorizar entrenador</h3>
            <label>
              Entrenador
              <select name="coach" required>
                {members.filter(member => member.roles.includes('coach')).map(member => (
                  <option key={member.id} value={member.id}>{member.name}</option>
                ))}
              </select>
            </label>
            <label>
              Deportista
              <select name="athlete" required>
                {members.filter(member => member.athlete_id).map(member => (
                  <option key={member.id} value={member.athlete_id!}>
                    {member.name}
                  </option>
                ))}
              </select>
            </label>
            <button>Conceder acceso</button>
          </form>
        </div>
      </section>

      <section>
        <h2>Miembros</h2>
        <ul>
          {members.map(member => (
            <li key={member.id}>
              {member.name} · {member.roles.join(', ')}
            </li>
          ))}
        </ul>
      </section>
    </>
  )
}
