import { FormEvent, useEffect, useState } from 'react'
import type { Member } from '../types'
import { useResource } from '../useResource'
import { dateTime } from '../format'

type ManagedGroup = {
  id: string
  name: string
  description: string
  active: boolean
  athlete_ids: string[]
  coach_ids: string[]
}
type Administration = {
  groups: ManagedGroup[]
  grants: { id: string; coach_membership_id: string; athlete_id: string }[]
}
type Audit = { id: string; actor: string; action: string; entity_id: string; occurred_at: string }
type Props = { base: string; members: Member[]; ownMemberId: string; refresh: () => Promise<void> }

const actions: Record<string, string> = {
  'member.created': 'Creación de miembro',
  'member.activated': 'Alta de miembro',
  'member.deactivated': 'Baja de miembro',
  'group.created': 'Creación de grupo',
  'group.updated': 'Cambio de grupo',
  'group.athlete_added': 'Entrada en grupo',
  'group.athlete_removed': 'Salida de grupo',
  'group.coach_granted': 'Acceso de entrenador al grupo',
  'group.coach_revoked': 'Retirada de acceso al grupo',
  'coach.direct_access_granted': 'Acceso directo a deportista',
  'coach.direct_access_revoked': 'Retirada de acceso directo',
  'season.created': 'Creación de temporada',
  'season.active': 'Activación de temporada',
  'season.closed': 'Cierre de temporada',
  'phase.created': 'Creación de fase',
  'plan.created': 'Creación de plan',
  'plan.archived': 'Archivo de plan',
  'microcycle.created': 'Creación de microciclo',
  'plan_day.created': 'Creación de día de plan',
  'session.published': 'Publicación de sesión',
  'recovery.created': 'Registro de recuperación',
  'recovery.corrected': 'Corrección de recuperación',
}

export function ClubManagement({ base, members, ownMemberId, refresh }: Props) {
  const resource = useResource<Administration>(`${base}/administration`)
  const audit = useResource<Audit[]>(`${base}/audit`)
  const { reload } = resource
  useEffect(() => {
    void reload().catch(() => {})
  }, [members, reload])

  const [groupId, setGroupId] = useState('')
  const [message, setMessage] = useState('')
  const group = resource.data?.groups.find(item => item.id === groupId) ?? resource.data?.groups[0]
  const coaches = members.filter(member => member.active && member.roles.includes('coach'))
  const athletes = members.filter(member => member.active && member.athlete_id)
  const nameOf = (id: string) => members.find(member => member.id === id)?.name ?? 'Miembro'
  const athleteName = (id: string) => members.find(member => member.athlete_id === id)?.name ?? 'Deportista'

  async function save(path: string, body?: object, method = 'POST') {
    setMessage('')
    if (await resource.mutate(base + path, body, method)) {
      await refresh().catch(() => {})
      await audit.reload().catch(() => {})
      setMessage('Cambios guardados')
      return true
    }
    return false
  }

  async function createGroup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const element = event.currentTarget
    const form = new FormData(element)
    if (await save('/groups', { name: form.get('name'), description: form.get('description') })) {
      element.reset()
    }
  }

  return (
    <>
      {resource.error && <p role="alert" className="error">{resource.error}</p>}
      {message && <p role="status" className="success">{message}</p>}
      <section>
        <h2>Miembros del club</h2>
        <p className="muted">La baja retira el acceso al club y conserva el histórico.</p>
        <div className="table-scroll">
          <table>
            <thead><tr><th>Nombre</th><th>Rol</th><th>Estado</th><th>Acción</th></tr></thead>
            <tbody>
              {members.map(member => (
                <tr key={member.id}>
                  <td>{member.name}</td>
                  <td>{member.roles.map(role => ({
                    coach: 'Entrenador', athlete: 'Deportista', club_admin: 'Administrador',
                  }[role] ?? role)).join(', ')}</td>
                  <td>{member.active ? 'Activo' : 'Inactivo'}</td>
                  <td>
                    {member.id === ownMemberId ? 'Tu cuenta' : (
                      <details>
                        <summary>{member.active ? 'Dar de baja' : 'Reactivar'}</summary>
                        <button className="secondary" disabled={resource.saving} onClick={() => void save(
                          `/members/${member.id}/status`, { active: !member.active }, 'PATCH',
                        )}>Confirmar</button>
                      </details>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section>
        <h2>Gestión de grupos</h2>
        {resource.loading && !resource.data && <p>Cargando grupos…</p>}
        {group && (
          <>
            <label>
              Grupo
              <select value={group.id} onChange={event => setGroupId(event.target.value)}>
                {resource.data?.groups.map(item => (
                  <option key={item.id} value={item.id}>{item.name}{item.active ? '' : ' · Archivado'}</option>
                ))}
              </select>
            </label>
            <details className="disclosure">
              <summary>Editar nombre, descripción y estado</summary>
              <form key={`${group.id}-${group.name}-${group.active}`} onSubmit={async event => {
                event.preventDefault()
                const form = new FormData(event.currentTarget)
                await save(`/groups/${group.id}`, {
                  name: form.get('name'), description: form.get('description'), active: form.get('active') === 'yes',
                }, 'PATCH')
              }}>
                <label>Nombre<input name="name" defaultValue={group.name} maxLength={160} required /></label>
                <label>Descripción<textarea name="description" defaultValue={group.description} maxLength={500} /></label>
                <label>
                  Estado
                  <select name="active" defaultValue={group.active ? 'yes' : 'no'}>
                    <option value="yes">Activo</option><option value="no">Archivado</option>
                  </select>
                </label>
                <button disabled={resource.saving}>Guardar grupo</button>
              </form>
            </details>
            <div className="form-row">
              <div>
                <h3>Deportistas del grupo</h3>
                {group.athlete_ids.map(id => (
                  <div className="management-row" key={id}>
                    <span>{athleteName(id)}</span>
                    <button className="text-button" disabled={resource.saving} onClick={() => void save(
                      `/groups/${group.id}/athletes/${id}`, undefined, 'DELETE',
                    )}>Retirar</button>
                  </div>
                ))}
                {group.active && (
                  <form className="inline-form" onSubmit={async event => {
                    event.preventDefault()
                    const form = new FormData(event.currentTarget)
                    await save(`/groups/${group.id}/athletes`, { athlete_id: form.get('athlete') })
                  }}>
                    <label>
                      Añadir deportista
                      <select name="athlete" required defaultValue="">
                        <option value="" disabled>Seleccionar</option>
                        {athletes.filter(member => !group.athlete_ids.includes(member.athlete_id!)).map(member => (
                          <option key={member.id} value={member.athlete_id!}>{member.name}</option>
                        ))}
                      </select>
                    </label>
                    <button disabled={resource.saving}>Añadir</button>
                  </form>
                )}
              </div>
              <div>
                <h3>Entrenadores autorizados</h3>
                {group.coach_ids.map(id => (
                  <div className="management-row" key={id}>
                    <span>{nameOf(id)}</span>
                    <button className="text-button" disabled={resource.saving} onClick={() => void save(
                      `/groups/${group.id}/coaches/${id}`, undefined, 'DELETE',
                    )}>Retirar permiso</button>
                  </div>
                ))}
                {group.active && (
                  <form className="inline-form" onSubmit={async event => {
                    event.preventDefault()
                    const form = new FormData(event.currentTarget)
                    await save(`/groups/${group.id}/coaches`, { coach_membership_id: form.get('coach') })
                  }}>
                    <label>
                      Autorizar entrenador
                      <select name="coach" required defaultValue="">
                        <option value="" disabled>Seleccionar</option>
                        {coaches.filter(member => !group.coach_ids.includes(member.id)).map(member => (
                          <option key={member.id} value={member.id}>{member.name}</option>
                        ))}
                      </select>
                    </label>
                    <button disabled={resource.saving}>Autorizar</button>
                  </form>
                )}
              </div>
            </div>
          </>
        )}
        <details className="disclosure">
          <summary>Crear grupo</summary>
          <form onSubmit={createGroup}>
            <label>Nombre<input name="name" required maxLength={160} /></label>
            <label>Descripción<textarea name="description" maxLength={500} /></label>
            <button disabled={resource.saving}>Crear grupo</button>
          </form>
        </details>
      </section>
      <section>
        <h2>Permisos directos</h2>
        {resource.data?.grants.length ? resource.data.grants.map(grant => (
          <div className="management-row" key={grant.id}>
            <span>{nameOf(grant.coach_membership_id)} → {athleteName(grant.athlete_id)}</span>
            <button className="text-button" disabled={resource.saving} onClick={() => void save(
              `/grants/${grant.id}`, undefined, 'DELETE',
            )}>Retirar permiso</button>
          </div>
        )) : <p>No hay permisos directos.</p>}
        <p className="muted">Un entrenador puede conservar acceso a través de un grupo autorizado.</p>
      </section>
      <section>
        <div className="section-head">
          <h2>Actividad administrativa</h2>
          <button className="secondary" onClick={() => void audit.reload().catch(() => {})}>Actualizar</button>
        </div>
        <p className="muted">Últimas 50 acciones. Los datos privados de recuperación no se incluyen aquí.</p>
        {audit.error && <p role="alert" className="error">{audit.error}</p>}
        {audit.data?.map(event => (
          <div className="record" key={event.id}>
            <strong>{actions[event.action] ?? event.action}</strong>
            <p>{event.actor} · {dateTime(event.occurred_at)}</p>
          </div>
        ))}
        {audit.data?.length === 0 && <p>Todavía no hay acciones registradas.</p>}
      </section>
    </>
  )
}
