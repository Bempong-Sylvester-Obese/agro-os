export const DASHBOARD_SECTIONS = [
  'overview',
  'members',
  'workers',
  'tasks',
  'attendance',
  'payroll',
  'payments',
  'loans',
  'production',
  'intake',
  'aggregation',
  'buyers',
  'sales',
  'settlements',
  'scores',
  'sms',
  'ussd',
  'announcements',
  'activity',
  'settings',
]

export const MARKETING_PATHS = {
  home: '/',
  solutions: '/solutions',
  features: '/features',
  pricing: '/pricing',
  bookDemo: '/book-demo',
  compliance: '/compliance',
  investors: '/investors',
}

const MARKETING_SEGMENT_TO_KEY = Object.fromEntries(
  Object.entries(MARKETING_PATHS)
    .filter(([, path]) => path !== '/')
    .map(([key, path]) => [path.replace(/^\//, '').split('/')[0], key]),
)

export function dashboardPath(section = 'overview') {
  const safe = DASHBOARD_SECTIONS.includes(section) ? section : 'overview'
  return safe === 'overview' ? '/dashboard' : `/dashboard/${safe}`
}

export function pageKeyFromPath(pathname) {
  if (pathname === '/' || pathname === '') return 'home'
  if (pathname.startsWith('/dashboard')) return 'dashboard'
  if (pathname.startsWith('/login')) return 'login'
  if (pathname.startsWith('/subscribe')) return 'subscription'
  const segment = pathname.replace(/^\//, '').split('/')[0]
  return MARKETING_SEGMENT_TO_KEY[segment] || 'home'
}
