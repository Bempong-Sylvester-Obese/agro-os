import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import GovernanceSettings from './GovernanceSettings'
import {
  fetchCooperativeUsers,
  fetchIntegrationHealth,
  inviteCooperativeUser,
  updateCooperativeUser,
} from '../../api/governance'
import { getOrganizationType } from '../../utils/auth'

vi.mock('../../api/governance', () => ({
  fetchCooperativeUsers: vi.fn(),
  fetchIntegrationHealth: vi.fn(),
  inviteCooperativeUser: vi.fn(),
  registerCooperativeUser: vi.fn(),
  updateCooperativeUser: vi.fn(),
}))
vi.mock('../../utils/auth', () => ({
  getOrganizationType: vi.fn(() => 'cooperative'),
}))

describe('GovernanceSettings', () => {
  beforeEach(() => {
    getOrganizationType.mockReturnValue('cooperative')
    fetchCooperativeUsers.mockResolvedValue([
      { id: 7, email: 'finance@example.com', role: 'finance_officer', is_active: true },
    ])
    fetchIntegrationHealth.mockResolvedValue({
      environment: 'sandbox',
      moolre: { api_credentials_configured: true, platform_wallet_configured: false },
      policy: {},
    })
    updateCooperativeUser.mockResolvedValue({})
    inviteCooperativeUser.mockResolvedValue({
      id: 9,
      email: 'new@example.com',
      role: 'finance_officer',
      delivery: {
        channel: 'log',
        delivered: false,
        message: 'Email delivery is not configured',
        invite_link: 'http://localhost:5173/login?invite=abc',
      },
    })
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

  it('offers only cooperative roles in the invite picker (#255)', async () => {
    render(<GovernanceSettings />)
    const picker = await screen.findByLabelText('New user role')
    const values = Array.from(picker.querySelectorAll('option')).map((option) => option.value)
    expect(values).toEqual([
      'admin', 'finance_officer', 'field_officer', 'operations_officer', 'sales_officer',
    ])
    expect(picker.value).toBe('finance_officer')
    expect(Array.from(picker.querySelectorAll('optgroup')).map((group) => group.label)).toEqual(['Cooperative roles'])

    fireEvent.change(picker, { target: { value: 'sales_officer' } })
    expect(screen.getByText('Buyers and buyer sales')).toBeTruthy()
  })

  it('offers only solo-farm roles when the workspace is a solo farm (#255)', async () => {
    getOrganizationType.mockReturnValue('solo_farm')
    fetchCooperativeUsers.mockResolvedValue([
      { id: 8, email: 'manager@example.com', role: 'farm_manager', is_active: true },
    ])
    render(<GovernanceSettings />)
    const picker = await screen.findByLabelText('New user role')
    expect(Array.from(picker.querySelectorAll('option')).map((option) => option.value)).toEqual([
      'admin', 'farm_owner', 'farm_manager', 'supervisor',
    ])
    expect(picker.value).toBe('farm_manager')
    expect(Array.from(picker.querySelectorAll('optgroup')).map((group) => group.label)).toEqual(['Solo farm roles'])
  })

  it('surfaces the invite link when email delivery is not configured (#248)', async () => {
    render(<GovernanceSettings />)
    fireEvent.change(await screen.findByLabelText('New user email'), { target: { value: 'new@example.com' } })
    fireEvent.submit(screen.getByRole('button', { name: 'Send invite' }).closest('form'))
    await waitFor(() => expect(inviteCooperativeUser).toHaveBeenCalledWith('new@example.com', 'finance_officer'))
    expect(screen.getByText(/share this link with new@example.com/)).toBeTruthy()
    expect(screen.getByText(/login\?invite=abc/)).toBeTruthy()
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
