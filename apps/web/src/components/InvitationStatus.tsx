import { useResource } from '../useResource'

type Invitation = { member_id: string; name: string; expires_at: string; sent_at: string | null; attempts: number; expired: boolean }
export function InvitationStatus({ base }: { base: string }) {
  const resource = useResource<Invitation[]>(`${base}/invitations`)
  return <details><summary>Invitaciones y entrega de correo</summary>
    {resource.loading && <p>Cargando invitaciones…</p>}{resource.error && <p className="error" role="alert">{resource.error}</p>}
    <button type="button" className="secondary" disabled={resource.loading || resource.saving} onClick={() => void resource.reload().catch(() => {})}>Actualizar estado</button>
    {resource.data?.map(row => <p key={row.member_id}>{row.name} · {row.expired ? 'Caducada' : row.sent_at ? 'Correo enviado' : 'Correo pendiente'} · Intentos fallidos: {row.attempts} <button type="button" disabled={resource.saving} onClick={() => void resource.mutate(`${base}/invitations/${row.member_id}/resend`)}>Reenviar invitación</button></p>)}
    {resource.data?.length === 0 && <p>No hay invitaciones pendientes.</p>}
  </details>
}
