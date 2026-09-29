export type Membership = {
  club_id: string
  roles: string[]
}

export type Me = {
  name: string
  memberships: Membership[]
}

export type Member = {
  id: string
  name: string
  roles: string[]
  athlete_id: string | null
}

export type Athlete = {
  id: string
  name: string
}

export type Group = {
  id: string
  name: string
  description: string
  athlete_ids: string[]
}

export type Prescription = {
  instructions: string
  steps?: string[]
}

export type Session = {
  id: string
  title: string
  training_type: string
  venue: string
  scheduled_start: string
  group_name: string | null
  prescription: Prescription
}

export type WaterFeedback = {
  sensations: string | null
  work_done: string | null
  best: string | null
  worst: string | null
}

export type Assignment = Session & {
  status: string
  planned_minutes: number
  comment: string | null
  water_feedback: WaterFeedback | null
}

export type Dashboard = {
  name: string
  athlete_id: string
  assignments: Assignment[]
  fatigue: {
    band: string
    available: boolean
  }
}

export type Summary = {
  id: string
  counts: Record<string, number>
  known_load: number
  load_coverage: number
}

export type Page = 'calendar' | 'organize' | 'team' | 'athlete' | 'admin'
