import { API_URL, apiFetch, isTransportFailure } from './config'

const PLANS_FALLBACK = [
  {
    key: 'starter', track: 'cooperative', name: 'Starter', price: 'Free',
    cadence: 'No card required',
    description: 'Establish a reliable digital member register and start collecting dues.',
    features: ['Up to 10 members', 'MoMo payment collection', 'Member and dues dashboard', '100 SMS messages per month', 'Email support'],
    cta: 'Create free workspace', bands: null,
  },
  {
    key: 'growth', track: 'cooperative', name: 'Growth', price: 'GHS 299',
    cadence: 'per organisation / month',
    description: 'Run payments, credit workflows, communication, and field operations at scale.',
    features: ['AgroCredit Trust Scores', 'USSD access', 'Unlimited payment records', '1,000 SMS messages per month', 'Priority support'],
    cta: 'Start Growth onboarding', featured: true, badge: 'Most selected',
    bands: [
      { key: 'base', label: 'Up to 50 members', capacity: 50, price: 299 },
      { key: 'plus_50', label: 'Up to 100 members', capacity: 100, price: 449 },
      { key: 'plus_100', label: 'Up to 200 members', capacity: 200, price: 599 },
    ],
  },
  {
    key: 'enterprise', track: 'cooperative', name: 'Enterprise', price: 'Custom',
    cadence: 'Annual agreement',
    description: 'A governed rollout for unions, lenders, NGOs, and multi-cooperative programmes.',
    features: ['Unlimited members', 'Multi-cooperative administration', 'Custom USSD and API access', 'Migration and implementation support', 'Dedicated account manager', 'Contracted SLA'],
    cta: 'Talk to enterprise sales', bands: null,
  },
  {
    key: 'solo', track: 'farmer', name: 'Solo Farm', price: 'GHS 99',
    cadence: 'per farm / month',
    description: 'Manage farm workers, track tasks and attendance, run payroll.',
    features: ['Worker management', 'Task management', 'Attendance tracking', 'Wage payroll', '200 SMS messages per month', 'Worker USSD access'],
    cta: 'Start Solo Farm onboarding',
    bands: [
      { key: 'w20', label: 'Up to 20 workers', capacity: 20, price: 99 },
      { key: 'w50', label: 'Up to 50 workers', capacity: 50, price: 199 },
      { key: 'w100', label: 'Up to 100 workers', capacity: 100, price: 349 },
      { key: 'custom', label: 'Custom worker count', capacity: null, price: null },
    ],
  },
]

export async function fetchPlans() {
  try {
    const res = await apiFetch(`${API_URL}/plans`)
    if (!res.ok) throw new Error('plans fetch failed')
    const data = await res.json()
    return data.plans
  } catch (err) {
    if (isTransportFailure(err)) return PLANS_FALLBACK
    throw err
  }
}

export async function createPreCheckout(payload) {
  const res = await apiFetch(`${API_URL}/subscriptions/pre-checkout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Failed to create checkout')
  }
  return res.json()
}
