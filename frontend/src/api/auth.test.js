import { describe, expect, it } from 'vitest'
import { TOKEN_KEY } from './auth'

describe('auth api', () => {
  it('exports stable token storage key', () => {
    expect(TOKEN_KEY).toBe('agro_os_token')
  })
})
