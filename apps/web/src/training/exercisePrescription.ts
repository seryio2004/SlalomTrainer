export type ExercisePrescription = {
  instruction: string
  sets: number
  repetitions: number | null
  seconds: number | null
  restSeconds: number
}

function secondsFrom(value: string | undefined): number | null {
  if (!value) return null
  const amount = Number(value.match(/\d+/)?.[0])
  if (!Number.isFinite(amount) || amount < 1) return null
  return /m|min/i.test(value) ? amount * 60 : amount
}

export function parseExercisePrescription(text: string): ExercisePrescription {
  const parts = text.split('|').map(part => part.trim()).filter(Boolean)
  const source = parts.length > 1 ? parts.slice(1).join(' ') : text
  const restMatch = source.match(/(?:descanso|recuperaci[oó]n)\s*:?\s*(\d+)\s*(min(?:utos?)?|m|seg(?:undos?)?|s)?/i)
  const restSeconds = secondsFrom(restMatch?.[0]) ?? 0
  const dosageMatch = source.match(/(\d+)\s*(?:x|×)\s*(\d+)\s*(reps?|repeticiones|rep|min(?:utos?)?|m|seg(?:undos?)?|s)?/i)

  let sets = 1
  let repetitions: number | null = null
  let seconds: number | null = null
  let instruction = parts.length > 1 ? parts[0] : text

  if (dosageMatch) {
    sets = Math.min(50, Math.max(1, Number(dosageMatch[1])))
    const amount = Number(dosageMatch[2])
    const unit = dosageMatch[3] ?? ''
    if (/rep/i.test(unit) || !unit) {
      repetitions = amount
    } else {
      seconds = secondsFrom(`${amount}${unit}`)
    }
    if (parts.length === 1) {
      instruction = text
        .replace(dosageMatch[0], '')
        .replace(restMatch?.[0] ?? '', '')
        .replace(/[|,:;–—-]+/g, ' ')
        .replace(/\s+/g, ' ')
        .trim()
    }
  }

  return { instruction, sets, repetitions, seconds, restSeconds }
}

export function stepsFromPrescription(instructions: string, steps: string[] = []): string[] {
  const explicitSteps = steps.map(step => step.trim()).filter(Boolean)
  if (explicitSteps.length) return explicitSteps

  const restMatch = instructions.match(/(?:descanso|recuperaci[oó]n)\s*:?\s*(\d+)\s*(min(?:utos?)?|m|seg(?:undos?)?|s)?/i)
  const restText = restMatch?.[0] ?? ''
  const chunks = instructions
    .split(/[\n;]+/)
    .flatMap(line => line.split(/,\s*(?=[\p{L}])/u))
    .map(line => line.trim().replace(/[.]$/, ''))
    .filter(line => /\d+\s*(?:x|×)\s*\d+/i.test(line))

  if (!chunks.length) return []
  if (!restText) return chunks
  return chunks.map(chunk => /(?:descanso|recuperaci[oó]n)/i.test(chunk)
    ? chunk
    : `${chunk} ${restText}`)
}
