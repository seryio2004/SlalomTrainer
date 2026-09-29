import { useState } from 'react'
import { dayKey, hour, place } from '../format'
import type { Session } from '../types'

const weekdays = ['L', 'M', 'X', 'J', 'V', 'S', 'D']

export function Calendar({ items }: { items: Session[] }) {
  const [month, setMonth] = useState(() => {
    const today = new Date()
    return new Date(today.getFullYear(), today.getMonth(), 1)
  })
  const [selected, setSelected] = useState('')

  const year = month.getFullYear()
  const monthIndex = month.getMonth()
  const offset = (new Date(year, monthIndex, 1).getDay() + 6) % 7
  const daysInMonth = new Date(year, monthIndex + 1, 0).getDate()
  const cells = Array.from(
    { length: offset + daysInMonth },
    (_, index) => index < offset ? 0 : index - offset + 1,
  )
  const selectedItems = items.filter(item => dayKey(item.scheduled_start) === selected)

  return (
    <section className="calendar">
      <div className="section-head">
        <div>
          <p className="eyebrow">Planificación</p>
          <h2>Calendario</h2>
        </div>
        <div className="month">
          <button
            aria-label="Mes anterior"
            onClick={() => setMonth(new Date(year, monthIndex - 1, 1))}
          >
            ‹
          </button>
          <strong>
            {month.toLocaleDateString('es-ES', { month: 'long', year: 'numeric' })}
          </strong>
          <button
            aria-label="Mes siguiente"
            onClick={() => setMonth(new Date(year, monthIndex + 1, 1))}
          >
            ›
          </button>
        </div>
      </div>

      <div className="calendar-grid">
        {weekdays.map(day => (
          <span className="weekday" key={day}>{day}</span>
        ))}
        {cells.map((day, index) => {
          if (!day) {
            return <span key={`empty-${index}`} />
          }

          const key = [
            year,
            String(monthIndex + 1).padStart(2, '0'),
            String(day).padStart(2, '0'),
          ].join('-')
          const events = items.filter(item => dayKey(item.scheduled_start) === key)
          const monthName = month.toLocaleDateString('es-ES', { month: 'long' })

          return (
            <button
              key={key}
              className={`day${selected === key ? ' selected' : ''}`}
              aria-label={`${day} de ${monthName}, ${events.length} entrenamientos`}
              aria-pressed={selected === key}
              onClick={() => setSelected(key)}
            >
              <span>{day}</span>
              <span className="dots">
                {events.slice(0, 3).map(event => (
                  <i
                    key={event.id}
                    className={event.venue === 'home' ? 'home' : ''}
                  />
                ))}
              </span>
            </button>
          )
        })}
      </div>

      {selected && (
        <div className="day-detail">
          <strong>
            {new Date(`${selected}T12:00:00`).toLocaleDateString('es-ES', {
              dateStyle: 'full',
            })}
          </strong>
          {selectedItems.length ? (
            <ul>
              {selectedItems.map(item => (
                <li key={item.id}>
                  {hour(item.scheduled_start)} · {item.title} · {place(item.venue)}
                </li>
              ))}
            </ul>
          ) : (
            <p>Sin entrenamientos.</p>
          )}
        </div>
      )}
    </section>
  )
}
