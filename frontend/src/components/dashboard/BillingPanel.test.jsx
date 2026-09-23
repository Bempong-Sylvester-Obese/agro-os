import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import BillingPanel from './BillingPanel'
import * as cooperativesApi from '../../api/cooperatives'
import * as plansApi from '../../api/plans'

vi.mock('../../api/cooperatives', () => ({
  cancelSubscription: vi.fn(),
  createSubscriptionCheckout: vi.fn(),
  fetchCooperativeUsage: vi.fn(),
  fetchSubscriptionHistory: vi.fn(),
  fetchSubscriptionStatus: vi.fn(),
  renewSubscription: vi.fn(),
  resumeSubscription: vi.fn(),
  updateCooperative: vi.fn(),
}))

vi.mock('../../api/plans', () => ({
  fetchPlans: vi.fn(),
}))

const PLANS = [
  { key: 'starter', track: 'cooperative', name: 'Starter', price: 0, display_price: 'Free', currency: 'GHS', cadence: 'No card required', bands: null, features: ['Up to 10 members'] },
  {
    key: 'growth', track: 'cooperative', name: 'Growth', price: 299, display_price: 'GHS 299', currency: 'GHS', cadence: 'per organisation / month', featured: true,
    bands: [
      { key: 'base', label: 'Up to 50 members', capacity: 50, price: 299 },
      { key: 'plus_50', label: 'Up to 100 members', capacity: 100, price: 449 },
      { key: 'plus_100', label: 'Up to 200 members', capacity: 200, price: 599 },
    ],
    features: ['AgroCredit Trust Scores', 'USSD access'],
  },
  { key: 'enterprise', track: 'cooperative', name: 'Enterprise', price: 0, display_price: 'Custom', currency: 'GHS', cadence: 'Annual agreement', cta: 'Talk to enterprise sales', bands: null, features: [] },
  { key: 'solo', track: 'farmer', name: 'Solo Farm', price: 99, display_price: 'GHS 99', currency: 'GHS', bands: [{ key: 'w20', label: 'Up to 20 workers', capacity: 20, price: 99 }], features: [] },
]

const usage = {
  effective_plan_key: 'growth',
  effective_plan_name: 'Growth',
  limits: {
    members: { used: 12, limit: 50, unlimited: false, percent: 24, remaining: 38, included: true },
    workers: { used: 0, limit: 0, unlimited: false, percent: null, remaining: 0, included: false },
    sms: { used: 10, limit: 1000, unlimited: false, percent: 1, remaining: 990, included: true },
  },
  features: { loans: true },
  feature_labels: { loans: 'AgroCredit loans' },
}

const history = {
  cooperative_id: 1,
  currency: 'GHS',
  total_paid: 598,
  items: [
    { id: 2, reference: 'sub_upg_1_abc', kind: 'upgrade', plan_key: 'growth', plan_name: 'Growth', band: 'base', band_label: 'Up to 50 members', amount: 299, currency: 'GHS', status: 'consumed', outcome: 'paid', provider_transaction_id: 'TX-2', created_at: '2026-09-01T10:00:00', paid_at: '2026-09-01T10:05:00' },
    { id: 3, reference: 'sub_upg_1_def', kind: 'upgrade', plan_key: 'growth', plan_name: 'Growth', band: 'plus_50', band_label: 'Up to 100 members', amount: 449, currency: 'GHS', status: 'pending', outcome: 'pending', provider_transaction_id: null, created_at: '2026-09-20T10:00:00', paid_at: null },
    { id: 1, reference: 'sub_pre_xyz', kind: 'pre_checkout', plan_key: 'growth', plan_name: 'Growth', band: 'base', band_label: 'Up to 50 members', amount: 299, currency: 'GHS', status: 'consumed', outcome: 'paid', provider_transaction_id: 'TX-1', created_at: '2026-08-01T10:00:00', paid_at: '2026-08-01T10:05:00' },
  ],
}

function setup({ status, coop = {} } = {}) {
  plansApi.fetchPlans.mockResolvedValue(PLANS)
  cooperativesApi.fetchSubscriptionStatus.mockResolvedValue(status)
  cooperativesApi.fetchCooperativeUsage.mockResolvedValue(usage)
  cooperativesApi.fetchSubscriptionHistory.mockResolvedValue(history)
  return render(
    <BillingPanel
      cooperative={{ id: 1, subscription_plan: status.plan_key, subscription_status: status.status, organization_type: 'cooperative', ...coop }}
      cooperativeId={1}
    />,
  )
}

const activeGrowth = { plan_key: 'growth', band: 'base', status: 'active', effective_plan_key: 'growth', expires_at: '2026-10-15T00:00:00', days_remaining: 23, in_grace: false, paid_access: true }

describe('BillingPanel', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(cleanup)

  it('shows plan, status, price and payment history from the API', async () => {
    setup({ status: activeGrowth })
    expect(await screen.findByText('Growth', { selector: 'div' })).toBeTruthy()
    expect(screen.getByText('Up to 50 members', { selector: 'div' })).toBeTruthy()
    expect(screen.getByText('active')).toBeTruthy()
    expect(screen.getByText('Price').nextElementSibling.textContent).toBe('GHS 299 / month')
    expect(screen.getByText('Active members: 12 of 50')).toBeTruthy()

    const table = await screen.findByRole('table')
    const rows = within(table).getAllByRole('row').slice(1)
    expect(rows).toHaveLength(3)
    expect(within(rows[0]).getByText('Upgrade / renewal')).toBeTruthy()
    expect(within(rows[1]).getByText('Pending')).toBeTruthy()
    expect(within(rows[2]).getByText('Signup')).toBeTruthy()
    expect(screen.getByText('Total paid: GHS 598')).toBeTruthy()
  })

  it('plan picker is catalogue-driven and band-aware; same plan+band cannot be re-bought', async () => {
    setup({ status: activeGrowth })
    const planSelect = await screen.findByLabelText('Plan')
    const options = within(planSelect).getAllByRole('option').map((o) => o.textContent)
    expect(options).toEqual(['Growth — GHS 299 per organisation / month'])
    expect(options.join()).not.toMatch(/Solo|Starter|Enterprise/) // other track / not purchasable

    const bandSelect = await screen.findByLabelText('Size')
    await waitFor(() => expect(bandSelect.value).toBe('base'))
    expect((await screen.findByRole('button', { name: 'Current plan' })).disabled).toBe(true)

    fireEvent.change(bandSelect, { target: { value: 'plus_50' } })
    const pay = await screen.findByRole('button', { name: 'Pay GHS 449' })
    expect(pay.disabled).toBe(false)

    cooperativesApi.createSubscriptionCheckout.mockResolvedValue({ authorization_url: '' })
    fireEvent.click(pay)
    await waitFor(() => expect(cooperativesApi.createSubscriptionCheckout).toHaveBeenCalledWith(1, 'growth', 'plus_50'))
    expect(screen.getByText(/Talk to enterprise sales/)).toBeTruthy()
  })

  it('renew and cancel flows call the lifecycle endpoints', async () => {
    setup({ status: activeGrowth })
    cooperativesApi.renewSubscription.mockResolvedValue({ authorization_url: '' })
    fireEvent.click(await screen.findByRole('button', { name: 'Renew Growth' }))
    await waitFor(() => expect(cooperativesApi.renewSubscription).toHaveBeenCalledWith(1))

    fireEvent.click(screen.getByRole('button', { name: 'Cancel subscription' }))
    expect(screen.getByRole('dialog', { name: 'Confirm cancellation' })).toBeTruthy()
    cooperativesApi.cancelSubscription.mockResolvedValue({ ...activeGrowth, status: 'cancelled' })
    fireEvent.click(screen.getByRole('button', { name: 'Cancel at period end' }))
    await waitFor(() => expect(cooperativesApi.cancelSubscription).toHaveBeenCalledWith(1, { immediately: false }))
    expect(await screen.findByText(/Cancellation scheduled for the end/)).toBeTruthy()
  })

  it('cancelled plan offers resume and explains access-until', async () => {
    setup({ status: { ...activeGrowth, status: 'cancelled' } })
    expect(await screen.findByText(/Cancellation scheduled\. Paid features remain until/)).toBeTruthy()
    cooperativesApi.resumeSubscription.mockResolvedValue({ ...activeGrowth })
    fireEvent.click(screen.getByRole('button', { name: 'Resume subscription' }))
    await waitFor(() => expect(cooperativesApi.resumeSubscription).toHaveBeenCalledWith(1))
    expect(screen.queryByRole('button', { name: 'Cancel subscription' })).toBeNull()
  })

  it('trial shows days left and a plan picker but no renew/cancel', async () => {
    setup({ status: { plan_key: 'starter', band: null, status: 'trial', effective_plan_key: 'growth', expires_at: '2026-10-01T00:00:00', days_remaining: 9, paid_access: true } })
    expect(await screen.findByText(/Growth trial · 9 days left/)).toBeTruthy()
    expect(screen.getByText('Trial Access')).toBeTruthy()
    expect(screen.getByText('Choose a plan')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Renew/ })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Cancel subscription' })).toBeNull()
    expect((await screen.findByRole('button', { name: 'Pay GHS 299' })).disabled).toBe(false)
  })

  it('downgrade to the free plan uses the cooperative update endpoint', async () => {
    setup({ status: activeGrowth })
    cooperativesApi.updateCooperative.mockResolvedValue({})
    fireEvent.click(await screen.findByRole('button', { name: 'Downgrade to Starter' }))
    await waitFor(() => expect(cooperativesApi.updateCooperative).toHaveBeenCalledWith(1, { subscription_plan: 'starter' }))
    expect(await screen.findByText('Plan changed to Starter.')).toBeTruthy()
  })

  it('falls back to the cooperative record when status fails to load', async () => {
    plansApi.fetchPlans.mockResolvedValue(PLANS)
    cooperativesApi.fetchSubscriptionStatus.mockRejectedValue(new Error('down'))
    cooperativesApi.fetchCooperativeUsage.mockRejectedValue(new Error('down'))
    cooperativesApi.fetchSubscriptionHistory.mockRejectedValue(new Error('down'))
    render(<BillingPanel cooperative={{ id: 1, subscription_plan: 'growth', subscription_status: 'active' }} cooperativeId={1} />)
    expect(await screen.findByText(/Billing status could not be loaded/)).toBeTruthy()
    expect(screen.getByText('Growth', { selector: 'div' })).toBeTruthy()
    expect(screen.getByText(/Payment history is unavailable/)).toBeTruthy()
  })
})
