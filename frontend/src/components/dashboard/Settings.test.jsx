import React from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Settings from './Settings'
import * as adminApi from '../../api/admin'
import * as farmersApi from '../../api/farmers'

vi.mock('../../api/admin', () => ({
  previewDemoReset: vi.fn(),
  confirmDemoReset: vi.fn(),
}))

vi.mock('../../api/cooperatives', () => ({
  createSubscriptionCheckout: vi.fn(),
  updateCooperative: vi.fn(),
}))

vi.mock('../../api/farmers', () => ({
  fetchFarmers: vi.fn(),
}))

const cooperative = {
  id: 1,
  name: 'AgroOS Demo Cooperative',
  location: 'Accra',
  currency: 'GHS',
  moolre_account_number: '1089700',
}

const preview = {
  dry_run: true,
  memberships: 3,
  transactions: 7,
  loans: 2,
  productions: 1,
  confirmation_phrase: 'RESET DEMO',
  confirmation_token: 'short-lived-token',
  expires_in_seconds: 300,
}

describe('Settings demo reset', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('does not request a preview until opened and shows retention guidance when unavailable', async () => {
    const unavailable = new Error('Not found')
    unavailable.status = 404
    adminApi.previewDemoReset.mockRejectedValue(unavailable)

    render(<Settings cooperative={cooperative} loading={false} />)
    expect(adminApi.previewDemoReset).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Review demo reset' }))

    expect(await screen.findByText(/approved archive or retention process/i)).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Review demo reset' })).toBeNull()
  })

  it('requires the exact phrase, resets, and refreshes dashboard data', async () => {
    const onRefresh = vi.fn().mockResolvedValue()
    adminApi.previewDemoReset.mockResolvedValue(preview)
    adminApi.confirmDemoReset.mockResolvedValue({ reset: true })

    render(<Settings cooperative={cooperative} loading={false} onRefresh={onRefresh} />)
    fireEvent.click(screen.getByRole('button', { name: 'Review demo reset' }))

    const dialog = await screen.findByRole('dialog', { name: 'Confirm demo data reset' })
    expect(dialog.getAttribute('aria-modal')).toBe('true')
    expect(screen.getByText('7')).toBeTruthy()

    const confirmButton = screen.getByRole('button', { name: 'Reset demo data' })
    expect(confirmButton.disabled).toBe(true)
    fireEvent.change(screen.getByLabelText(/Type RESET DEMO to confirm/), { target: { value: 'RESET DEMO' } })
    expect(confirmButton.disabled).toBe(false)
    fireEvent.click(confirmButton)

    await waitFor(() => {
      expect(adminApi.confirmDemoReset).toHaveBeenCalledWith('short-lived-token', 'RESET DEMO')
      expect(onRefresh).toHaveBeenCalled()
    })
    expect(await screen.findByText('Demo data was reset successfully.')).toBeTruthy()
  })
})

describe('Settings subscription usage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads all member pages for the Growth usage meter', async () => {
    farmersApi.fetchFarmers
      .mockResolvedValueOnce(Array.from({ length: 100 }, (_, id) => ({ id })))
      .mockResolvedValueOnce(Array.from({ length: 5 }, (_, id) => ({ id: id + 100 })))

    render(
      <Settings
        cooperative={{
          ...cooperative,
          subscription_plan: 'growth',
          subscription_status: 'active',
        }}
        cooperativeId={1}
        loading={false}
      />,
    )

    expect(await screen.findByText('Active members: 105 of 500')).toBeTruthy()
    expect(farmersApi.fetchFarmers).toHaveBeenNthCalledWith(1, 1, null, 0, 100)
    expect(farmersApi.fetchFarmers).toHaveBeenNthCalledWith(2, 1, null, 100, 100)
  })
})
