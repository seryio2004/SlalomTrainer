type IconName = 'calendar' | 'training' | 'team' | 'plan' | 'recovery' | 'settings' | 'logout'

const paths: Record<IconName, string> = {
  calendar: 'M8 3v4m8-4v4M4 10h16M5 5h14a1 1 0 0 1 1 1v14H4V6a1 1 0 0 1 1-1ZM8 14h2m4 0h2m-8 3h2',
  training: 'M3 12h4l3-7 4 14 3-7h4',
  team: 'M16 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2m18 0v-2a4 4 0 0 0-3-3.87M15 3.13a4 4 0 0 1 0 7.75M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z',
  plan: 'M8 6h12M8 12h12M8 18h12M3 6h1m-1 6h1m-1 6h1',
  recovery: 'M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z',
  settings: 'M4 7h16M4 17h16M8 4v6m8 4v6',
  logout: 'M9 4H4v16h5m5-13 5 5-5 5m-6-5h11',
}

export function Icon({ name }: { name: IconName }) {
  return (
    <svg className="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={paths[name]} />
    </svg>
  )
}
