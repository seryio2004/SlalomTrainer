export const trainingTypes: Record<string, string> = {
  water: 'Agua',
  gym: 'Gimnasio',
  running: 'Carrera',
  ergometer: 'Ergómetro',
  core: 'Core',
  mobility: 'Movilidad',
  test: 'Test',
  recovery: 'Recuperación',
  rest: 'Descanso',
  other: 'Otro',
}

export function place(venue: string): string {
  return venue === 'home' ? 'En casa' : 'En el club'
}

export function dateTime(value: string): string {
  return new Date(value).toLocaleString('es-ES', {
    dateStyle: 'long',
    timeStyle: 'short',
  })
}

export function hour(value: string): string {
  return new Date(value).toLocaleTimeString('es-ES', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function dayKey(value: string): string {
  const date = new Date(value)
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}
