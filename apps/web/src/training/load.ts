import { dayKey } from '../format'

export type LoadRecord = {
  scheduled_start: string
  actual_date?: string | null
  status: string
  training_type: string
  venue: string
  load: number | null
  actual_minutes: number | null
}

export type LoadBucket = {
  start: string
  end: string
  sessions: number
  known: number
  club: number
  home: number
}

export type LoadMetric = 'load' | 'actual_minutes'

function localDay(date: Date) {
  return dayKey(date.toISOString())
}

/** Calendar arithmetic keeps days intact across daylight-saving changes. */
function shiftDay(date: Date, offset: number) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + offset, 12)
}

export function summarizeLoad(
  assignments: LoadRecord[],
  days: number,
  metric: LoadMetric,
  now = new Date(),
) {
  const start = shiftDay(now, 1 - days)
  const firstDay = localDay(start)
  const lastDay = localDay(now)
  const groupSize = days > 28 ? 7 : 1
  const buckets: LoadBucket[] = []
  const bucketByDay = new Map<string, LoadBucket>()

  for (let offset = 0; offset < days; offset += groupSize) {
    const endOffset = Math.min(offset + groupSize - 1, days - 1)
    const bucket: LoadBucket = {
      start: localDay(shiftDay(start, offset)),
      end: localDay(shiftDay(start, endOffset)),
      sessions: 0,
      known: 0,
      club: 0,
      home: 0,
    }
    buckets.push(bucket)
    for (let day = offset; day <= endOffset; day += 1) {
      bucketByDay.set(localDay(shiftDay(start, day)), bucket)
    }
  }

  const records = assignments.filter(item => {
    if ('actual_date' in item && !item.actual_date) return false
    const instant = new Date(item.actual_date ? `${item.actual_date}T12:00:00` : item.scheduled_start)
    if (!Number.isFinite(instant.getTime()) || (!item.actual_date && instant > now)) return false
    const date = item.actual_date ?? localDay(instant)
    return ['completed', 'partial'].includes(item.status)
      && item.training_type !== 'rest'
      && date >= firstDay && date <= lastDay
  })
  let total = 0
  let known = 0
  let minutes = 0
  let knownMinutes = 0
  const byType = new Map<string, number>()

  for (const item of records) {
    const bucket = bucketByDay.get(item.actual_date ?? dayKey(item.scheduled_start))!
    bucket.sessions += 1
    if (item.actual_minutes != null && Number.isFinite(item.actual_minutes)) {
      minutes += item.actual_minutes
      knownMinutes += 1
    }
    const value = item[metric]
    if (value == null || !Number.isFinite(value) || value < 0) continue
    bucket.known += 1
    bucket[item.venue === 'home' ? 'home' : 'club'] += value
    total += value
    known += 1
    byType.set(item.training_type, (byType.get(item.training_type) ?? 0) + value)
  }

  return {
    buckets, total, known, minutes, knownMinutes,
    sessions: records.length,
    missing: records.length - known,
    firstDay, lastDay,
    byType: [...byType.entries()].sort((a, b) => b[1] - a[1]),
  }
}
