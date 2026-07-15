import { afterEach, describe, expect, it, vi } from 'vitest'
import { cancelLoan, fetchLoans } from './loans'
import { fetchProductions } from './production'
import { fetchTransactions } from './transactions'

describe('dashboard resource failures', () => {
  afterEach(() => {
    vi.useRealTimers()
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

  it('times out loan cancellation with a friendly transport error', async () => {
    vi.useFakeTimers()
    vi.stubGlobal('fetch', vi.fn((_url, options) => new Promise((_resolve, reject) => {
      options.signal.addEventListener('abort', () => reject(new window.DOMException('Aborted', 'AbortError')))
    })))

    const cancellation = expect(cancelLoan(12, 'Duplicate request')).rejects.toThrow(
      'The server is still starting up or the connection timed out',
    )
    await vi.advanceTimersByTimeAsync(120000)

    await cancellation
  })
})
