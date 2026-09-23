import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import OrganizationPanel from './OrganizationPanel'
import OrganizationSwitcher from './OrganizationSwitcher'
import * as orgApi from '../../api/organizations'

vi.mock('../../api/organizations', () => ({
  createOrganization: vi.fn(),
  createOrganizationCooperative: vi.fn(),
  fetchMyOrganization: vi.fn(),
  fetchOrganizationBilling: vi.fn(),
  switchOrganizationCooperative: vi.fn(),
  updateOrganization: vi.fn(),
}))

vi.mock('../../api/auth', () => ({
  getAuthUser: vi.fn(() => null),
  storeAuthUser: vi.fn(),
}))

const billing = {
  organization: { id: 5, name: 'Ashanti Union', subscription_plan: 'enterprise', subscription_status: 'active', subscription_live: true, subscription_expires_at: '2027-09-01T00:00:00' },
  cooperatives: [
    { id: 1, name: 'HQ Coop', location: 'Kumasi', is_active_scope: true, subscription_plan: 'starter', subscription_status: 'active', effective_plan_key: 'enterprise', effective_plan_name: 'Enterprise', inherits_organization_plan: true, members: { used: 12, limit: null, unlimited: true, included: true }, workers: { used: 0, included: false }, sms: { used: 40, limit: 999999, unlimited: false, included: true } },
    { id: 2, name: 'Branch North', location: 'Tamale', is_active_scope: false, subscription_plan: 'starter', subscription_status: 'active', effective_plan_key: 'enterprise', effective_plan_name: 'Enterprise', inherits_organization_plan: true, members: { used: 3, limit: null, unlimited: true, included: true }, workers: { used: 0, included: false }, sms: { used: 0, limit: 999999, unlimited: false, included: true } },
  ],
  totals: { cooperatives: 2, members: 15, workers: 0, sms_this_month: 40, paid: 299, currency: 'GHS' },
  history: [],
}

describe('OrganizationPanel', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(cleanup)

  it('offers to create an organization when the admin has none', async () => {
    orgApi.createOrganization.mockResolvedValue({ id: 9, name: 'New Union' })
    const reload = vi.fn()
    render(<OrganizationPanel cooperative={{ id: 1, name: 'HQ Coop' }} cooperativeId={1} user={{ role: 'admin', cooperative_id: 1 }} reloadPage={reload} />)

    expect(screen.getByText(/HQ Coop becomes the first member/)).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Organization name'), { target: { value: 'New Union' } })
    fireEvent.change(screen.getByLabelText('Billing email (optional)'), { target: { value: 'bill@union.org' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create organization' }))
    await waitFor(() => expect(orgApi.createOrganization).toHaveBeenCalledWith({ name: 'New Union', billing_email: 'bill@union.org' }))
    await waitFor(() => expect(reload).toHaveBeenCalled())
  })

  it('renders consolidated billing with inherited plans and lets the admin switch', async () => {
    orgApi.fetchOrganizationBilling.mockResolvedValue(billing)
    orgApi.switchOrganizationCooperative.mockResolvedValue({ access_token: 't' })
    const reload = vi.fn()
    render(<OrganizationPanel cooperative={{ id: 1 }} cooperativeId={1} user={{ role: 'admin', cooperative_id: 1, organization_id: 5 }} reloadPage={reload} />)

    expect(await screen.findByText('Ashanti Union')).toBeTruthy()
    expect(screen.getByText('GHS 299')).toBeTruthy()
    const table = screen.getByRole('table', { name: 'Organization cooperatives' })
    const rows = within(table).getAllByRole('row').slice(1)
    expect(rows).toHaveLength(2)
    expect(within(rows[0]).getByText('ACTIVE')).toBeTruthy()
    expect(within(rows[0]).getByText('12 / ∞')).toBeTruthy()
    expect(within(rows[0]).getAllByText('inherited')).toHaveLength(1)
    expect(within(rows[0]).queryByRole('button', { name: 'Switch' })).toBeNull()

    fireEvent.click(within(rows[1]).getByRole('button', { name: 'Switch' }))
    await waitFor(() => expect(orgApi.switchOrganizationCooperative).toHaveBeenCalledWith(5, 2))
    await waitFor(() => expect(reload).toHaveBeenCalled())
  })

  it('adds a cooperative to the organization', async () => {
    orgApi.fetchOrganizationBilling.mockResolvedValue({ ...billing, organization: { ...billing.organization, subscription_status: 'pending', subscription_live: false } })
    orgApi.createOrganizationCooperative.mockResolvedValue({ id: 3, name: 'Branch East' })
    render(<OrganizationPanel cooperative={{ id: 1 }} cooperativeId={1} user={{ role: 'admin', cooperative_id: 1, organization_id: 5 }} />)

    expect(await screen.findByText(/The Enterprise agreement is pending/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Add cooperative' }))
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Branch East' } })
    fireEvent.change(screen.getByLabelText('Location'), { target: { value: 'Ho' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add cooperative' }))
    await waitFor(() => expect(orgApi.createOrganizationCooperative).toHaveBeenCalledWith(5, { name: 'Branch East', location: 'Ho', organization_type: 'cooperative' }))
    expect(await screen.findByText('Branch East added to the organization.')).toBeTruthy()
    expect(orgApi.fetchOrganizationBilling).toHaveBeenCalledTimes(2)
  })

  it('renders nothing for non-admin roles', () => {
    const { container } = render(<OrganizationPanel cooperative={{ id: 1 }} cooperativeId={1} user={{ role: 'finance_officer' }} />)
    expect(container.innerHTML).toBe('')
  })
})

describe('OrganizationSwitcher', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(cleanup)

  it('renders nothing without an organization or with a single cooperative', async () => {
    const { container } = render(<OrganizationSwitcher user={{ organization_id: null }} activeCooperativeId={1} />)
    expect(container.innerHTML).toBe('')
    expect(orgApi.fetchMyOrganization).not.toHaveBeenCalled()

    orgApi.fetchMyOrganization.mockResolvedValue({ id: 5, name: 'Union', cooperatives: [{ id: 1, name: 'Only', is_active_scope: true }] })
    const single = render(<OrganizationSwitcher user={{ organization_id: 5 }} activeCooperativeId={1} />)
    await waitFor(() => expect(orgApi.fetchMyOrganization).toHaveBeenCalled())
    expect(single.container.innerHTML).toBe('')
  })

  it('switches scope and notifies the caller', async () => {
    orgApi.fetchMyOrganization.mockResolvedValue({ id: 5, name: 'Union', cooperatives: [{ id: 1, name: 'HQ', is_active_scope: true }, { id: 2, name: 'North', is_active_scope: false }] })
    orgApi.switchOrganizationCooperative.mockResolvedValue({ access_token: 't' })
    const onSwitched = vi.fn()
    render(<OrganizationSwitcher user={{ organization_id: 5 }} activeCooperativeId={1} onSwitched={onSwitched} />)
    const select = await screen.findByLabelText('Switch cooperative')
    expect(select.value).toBe('1')
    fireEvent.change(select, { target: { value: '2' } })
    await waitFor(() => expect(orgApi.switchOrganizationCooperative).toHaveBeenCalledWith(5, 2))
    await waitFor(() => expect(onSwitched).toHaveBeenCalledWith(2))
  })
})
