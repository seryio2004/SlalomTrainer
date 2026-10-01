import type { DisciplineTarget } from '../types'

export function readDiscipline(form: FormData): DisciplineTarget | null {
  const keys = ['water_subtype', 'runs', 'meters', 'seconds', 'target_rpe', 'model', 'resistance', 'protocol', 'protocol_version'] as const
  const details: DisciplineTarget = {}
  for (const key of keys) {
    const text = String(form.get('target_' + key) ?? '').trim()
    if (['water_subtype', 'model', 'resistance', 'protocol'].includes(key)) Object.assign(details, { [key]: text || null })
    else Object.assign(details, { [key]: text === '' ? null : Number(text) })
  }
  return Object.values(details).some(value => value != null) ? details : null
}

export function DisciplinePrescription({ kind, details }: { kind: string; details?: DisciplineTarget | null }) {
  if (!['water', 'running', 'ergometer', 'test'].includes(kind)) return null
  return <fieldset><legend>Objetivos específicos · opcionales</legend>
    {kind === 'water' && <><label>Subtipo<select name="target_water_subtype" defaultValue={details?.water_subtype ?? ''}><option value="">Sin especificar</option><option value="technique">Técnica</option><option value="base">Base</option><option value="intensity">Intensidad</option><option value="simulation">Simulación</option><option value="specific">Específico</option></select></label><label>Mangas previstas<input type="number" name="target_runs" min="0" defaultValue={details?.runs ?? ''} /></label><label>RPE objetivo<input type="number" name="target_target_rpe" min="1" max="10" defaultValue={details?.target_rpe ?? ''} /></label></>}
    {kind !== 'water' && <><label>Distancia prevista (m)<input type="number" name="target_meters" min="0" step="any" defaultValue={details?.meters ?? ''} list={kind === 'test' ? 'test-distances' : undefined} /></label><datalist id="test-distances"><option value="200" /><option value="500" /><option value="1000" /></datalist><label>Tiempo previsto (s)<input type="number" name="target_seconds" min="0" step="any" defaultValue={details?.seconds ?? ''} /></label></>}
    {['ergometer', 'test'].includes(kind) && <><label>Modelo<input name="target_model" maxLength={160} defaultValue={details?.model ?? ''} /></label><label>Resistencia / drag y escala<input name="target_resistance" maxLength={160} defaultValue={details?.resistance ?? ''} /></label></>}
    {kind === 'test' && <><label>Protocolo<textarea name="target_protocol" maxLength={2000} defaultValue={details?.protocol ?? ''} /></label><label>Versión del protocolo<input type="number" min="1" name="target_protocol_version" defaultValue={details?.protocol_version ?? ''} /></label></>}
  </fieldset>
}
