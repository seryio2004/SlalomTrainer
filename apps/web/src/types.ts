export type Membership = {
  id: string
  club_id: string
  roles: string[]
}

export type Me = {
  name: string
  memberships: Membership[]
}

export type Member = {
  active: boolean
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

export type ExerciseTarget = {
  id: string; exercise_id?: string | null; name: string; instructions: string
  sets?: number | null; reps?: number | null; kg?: number | null
  seconds?: number | null; meters?: number | null; rest_seconds?: number | null
  rir?: number | null; target_rpe?: number | null
  side?: 'bilateral' | 'left' | 'right' | 'alternating' | null
  intensity?: string | null; zone?: string | null
  load_convention?: 'total' | 'per_side' | 'bodyweight' | null
}
export type PrescriptionBlock = { id: string; title: string; instructions: string; exercises: ExerciseTarget[] }
export type DisciplineTarget = {
  water_subtype?: string | null; runs?: number | null; meters?: number | null
  seconds?: number | null; target_rpe?: number | null; model?: string | null
  resistance?: string | null; protocol?: string | null; protocol_version?: number | null
}
export type Prescription = {
  details?: DisciplineTarget | null
  title?: string; training_type?: string; venue?: string; planned_minutes?: number
  objective?: string
  blocks?: PrescriptionBlock[]
  instructions: string
  steps?: string[]
}

export type Session = {
  plan_day_id: string | null
  id: string
  title: string
  training_type: string
  venue: string
  scheduled_start: string
  group_name: string | null
  status?: string
  version?: number
  planned_minutes?: number
  prescription: Prescription
}

export type WaterFeedback = {
  sensations: string | null
  work_done: string | null
  best: string | null
  worst: string | null
}

export type SeriesResult = {
  item_id?: string | null; exercise_id?: string | null; name: string
  origin: 'prescribed' | 'added' | 'substituted'; set_number: number
  reps?: number | null; kg?: number | null; seconds?: number | null; meters?: number | null
  rir?: number | null; rpe?: number | null; side?: ExerciseTarget['side']
  load_convention?: ExerciseTarget['load_convention']; comment?: string | null
}
export type ExecutionData = {
  status: string; actual_minutes: number | null; actual_date?: string | null
  technical_quality?: number | null; muscle_fatigue?: number | null; pain_intensity?: number | null
  rpe: number | null; feeling: number | null; has_pain: boolean; pain_area: string | null
  comment: string | null; sensations?: string | null; work_done?: string | null
  best?: string | null; worst?: string | null; results: SeriesResult[]
  discipline?: Record<string, string | number | null> | null
}
export type Assignment = Session & {
  original_prescription?: Prescription
  prescription_revisions?: { version: number; prescription: Prescription; author: string; at: string; reason: string }[]
  execution_state?: string | null
  actual_date?: string | null
  execution_data?: ExecutionData | null
  execution_revisions?: { version: number; data: ExecutionData; author: string; at: string; reason: string }[]
  actual_minutes: number | null
  load: number | null
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
  known_load: number | null
  load_coverage: number
  assigned: number
  mean_rpe: number | null
  rpe_sample: number
  pain_count: number
  without_feedback: number
}

export type Page = 'calendar' | 'organize' | 'team' | 'athlete' | 'admin' | 'planning' | 'recovery' | 'perform'
