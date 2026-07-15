import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Members from './Members'
import * as farmersApi from '../../api/farmers'

vi.mock('../../api/farmers', () => ({
  createFarmer: vi.fn(),
  updateFarmer: vi.fn(),
  deactivateFarmer: vi.fn(),
}))
vi.mock('../../api/reports', () => ({ exportDashboardReport: vi.fn() }))
vi.mock('../Motion', () => ({
  ModalPresence: ({ show, children }) => show ? children : null,
}))

const member = {
  id: 4,
  name: 'Ama Mensah',
  phone: '0200000000',
  email: 'ama@example.com',
  location: 'Kumasi',
  crop_type: 'Maize',
  acreage: 4,
  membership_status: 'active',
  trust_score: 72,
  created_at: '2026-07-01T10:00:00Z',
}

describe('Members administration', () => {
  afterEach(cleanup)
  beforeEach(() => vi.clearAllMocks())

  it('suspends a member through the existing update API', async () => {
    farmersApi.updateFarmer.mockResolvedValue({ ...member, membership_status: 'suspended' })
    const onMemberAdded = vi.fn()
    render(<Members farmers={[member]} cooperativeId={2} onMemberAdded={onMemberAdded} loading={false} />)

    fireEvent.click(screen.getByRole('button', { name: 'Edit Ama Mensah' }))
    expect(screen.getByRole('dialog', { name: 'Member details' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Suspend' }))

    await waitFor(() => expect(farmersApi.updateFarmer).toHaveBeenCalledWith(4, { membership_status: 'suspended' }))
    expect(onMemberAdded).toHaveBeenCalled()
  })

  it('deactivates a member through the soft-delete API', async () => {
    farmersApi.deactivateFarmer.mockResolvedValue()
    render(<Members farmers={[member]} cooperativeId={2} onMemberAdded={vi.fn()} loading={false} />)

    fireEvent.click(screen.getByRole('button', { name: 'Edit Ama Mensah' }))
    fireEvent.click(screen.getByRole('button', { name: 'Deactivate' }))

    await waitFor(() => expect(farmersApi.deactivateFarmer).toHaveBeenCalledWith(4))
  })
})
