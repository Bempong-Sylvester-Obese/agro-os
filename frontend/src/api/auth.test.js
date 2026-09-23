import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchCurrentUser, isAuthTokenUsable, signup, TOKEN_KEY, userFromAuthToken, userFromLoginResponse, userFromMeResponse } from './auth'

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

  it('hydrates the session user from JWT claims without inventing display strings (#251)', () => {
    const payload = globalThis.btoa(JSON.stringify({
      sub: 'ama@union.org', user_id: 7, role: 'finance_officer', cooperative_id: 3, organization_id: 9,
      organization_type: 'cooperative', exp: Date.now() / 1000 + 60,
    }))
    const user = userFromAuthToken(`h.${payload}.s`)
    expect(user).toEqual({
      id: 7,
      email: 'ama@union.org',
      role: 'finance_officer',
      cooperative_id: 3,
      organization_id: 9,
      cooperative: null,
      organization_type: 'cooperative',
    })
    expect(JSON.stringify(user)).not.toMatch(/Kuapa|Demo|Cooperative Admin/)
    expect(userFromAuthToken(null)).toBeNull()
    expect(userFromAuthToken('garbage')).toBeNull()
  })

  it('prefers API user fields over claims and uses the real cooperative name on login', () => {
    const payload = globalThis.btoa(JSON.stringify({ sub: 'ama@union.org', role: 'admin', cooperative_id: 3 }))
    const user = userFromLoginResponse({
      access_token: `h.${payload}.s`,
      user: { id: 7, email: 'ama@union.org', role: 'finance_officer', cooperative_id: 3, organization_id: null },
      cooperative_name: 'Ashanti Growers',
      organization_type: 'cooperative',
    })
    expect(user.role).toBe('finance_officer')
    expect(user.cooperative).toBe('Ashanti Growers')
    expect(user.id).toBe(7)

    const bare = userFromLoginResponse({ access_token: `h.${payload}.s` }, 'ama@union.org')
    expect(bare.cooperative).toBeNull()
    expect(bare.role).toBe('admin')
  })

  it('maps /auth/me into the session user shape', async () => {
    localStorage.setItem(TOKEN_KEY, 'tok')
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        id: 7, email: 'ama@union.org', role: 'admin', is_active: true, onboarding_role: null,
        cooperative_id: 3, organization_id: null, cooperative_name: 'Ashanti Growers',
        organization_type: 'cooperative', password_change_required: false,
      }),
    })
    const me = await fetchCurrentUser()
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/auth\/me$/)
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer tok')
    expect(userFromMeResponse(me)).toMatchObject({ id: 7, cooperative: 'Ashanti Growers', role: 'admin', cooperative_id: 3 })
    expect(userFromMeResponse(null)).toBeNull()
    localStorage.removeItem(TOKEN_KEY)
  })

  it('does not retry a signup after a transport failure', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockRejectedValue(
      new TypeError('connection lost'),
    )

    await expect(signup({
      email: 'admin@example.com',
      password: 'secret123',
      cooperativeName: 'Test Cooperative',
    })).rejects.toThrow('Could not reach the AgroOS API')

    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})
