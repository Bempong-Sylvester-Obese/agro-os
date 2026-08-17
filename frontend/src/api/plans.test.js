import { describe, expect, it, vi, beforeEach } from 'vitest'

vi.mock('./config', () => ({
  API_URL: 'https://api.test',
  apiFetch: vi.fn(),
  authHeaders: vi.fn(() => ({})),
  isTransportFailure: (err) => err instanceof TypeError,
}))

import { createPreCheckout, fetchPlans } from './plans'
import { apiFetch } from './config'

describe('plans api', () => {
  beforeEach(() => vi.clearAllMocks())

  it('fetchPlans returns the plan list', async () => {
    apiFetch.mockResolvedValue({ ok: true, json: async () => ({ plans: [{ key: 'starter' }] }) })
    const plans = await fetchPlans()
    expect(plans).toEqual([{ key: 'starter' }])
  })

  it('fetchPlans falls back on transport failure', async () => {
    apiFetch.mockRejectedValue(new TypeError('network down'))
    const plans = await fetchPlans()
    expect(plans.some((p) => p.key === 'growth')).toBe(true)
  })

  it('createPreCheckout posts the payload', async () => {
    apiFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ checkout_id: 1, reference: 'sub_pre_x', authorization_url: 'https://pay', amount: 299 }),
    })
    const result = await createPreCheckout({ plan_key: 'growth', band: 'base', organisation: 'Coop' })
    expect(result.authorization_url).toBe('https://pay')
  })
})
