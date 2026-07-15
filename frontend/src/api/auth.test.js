import { describe, expect, it } from 'vitest'
import { isAuthTokenUsable, TOKEN_KEY } from './auth'

function tokenWithExpiry(exp) {
  const payload = globalThis.btoa(JSON.stringify({ sub: 'admin@example.com', exp }))
  return `header.${payload}.signature`
}

describe('auth api', () => {
  it('exports stable token storage key', () => {
    expect(TOKEN_KEY).toBe('agro_os_token')
  })

  it('accepts only unexpired backend token shapes', () => {
    expect(isAuthTokenUsable(tokenWithExpiry(Date.now() / 1000 + 60))).toBe(true)
    expect(isAuthTokenUsable(tokenWithExpiry(Date.now() / 1000 - 60))).toBe(false)
    expect(isAuthTokenUsable('not-a-token')).toBe(false)
  })
})
