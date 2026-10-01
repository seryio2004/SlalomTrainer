import { AccountAccess } from './components/AccountAccess'
import { FormEvent, useEffect, useRef, useState } from 'react'
import { api } from './api'
import { Icon } from './components/Icon'
import { WorkoutSession } from './components/WorkoutSession'
import { PlanningPage } from './components/PlanningPage'
import { RecoveryPage } from './components/RecoveryPage'
import { ClubManagement } from './components/ClubManagement'
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
    case 'planning':
      return 'Planificación'
    case 'perform':
      return 'Realizar entreno'
    case 'recovery':
      return 'Mi recuperación'
    case 'calendar':
      return 'Planifica la semana'
    case 'organize':
      return 'Organizar entreno'
    case 'team':
      return 'Deportistas y grupos'
    case 'admin':
      return 'Administración'
    case 'athlete':
      return `Entrenamiento de ${name}`
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
    <main className="login-layout">
      <div className="login-story">
        <div className="brand"><span>T</span><strong>TeiTraining</strong></div>
        <div className="login-statement">
          <p className="eyebrow">Piragüismo slalom</p>
          <h1>Cada sesión<br />cuenta.</h1>
          <p>Tu planificación, tus sensaciones y tu evolución. Todo lo que necesitas para seguir entrenando.</p>
        </div>
        <p className="login-caption">En el agua. Fuera del agua.</p>
      </div>
      <div className="login-form-area">
        <div className="login">
          <p className="eyebrow">Tu espacio de entrenamiento</p>
          <h2>Inicia sesión</h2>
          <p>Accede con la cuenta de tu club.</p>
          <AccountAccess />
          <form onSubmit={login}>
            <label>
              Correo electrónico
              <input name="email" type="email" autoComplete="username" required />
            </label>
            <label>
              Contraseña
              <input name="password" type="password" autoComplete="current-password" required />
            </label>
            <button>Entrar a TeiTraining</button>
          </form>
          {error && <p role="alert" className="error">{error}</p>}
        </div>
      </div>
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
  openWorkout: () => void
  logout: () => Promise<void>
  mobile?: boolean
  close?: () => void
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
  openWorkout,
  logout,
  mobile = false,
  close,
}: SidebarProps) {
  const selectedName = athletes.find(person => person.id === selectedAthlete)?.name

  function navigate(target: Page) {
    setPage(target)
    close?.()
  }

  function openDashboard() {
    close?.()
    void openOwnDashboard()
  }

  function signOut() {
    close?.()
    void logout()
  }

  return (
    <aside className={`sidebar ${mobile ? 'mobile-sidebar' : 'desktop-sidebar'}`}>
      <div className="brand">
        <span>T</span>
        <div>
          <strong>TeiTraining</strong>
          <small>Piragüismo slalom</small>
        </div>
        {mobile && (
          <button type="button" className="mobile-menu-close" onClick={close}>
            Cerrar
          </button>
        )}
      </div>
      <nav aria-label="Navegación principal">
        <p>{coach ? 'ENTRENADOR' : athlete ? 'DEPORTISTA' : 'CLUB'}</p>
        {coach && (
          <>
            <button
              className={page === 'calendar' ? 'active' : ''}
              aria-current={page === 'calendar' ? 'page' : undefined}
              onClick={() => navigate('calendar')}
            >
              <Icon name="calendar" />
              <span>Calendario</span>
            </button>
            <button
              className={page === 'organize' ? 'active' : ''}
              aria-current={page === 'organize' ? 'page' : undefined}
              onClick={() => navigate('organize')}
            >
              <Icon name="training" />
              <span>Organizar entreno</span>
            </button>
            <button
              className={page === 'team' ? 'active' : ''}
              aria-current={page === 'team' ? 'page' : undefined}
              onClick={() => navigate('team')}
            >
              <Icon name="team" />
              <span>Deportistas y grupos</span>
            </button>
          </>
        )}
        {(coach || admin) && (
          <button
            className={page === 'planning' ? 'active' : ''}
              aria-current={page === 'planning' ? 'page' : undefined}
            onClick={() => navigate('planning')}
          >
            <Icon name="plan" />
            <span>Planes y temporadas</span>
          </button>
        )}
        {athlete && (
          <button
            className={page === 'perform' ? 'active' : ''}
            aria-current={page === 'perform' ? 'page' : undefined}
            onClick={() => { openWorkout(); close?.() }}
          >
            <Icon name="training" />
            <span>Realizar entreno</span>
          </button>
        )}
        {athlete && (
          <button
            className={page === 'recovery' ? 'active' : ''}
              aria-current={page === 'recovery' ? 'page' : undefined}
            onClick={() => navigate('recovery')}
          >
            <Icon name="recovery" />
            <span>Recuperación</span>
          </button>
        )}
        {athlete && (
          <button
            className={page === 'athlete' && !selectedAthlete ? 'active' : ''}
            aria-current={page === 'athlete' && !selectedAthlete ? 'page' : undefined}
            onClick={openDashboard}
          >
            <Icon name="training" />
            <span>Mi entrenamiento</span>
          </button>
        )}
        {coach && selectedAthlete && (
          <button
            className={page === 'athlete' ? 'active' : ''}
            aria-current={page === 'athlete' ? 'page' : undefined}
            onClick={() => navigate('athlete')}
          >
            <Icon name="training" />
            <span>Vista de {selectedName}</span>
          </button>
        )}
        {admin && (
          <button
            className={page === 'admin' ? 'active' : ''}
              aria-current={page === 'admin' ? 'page' : undefined}
            onClick={() => navigate('admin')}
          >
            <Icon name="settings" />
            <span>Administración</span>
          </button>
        )}
      </nav>
      <div className="side-foot">
        <div className="profile-summary">
          <span className="profile-avatar">{name.slice(0, 1).toUpperCase()}</span>
          <div><strong>{name}</strong><small>{coach ? 'Entrenador' : athlete ? 'Deportista' : 'Administración'}</small></div>
        </div>
        <button onClick={signOut}><Icon name="logout" />Cerrar sesión</button>
      </div>
    </aside>
  )
}

export function App() {
  const mobileMenu = useRef<HTMLDialogElement>(null)
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
  const [selectedPlanDay, setSelectedPlanDay] = useState('')
  const [selectedWorkoutId, setSelectedWorkoutId] = useState('')

  const club = me?.memberships[0]
  const base = club ? `/clubs/${club.club_id}` : ''
  const coach = !!club?.roles.includes('coach')
  const admin = !!club?.roles.includes('club_admin')
  const athlete = !!club?.roles.includes('athlete')

  useEffect(() => {
    const viewport = window.matchMedia('(max-width: 900px)')
    const closeOnDesktop = () => {
      if (!viewport.matches && mobileMenu.current?.open) mobileMenu.current.close()
    }
    viewport.addEventListener('change', closeOnDesktop)
    return () => viewport.removeEventListener('change', closeOnDesktop)
  }, [])

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
        .catch(() => {
          setSelectedAthlete('')
          return null
        })
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
        setSelectedWorkoutId('')
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

  async function openWorkout(id = '') {
    const showingAnotherAthlete = !!selectedAthlete
    setSelectedAthlete('')
    setSelectedWorkoutId(id)
    setPage('perform')
    if (showingAnotherAthlete) {
      setDashboard(null)
      try {
        setDashboard(await api<Dashboard>(`${base}/dashboard/athlete`))
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : 'No se pudo cargar tu entrenamiento')
      }
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

  async function editSession(id: string, body: object) {
    await run(async () => {
      await api(`${base}/sessions/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      })
      setSummary(null)
      setMessage('Entreno actualizado')
    })
  }

  async function cancelSession(id: string, version: number) {
    await run(async () => {
      await api(`${base}/sessions/${id}/cancel`, {
        method: 'POST',
        body: JSON.stringify({ version }),
      })
      setSummary(null)
      setMessage('Entreno cancelado')
    })
  }

  async function report(id: string, body: object) {
    await run(async () => {
      const { operation, ...data } = body as { operation?: string }
      await api(`${base}/assignments/${id}/${operation === 'draft' ? 'draft' : 'report'}`, {
        method: operation === 'draft' ? 'PUT' : operation === 'correct' ? 'PATCH' : 'POST',
        body: JSON.stringify(data),
      })
      setMessage(operation === 'draft' ? 'Borrador guardado' : 'Entreno y feedback guardados')
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
      await api(`${base}/invitations`, {
        method: 'POST',
        body: JSON.stringify({
          email: form.get('email'),
          name: form.get('name'),
          roles: [form.get('role')],
        }),
      })
      setMessage('Invitación en cola de correo')
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
    return <main className="app-loading"><p role="status">Cargando tu espacio de entrenamiento…</p></main>
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
      <a className="skip-link" href="#main-content">Ir al contenido</a>
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
        openWorkout={openWorkout}
        logout={logout}
      />
      <div className="mobile-topbar">
        <div className="brand">
          <span>T</span>
          <div>
            <strong>TeiTraining</strong>
            <small>Piragüismo slalom</small>
          </div>
        </div>
        <button
          type="button"
          className="mobile-menu-trigger"
          aria-haspopup="dialog"
          aria-controls="mobile-navigation"
          onClick={() => mobileMenu.current?.showModal()}
        >
          Menú
        </button>
      </div>
      <dialog
        id="mobile-navigation"
        ref={mobileMenu}
        className="mobile-menu-dialog"
        aria-label="Menú de navegación"
        onClick={event => {
          if (event.target === event.currentTarget) event.currentTarget.close()
        }}
      >
        <Sidebar
          mobile
          close={() => mobileMenu.current?.close()}
          name={me.name}
          page={page}
          coach={coach}
          athlete={athlete}
          admin={admin}
          selectedAthlete={selectedAthlete}
          athletes={athletes}
          setPage={setPage}
          openOwnDashboard={openOwnDashboard}
          openWorkout={openWorkout}
          logout={logout}
        />
      </dialog>
      <main className="content" id="main-content">
        <header className="page-header">
          <div>
            <p className="eyebrow">
              {page === 'athlete' || page === 'recovery' || page === 'perform' ? 'Espacio deportista' : 'Gestión del club'}
            </p>
            <h1>{pageTitle(page, dashboard?.name ?? me.name)}</h1>
          </div>
          <div className="account-actions">
            <time className="header-date" dateTime={new Date().toISOString().slice(0, 10)}>
              {new Date().toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long' })}
            </time>
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
            create={() => {
              setSelectedPlanDay('')
              setPage('organize')
            }}
            loadSummary={loadSummary}
            editSession={editSession}
            cancelSession={cancelSession}
          />
        )}
        {page === 'organize' && coach && (
          <OrganizePage
            key={selectedPlanDay}
            base={base}
            initialDay={selectedPlanDay}
            athletes={athletes}
            groups={groups}
            publish={publishSession}
          />
        )}
        {page === 'planning' && (coach || admin) && (
          <PlanningPage
            base={base}
            admin={admin}
            coach={coach}
            sessions={sessions}
            organize={dayId => {
              setSelectedPlanDay(dayId)
              setPage('organize')
            }}
          />
        )}
        {page === 'recovery' && athlete && <RecoveryPage base={base} />}
        {page === 'perform' && athlete && !dashboard && (
          <section>Cargando tus entrenamientos…</section>
        )}
        {page === 'perform' && athlete && dashboard && (
          <WorkoutSession
            assignments={dashboard.assignments}
            selectedId={selectedWorkoutId}
            onSelect={setSelectedWorkoutId}
            onReport={async (id, body) => {
              await report(id, body)
              setPage('athlete')
              setSelectedWorkoutId('')
            }}
          />
        )}
        {page === 'team' && coach && (
          <TeamPage
            base={base}
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
              base={base}
              report={report}
              openWorkout={openWorkout}
            />
          ) : (
            <section>Cargando vista del deportista…</section>
          )
        )}
        {page === 'admin' && admin && (
          <>
            <AdminPage
              base={base}
              members={members}
              createMember={createMember}
              createGrant={createGrant}
              changeRoles={(id, roles) => run(async () => {
                await api(`${base}/members/${id}/roles`, { method: 'PATCH', body: JSON.stringify({ roles }) })
                setMessage('Roles actualizados')
              })}
            />
            <ClubManagement
              base={base}
              members={members}
              ownMemberId={club.id}
              refresh={() => refresh(me, '')}
            />
          </>
        )}
      </main>
    </div>
  )
}
