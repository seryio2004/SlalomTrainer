import { FormEvent, useEffect, useState } from 'react'
import { api } from './api'
import { AdminPage } from './components/AdminPage'
import { AthleteView } from './components/AthleteView'
import { CoachCalendarPage, OrganizePage, TeamPage } from './components/CoachPages'
import type {
  Athlete,
  Dashboard,
  Group,
  Me,
  Member,
  Page,
  Session,
  Summary,
} from './types'

function initialPage(me: Me): Page {
  const roles = me.memberships[0]?.roles ?? []
  if (roles.includes('coach')) {
    return 'calendar'
  }
  if (roles.includes('athlete')) {
    return 'athlete'
  }
  return 'admin'
}

function pageTitle(page: Page, name: string): string {
  switch (page) {
    case 'calendar':
      return 'Planifica la semana'
    case 'organize':
      return 'Organizar entreno'
    case 'team':
      return 'Deportistas y grupos'
    case 'admin':
      return 'Administración'
    case 'athlete':
      return `Hola, ${name}`
  }
}

function LoginPage({
  login,
  error,
}: {
  login: (event: FormEvent<HTMLFormElement>) => Promise<void>
  error: string
}) {
  return (
    <main className="login">
      <p className="eyebrow">TeiTraining</p>
      <h1>Tu entrenamiento, en un solo lugar.</h1>
      <p>Planificación y seguimiento para piragüismo slalom.</p>
      <form onSubmit={login}>
        <label>
          Email
          <input name="email" type="email" autoComplete="username" required />
        </label>
        <label>
          Contraseña
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            required
          />
        </label>
        <button>Entrar</button>
      </form>
      {error && <p role="alert" className="error">{error}</p>}
    </main>
  )
}

type SidebarProps = {
  name: string
  page: Page
  coach: boolean
  athlete: boolean
  admin: boolean
  selectedAthlete: string
  athletes: Athlete[]
  setPage: (page: Page) => void
  openOwnDashboard: () => Promise<void>
  logout: () => Promise<void>
}

function Sidebar({
  name,
  page,
  coach,
  athlete,
  admin,
  selectedAthlete,
  athletes,
  setPage,
  openOwnDashboard,
  logout,
}: SidebarProps) {
  const selectedName = athletes.find(person => person.id === selectedAthlete)?.name

  return (
    <aside className="sidebar">
      <div className="brand">
        <span>T</span>
        <div>
          <strong>TeiTraining</strong>
          <small>Piragüismo slalom</small>
        </div>
      </div>
      <nav>
        <p>MENÚ</p>
        {coach && (
          <>
            <button
              className={page === 'calendar' ? 'active' : ''}
              onClick={() => setPage('calendar')}
            >
              Calendario
            </button>
            <button
              className={page === 'organize' ? 'active' : ''}
              onClick={() => setPage('organize')}
            >
              Organizar entreno
            </button>
            <button
              className={page === 'team' ? 'active' : ''}
              onClick={() => setPage('team')}
            >
              Deportistas y grupos
            </button>
          </>
        )}
        {athlete && (
          <button
            className={page === 'athlete' && !selectedAthlete ? 'active' : ''}
            onClick={openOwnDashboard}
          >
            Mi entrenamiento
          </button>
        )}
        {coach && selectedAthlete && (
          <button
            className={page === 'athlete' ? 'active' : ''}
            onClick={() => setPage('athlete')}
          >
            Vista de {selectedName}
          </button>
        )}
        {admin && (
          <button
            className={page === 'admin' ? 'active' : ''}
            onClick={() => setPage('admin')}
          >
            Administración
          </button>
        )}
      </nav>
      <div className="side-foot">
        <span>{name}</span>
        <button onClick={logout}>Cerrar sesión</button>
      </div>
    </aside>
  )
}

export function App() {
  const [me, setMe] = useState<Me | null>(null)
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [page, setPage] = useState<Page>('athlete')

  const [members, setMembers] = useState<Member[]>([])
  const [athletes, setAthletes] = useState<Athlete[]>([])
  const [groups, setGroups] = useState<Group[]>([])
  const [sessions, setSessions] = useState<Session[]>([])
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [summary, setSummary] = useState<Summary | null>(null)
  const [selectedAthlete, setSelectedAthlete] = useState('')

  const club = me?.memberships[0]
  const base = club ? `/clubs/${club.club_id}` : ''
  const coach = !!club?.roles.includes('coach')
  const admin = !!club?.roles.includes('club_admin')
  const athlete = !!club?.roles.includes('athlete')

  async function refresh(current: Me, athleteId = selectedAthlete) {
    const member = current.memberships[0]
    if (!member) return

    const root = `/clubs/${member.club_id}`
    const canCoach = member.roles.includes('coach')
    const canAdmin = member.roles.includes('club_admin')
    const canAthlete = member.roles.includes('athlete')

    let dashboardRequest: Promise<Dashboard | null> = Promise.resolve(null)
    if (canCoach && athleteId) {
      dashboardRequest = api<Dashboard>(`${root}/athletes/${athleteId}/dashboard`)
    } else if (canAthlete) {
      dashboardRequest = api<Dashboard>(`${root}/dashboard/athlete`)
    }

    const [newMembers, newAthletes, newGroups, newSessions, newDashboard] =
      await Promise.all([
        canAdmin ? api<Member[]>(`${root}/members`) : Promise.resolve([]),
        canCoach ? api<Athlete[]>(`${root}/athletes`) : Promise.resolve([]),
        canCoach ? api<Group[]>(`${root}/groups`) : Promise.resolve([]),
        canCoach ? api<Session[]>(`${root}/sessions`) : Promise.resolve([]),
        dashboardRequest,
      ])

    setMembers(newMembers)
    setAthletes(newAthletes)
    setGroups(newGroups)
    setSessions(newSessions)
    setDashboard(newDashboard)
  }

  useEffect(() => {
    api<Me>('/me')
      .then(async current => {
        setMe(current)
        setPage(initialPage(current))
        await refresh(current, '')
      })
      .catch(() => setMe(null))
      .finally(() => setBusy(false))
  }, [])

  async function run(action: () => Promise<void>, reload = true) {
    setError('')
    setMessage('')
    try {
      await action()
      if (reload && me) await refresh(me)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Error inesperado')
      throw reason
    }
  }

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setError('')

    try {
      await api('/auth/login', {
        method: 'POST',
        body: JSON.stringify({
          email: form.get('email'),
          password: form.get('password'),
        }),
      })
      const current = await api<Me>('/me')
      setMe(current)
      setPage(initialPage(current))
      await refresh(current, '')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Error de acceso')
    }
  }

  async function logout() {
    try {
      await run(async () => {
        await api('/auth/logout', { method: 'POST' })
        setMe(null)
        setDashboard(null)
        setSelectedAthlete('')
      }, false)
    } catch {
      // run already shows the error in the interface.
    }
  }

  async function openOwnDashboard() {
    setSelectedAthlete('')
    setPage('athlete')
    try {
      setDashboard(await api<Dashboard>(`${base}/dashboard/athlete`))
    } catch {
      setError('No se pudo cargar la vista')
    }
  }

  async function openAthlete(id: string) {
    setSelectedAthlete(id)
    setDashboard(null)
    setPage('athlete')
    try {
      setDashboard(await api<Dashboard>(`${base}/athletes/${id}/dashboard`))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'No se pudo abrir la vista')
    }
  }

  async function publishSession(data: object) {
    await run(async () => {
      await api(`${base}/sessions`, {
        method: 'POST',
        body: JSON.stringify(data),
      })
      setPage('calendar')
      setMessage('Entreno publicado')
    })
  }

  async function report(id: string, body: object) {
    await run(async () => {
      await api(`${base}/assignments/${id}/report`, {
        method: 'POST',
        body: JSON.stringify(body),
      })
      setMessage('Entreno y feedback guardados')
    })
  }

  async function loadSummary(id: string) {
    try {
      setSummary(await api<Summary>(`${base}/sessions/${id}/summary`))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Error de seguimiento')
    }
  }

  async function createMember(form: FormData) {
    await run(async () => {
      await api(`${base}/members`, {
        method: 'POST',
        body: JSON.stringify({
          email: form.get('email'),
          name: form.get('name'),
          password: form.get('password'),
          roles: [form.get('role')],
        }),
      })
      setMessage('Cuenta creada')
    })
  }

  async function createGrant(form: FormData) {
    await run(async () => {
      await api(`${base}/grants`, {
        method: 'POST',
        body: JSON.stringify({
          coach_membership_id: form.get('coach'),
          athlete_id: form.get('athlete'),
        }),
      })
      setMessage('Permiso concedido')
    })
  }

  if (busy) {
    return <main className="login"><p>Cargando…</p></main>
  }
  if (!me) {
    return <LoginPage login={login} error={error} />
  }
  if (!club) {
    return (
      <main>
        <h1>TeiTraining</h1>
        <p>Tu cuenta no pertenece a ningún club activo.</p>
      </main>
    )
  }

  return (
    <div className="shell">
      <Sidebar
        name={me.name}
        page={page}
        coach={coach}
        athlete={athlete}
        admin={admin}
        selectedAthlete={selectedAthlete}
        athletes={athletes}
        setPage={setPage}
        openOwnDashboard={openOwnDashboard}
        logout={logout}
      />
      <main className="content">
        <header>
          <div>
            <p className="eyebrow">
              {page === 'athlete' ? 'Espacio deportista' : 'Espacio entrenador'}
            </p>
            <h1>{pageTitle(page, dashboard?.name ?? me.name)}</h1>
          </div>
          <div className="account-actions">
            <span className="user-pill">{me.name}</span>
            <button type="button" className="switch-account" onClick={logout}>
              Cambiar cuenta
            </button>
          </div>
        </header>

        {error && <p role="alert" className="error">{error}</p>}
        {message && <p role="status" className="success">{message}</p>}

        {page === 'calendar' && coach && (
          <CoachCalendarPage
            sessions={sessions}
            summary={summary}
            create={() => setPage('organize')}
            loadSummary={loadSummary}
          />
        )}
        {page === 'organize' && coach && (
          <OrganizePage
            athletes={athletes}
            groups={groups}
            publish={publishSession}
          />
        )}
        {page === 'team' && coach && (
          <TeamPage
            athletes={athletes}
            groups={groups}
            openAthlete={openAthlete}
          />
        )}
        {page === 'athlete' && (athlete || (coach && !!selectedAthlete)) && (
          dashboard ? (
            <AthleteView
              key={dashboard.athlete_id}
              dashboard={dashboard}
              editable={athlete && !selectedAthlete}
              report={report}
            />
          ) : (
            <section>Cargando vista del deportista…</section>
          )
        )}
        {page === 'admin' && admin && (
          <AdminPage
            members={members}
            createMember={createMember}
            createGrant={createGrant}
          />
        )}
      </main>
    </div>
  )
}
