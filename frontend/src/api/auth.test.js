import { afterEach, describe, expect, it, vi } from 'vitest'
import { isAuthTokenUsable, signup, TOKEN_KEY } from './auth'

function tokenWithExpiry(exp) {
  const payload = globalThis.btoa(JSON.stringify({ sub: 'admin@example.com', exp }))
  return `header.${payload}.signature`
}

describe('auth api', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('exports stable token storage key', () => {
    expect(TOKEN_KEY).toBe('agro_os_token')
  })

  it('accepts only unexpired backend token shapes', () => {
    expect(isAuthTokenUsable(tokenWithExpiry(Date.now() / 1000 + 60))).toBe(true)
    expect(isAuthTokenUsable(tokenWithExpiry(Date.now() / 1000 - 60))).toBe(false)
    expect(isAuthTokenUsable('not-a-token')).toBe(false)
  })

  it('sends the subscription plan and onboarding role in the signup request', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ access_token: 'token', cooperative_name: 'Test Cooperative' }),
    })

    await signup({
      email: 'admin@example.com',
      password: 'secret123',
      cooperativeName: 'Test Cooperative',
      location: 'Accra',
      memberCount: 25,
      subscriptionPlan: 'growth',
      onboardingRole: 'Finance or operations lead',
    })

    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toMatchObject({
      subscription_plan: 'growth',
      onboarding_role: 'Finance or operations lead',
    })
  })
})
