import React from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Settings from './Settings'
import * as adminApi from '../../api/admin'
import * as cooperativesApi from '../../api/cooperatives'

vi.mock('../../api/admin', () => ({
  previewDemoReset: vi.fn(),
  confirmDemoReset: vi.fn(),
}))

vi.mock('../../api/cooperatives', () => ({
  createSubscriptionCheckout: vi.fn(),
  fetchCooperativeUsage: vi.fn(),
  updateCooperative: vi.fn(),
}))

const cooperative = {
  id: 1,
  name: 'AgroOS Demo Cooperative',
  location: 'Accra',
  currency: 'GHS',
  wallet_account_id: '1089700',
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

  const usage = {
    cooperative_id: 1,
    plan_key: 'growth',
    effective_plan_key: 'growth',
    effective_plan_name: 'Growth',
    band: 'plus_50',
    status: 'active',
    days_remaining: 20,
    limits: {
      members: { used: 62, limit: 100, unlimited: false, percent: 62, remaining: 38, included: true },
      workers: { used: 0, limit: 0, unlimited: false, percent: null, remaining: 0, included: false },
      sms: { used: 250, limit: 1000, unlimited: false, percent: 25, remaining: 750, included: true, period: 'month' },
    },
    features: { loans: true, scores: true, ussd: true, commerce: true, sms: true, workers: false, payroll: false },
    feature_labels: { loans: 'AgroCredit loans', scores: 'Trust scores', ussd: 'Member USSD', commerce: 'Commerce', sms: 'Bulk SMS', workers: 'Worker management', payroll: 'Wage payroll' },
  }

  it('renders band-aware usage meters from the usage endpoint', async () => {
    cooperativesApi.fetchCooperativeUsage.mockResolvedValue(usage)

    render(
      <Settings
        cooperative={{ ...cooperative, subscription_plan: 'growth', subscription_status: 'active' }}
        cooperativeId={1}
        loading={false}
      />,
    )

    expect(await screen.findByText('Active members: 62 of 100')).toBeTruthy()
    expect(screen.getByText('SMS sent this month: 250 of 1,000')).toBeTruthy()
    expect(screen.queryByText(/Active workers/)).toBeNull() // not included on Growth
    expect(screen.getByText('AgroCredit loans')).toBeTruthy()
    expect(screen.getByText('Wage payroll').style.textDecoration).toBe('line-through')
    expect(cooperativesApi.fetchCooperativeUsage).toHaveBeenCalledWith(1)
  })

  it('shows the effective plan when it differs from the plan on record', async () => {
    cooperativesApi.fetchCooperativeUsage.mockResolvedValue({
      ...usage,
      plan_key: 'starter',
      status: 'trial',
      days_remaining: 9,
      limits: { ...usage.limits, members: { ...usage.limits.members, used: 3, limit: 50, percent: 6, remaining: 47 } },
    })

    render(
      <Settings
        cooperative={{ ...cooperative, subscription_plan: 'starter', subscription_status: 'trial' }}
        cooperativeId={1}
        loading={false}
      />,
    )

    const trialLabel = await screen.findByText('Trial Access')
    expect(trialLabel.nextElementSibling.textContent).toBe('Growth · 9 days left')
    expect(screen.getByText('Active members: 3 of 50')).toBeTruthy()
  })

  it('degrades gracefully when usage cannot be loaded', async () => {
    cooperativesApi.fetchCooperativeUsage.mockRejectedValue(new Error('boom'))

    render(<Settings cooperative={{ ...cooperative, subscription_plan: 'starter' }} cooperativeId={1} loading={false} />)

    expect(await screen.findByText(/Usage is unavailable right now/)).toBeTruthy()
  })
})
