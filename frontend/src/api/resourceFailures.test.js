import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchLoans } from './loans'
import { fetchProductions } from './production'
import { fetchTransactions } from './transactions'

describe('dashboard resource failures', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it.each([
    ['transactions', fetchTransactions],
    ['loans', fetchLoans],
    ['production', fetchProductions],
  ])('does not turn a %s transport failure into an empty dataset', async (_name, fetchResource) => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))

    await expect(fetchResource(1)).rejects.toThrow()
  })
})
