export type Period = {
  id: string
  name: string
  starts_on: string
  ends_on: string
  objectives: string
}

export type Season = Period & {
  status: 'draft' | 'active' | 'closed'
  age_reference_date: string
}

export type Phase = Period & { season_id: string }
export type Plan = Period & { phase_id: string; status: string }
export type Microcycle = Period & { plan_id: string }
export type PlanDay = { id: string; microcycle_id: string; local_date: string }

export type Planning = {
  timezone: string
  seasons: Season[]
  phases: Phase[]
  plans: Plan[]
  microcycles: Microcycle[]
  days: PlanDay[]
}

export function availableDays(planning: Planning): PlanDay[] {
  const openSeasons = planning.seasons.filter(item => item.status !== 'closed')
  const phases = planning.phases.filter(item => openSeasons.some(s => s.id === item.season_id))
  const plans = planning.plans.filter(item =>
    item.status !== 'archived' && phases.some(phase => phase.id === item.phase_id))
  const cycles = planning.microcycles.filter(item => plans.some(plan => plan.id === item.plan_id))
  return planning.days.filter(item => cycles.some(cycle => cycle.id === item.microcycle_id))
}

export function dayLabel(planning: Planning, day: PlanDay): string {
  const cycle = planning.microcycles.find(item => item.id === day.microcycle_id)
  const plan = planning.plans.find(item => item.id === cycle?.plan_id)
  return `${day.local_date} · ${plan?.name ?? ''} · ${cycle?.name ?? ''}`
}
