import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import GovernanceSettings from './GovernanceSettings'
import {
  fetchCooperativeUsers,
  fetchIntegrationHealth,
  updateCooperativeUser,
} from '../../api/governance'

vi.mock('../../api/governance', () => ({
  fetchCooperativeUsers: vi.fn(),
  fetchIntegrationHealth: vi.fn(),
  registerCooperativeUser: vi.fn(),
  updateCooperativeUser: vi.fn(),
}))

describe('GovernanceSettings', () => {
  beforeEach(() => {
    fetchCooperativeUsers.mockResolvedValue([
      { id: 7, email: 'finance@example.com', role: 'finance_officer', is_active: true },
    ])
    fetchIntegrationHealth.mockResolvedValue({
      environment: 'sandbox',
      moolre: { api_credentials_configured: true, platform_wallet_configured: false },
      policy: {},
    })
    updateCooperativeUser.mockResolvedValue({})
  })
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('lets an administrator deactivate a cooperative user', async () => {
    render(<GovernanceSettings />)
    const deactivate = await screen.findByRole('button', { name: 'Deactivate finance@example.com' })

    fireEvent.click(deactivate)

    await waitFor(() => expect(updateCooperativeUser).toHaveBeenCalledWith(7, { is_active: false }))
  })

  it('offers every API role in the invite picker, grouped by track (#244)', async () => {
    render(<GovernanceSettings />)
    const picker = await screen.findByLabelText('New user role')
    const values = Array.from(picker.querySelectorAll('option')).map((option) => option.value)
    expect(values).toEqual([
      'admin', 'finance_officer', 'field_officer', 'operations_officer', 'sales_officer',
      'farm_owner', 'farm_manager', 'supervisor',
    ])
    expect(picker.value).toBe('finance_officer')
    expect(Array.from(picker.querySelectorAll('optgroup')).map((group) => group.label)).toEqual(['Cooperative roles', 'Solo farm roles'])

    fireEvent.change(picker, { target: { value: 'sales_officer' } })
    expect(screen.getByText('Buyers and buyer sales')).toBeTruthy()
  })

  it('hides team controls from non-administrators', async () => {
    fetchCooperativeUsers.mockRejectedValue(Object.assign(new Error('Forbidden'), { status: 403 }))
    fetchIntegrationHealth.mockRejectedValue(Object.assign(new Error('Forbidden'), { status: 403 }))

    render(<GovernanceSettings />)

    expect(await screen.findByText('Only cooperative administrators can manage team access.')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Deactivate/ })).toBeNull()
  })

  it('clears a stale restricted state after a non-403 failure', async () => {
    fetchCooperativeUsers.mockRejectedValue(Object.assign(new Error('Forbidden'), { status: 403 }))
    render(<GovernanceSettings />)
    expect(await screen.findByText('Only cooperative administrators can manage team access.')).toBeTruthy()

    fetchCooperativeUsers.mockRejectedValue(Object.assign(new Error('Service unavailable'), { status: 503 }))
    fireEvent.click(screen.getByRole('button', { name: 'Refresh' }))

    expect(await screen.findByRole('alert')).toBeTruthy()
    expect(screen.queryByText('Only cooperative administrators can manage team access.')).toBeNull()
  })
})
