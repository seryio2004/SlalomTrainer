const { strict: assert } = require('node:assert')
const { test } = require('node:test')
const { summarizeLoad } = require('../src/training/load.js')

const now = new Date('2026-04-02T18:00:00+02:00')

function session(changes = {}) {
  return {
    scheduled_start: '2026-04-01T17:00:00+02:00',
    status: 'completed',
    training_type: 'water',
    venue: 'club',
    load: 300,
    actual_minutes: 60,
    ...changes,
  }
}

test('sums completed and partial sessions, excluding plans, rest and cancelled sessions', () => {
  const summary = summarizeLoad([
    session(),
    session({ status: 'partial', venue: 'home', training_type: 'mobility', load: 40, actual_minutes: 20 }),
    session({ status: 'planned' }),
    session({ status: 'cancelled' }),
    session({ status: 'skipped' }),
    session({ training_type: 'rest' }),
    session({ scheduled_start: '2026-04-03T18:00:00+02:00' }),
  ], 7, 'load', now)
  assert.equal(summary.total, 340)
  assert.equal(summary.sessions, 2)
  assert.equal(summary.minutes, 80)
  assert.deepEqual(summary.byType, [['water', 300], ['mobility', 40]])
  assert.equal(summary.buckets.reduce((sum, bucket) => sum + bucket.club, 0), 300)
  assert.equal(summary.buckets.reduce((sum, bucket) => sum + bucket.home, 0), 40)
})

test('missing load is not zero, while a measured zero remains valid', () => {
  const summary = summarizeLoad([
    session({ load: null }),
    session({ load: 0, actual_minutes: 0 }),
  ], 7, 'load', now)
  assert.equal(summary.sessions, 2)
  assert.equal(summary.known, 1)
  assert.equal(summary.missing, 1)
  assert.equal(summary.total, 0)
  const duration = summarizeLoad([session({ load: null })], 7, 'actual_minutes', now)
  assert.equal(duration.known, 1)
  assert.equal(duration.total, 60)
})

test('keeps calendar-day boundaries through daylight saving and includes the first day', () => {
  const summary = summarizeLoad([
    session({ scheduled_start: '2026-03-27T00:00:00+01:00' }),
    session({ scheduled_start: '2026-03-26T23:59:00+01:00' }),
    session({ scheduled_start: '2026-03-29T03:30:00+02:00' }),
    session({ scheduled_start: '2026-04-02T20:00:00+02:00' }),
  ], 7, 'load', now)
  assert.equal(summary.firstDay, '2026-03-27')
  assert.equal(summary.lastDay, '2026-04-02')
  assert.equal(summary.buckets.length, 7)
  assert.equal(summary.sessions, 2)
  assert.equal(summary.buckets[0].club, 300)
  assert.equal(summary.buckets[2].club, 300)
})

test('84-day view groups into twelve non-overlapping seven-day buckets', () => {
  const records = Array.from({ length: 84 }, (_, index) => session({
    scheduled_start: new Date(2026, 3, 2 - index, 12).toISOString(),
    load: 10,
  }))
  const summary = summarizeLoad(records, 84, 'load', now)
  assert.equal(summary.buckets.length, 12)
  assert.equal(summary.total, 840)
  assert.ok(summary.buckets.every(bucket => bucket.sessions === 7 && bucket.club === 70))
})

test('an empty period has no fabricated measurements', () => {
  const summary = summarizeLoad([], 28, 'load', now)
  assert.equal(summary.known, 0)
  assert.equal(summary.sessions, 0)
  assert.equal(summary.buckets.length, 28)
  assert.deepEqual(summary.byType, [])
})

test('uses actual local execution date, excludes undated historical records and preserves zero', () => {
  const summary = summarizeLoad([
    session({ scheduled_start: '2026-04-10T17:00:00+02:00', actual_date: '2026-04-01', load: 315 }),
    session({ actual_date: null }),
    session({ actual_date: '2026-04-02', load: 0 }),
  ], 7, 'load', now)
  assert.equal(summary.total, 315)
  assert.equal(summary.sessions, 2)
  assert.equal(summary.buckets[5].club, 315)
  assert.equal(summary.known, 2)
})
