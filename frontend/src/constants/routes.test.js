import { describe, expect, it } from 'vitest'
import { pageKeyFromPath } from './routes'

describe('pageKeyFromPath', () => {
  it('maps the marketing home and hyphenated demo path to distinct keys', () => {
    expect(pageKeyFromPath('/')).toBe('home')
    expect(pageKeyFromPath('/book-demo')).toBe('bookDemo')
  })

  it('maps other marketing segments, app shells, and unknown paths', () => {
    expect(pageKeyFromPath('/solutions')).toBe('solutions')
    expect(pageKeyFromPath('/features')).toBe('features')
    expect(pageKeyFromPath('/pricing')).toBe('pricing')
    expect(pageKeyFromPath('/compliance')).toBe('compliance')
    expect(pageKeyFromPath('/investors')).toBe('investors')
    expect(pageKeyFromPath('/dashboard')).toBe('dashboard')
    expect(pageKeyFromPath('/dashboard/intake')).toBe('dashboard')
    expect(pageKeyFromPath('/login')).toBe('login')
    expect(pageKeyFromPath('/subscribe/starter')).toBe('subscription')
    expect(pageKeyFromPath('/not-a-page')).toBe('home')
  })
})
