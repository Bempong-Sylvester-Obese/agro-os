export const DASHBOARD_SECTIONS = [
  'overview',
  'members',
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
}

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
  if (segment in MARKETING_PATHS) return segment
  return 'home'
}
