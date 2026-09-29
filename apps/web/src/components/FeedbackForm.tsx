import { FormEvent, useState } from 'react'
import type { Assignment } from '../types'

type Props = {
  item: Assignment
  submit: (body: object) => Promise<void>
  cancel: () => void
}

export function FeedbackForm({ item, submit, cancel }: Props) {
  const [status, setStatus] = useState('completed')
  const [pain, setPain] = useState(false)
  const completed = status !== 'skipped'
  const isWater = item.training_type === 'water'

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const value = (name: string) => String(form.get(name) ?? '').trim() || null
    const waterValue = (name: string) => completed && isWater ? value(name) : null

    await submit({
      status,
      actual_minutes: completed ? Number(form.get('minutes')) : null,
      rpe: completed ? Number(form.get('rpe')) : null,
      feeling: completed ? Number(form.get('feeling')) : null,
      has_pain: pain,
      pain_area: pain ? value('pain_area') : null,
      comment: value('comment'),
      sensations: waterValue('sensations'),
      work_done: waterValue('work_done'),
      best: waterValue('best'),
      worst: waterValue('worst'),
    })
  }

  return (
    <form className="feedback" onSubmit={save}>
      <h3>¿Cómo fue el entreno?</h3>

      <label>
        Resultado
        <select value={status} onChange={event => setStatus(event.target.value)}>
          <option value="completed">Completado</option>
          <option value="partial">Parcial</option>
          <option value="skipped">No realizado</option>
        </select>
      </label>

      {completed && (
        <>
          <div className="form-row">
            <label>
              Minutos realizados
              <input
                name="minutes"
                type="number"
                min="0"
                max="1440"
                defaultValue={item.planned_minutes}
                required
              />
            </label>
            <label>
              Esfuerzo percibido (RPE)
              <input name="rpe" type="number" min="1" max="10" required />
            </label>
          </div>

          <label>
            Sensaciones generales
            <select name="feeling" defaultValue="" required>
              <option value="" disabled>Seleccionar</option>
              <option value="5">Muy buenas</option>
              <option value="4">Buenas</option>
              <option value="3">Normales</option>
              <option value="2">Cansado/a</option>
              <option value="1">Muy cansado/a</option>
            </select>
          </label>

          {isWater && (
            <div className="water">
              <h4>Sesión de agua</h4>
              <label>
                Sensaciones
                <textarea name="sensations" maxLength={1000} required />
              </label>
              <label>
                Qué se trabajó
                <textarea name="work_done" maxLength={1000} required />
              </label>
              <label>
                Lo mejor del entreno
                <textarea name="best" maxLength={1000} required />
              </label>
              <label>
                Lo peor del entreno
                <textarea name="worst" maxLength={1000} required />
              </label>
            </div>
          )}
        </>
      )}

      <label>
        ¿Tuviste molestias?
        <select
          value={pain ? 'yes' : 'no'}
          onChange={event => setPain(event.target.value === 'yes')}
        >
          <option value="no">No</option>
          <option value="yes">Sí</option>
        </select>
      </label>
      {pain && (
        <label>
          Zona de molestia
          <input name="pain_area" maxLength={120} required />
        </label>
      )}
      <label>
        Comentario adicional
        <textarea name="comment" maxLength={2000} />
      </label>

      <div className="buttons">
        <button>Guardar feedback</button>
        <button type="button" className="secondary" onClick={cancel}>
          Cancelar
        </button>
      </div>
    </form>
  )
}
