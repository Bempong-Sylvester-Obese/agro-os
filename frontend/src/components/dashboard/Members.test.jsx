import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Members from './Members'
import * as farmersApi from '../../api/farmers'
import { exportDashboardReport } from '../../api/reports'

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
  production_focus: 'crop',
  crop_type: 'Maize',
  acreage: 4,
  membership_status: 'active',
  trust_score: 72,
  created_at: '2026-07-01T10:00:00Z',
}

describe('Members administration', () => {
  afterEach(cleanup)
  beforeEach(() => vi.clearAllMocks())

  it('shows conditional animal fields and submits an animal profile', async () => {
    farmersApi.createFarmer.mockResolvedValue({
      ...member,
      id: 5,
      production_focus: 'animal',
      animal_type: 'Poultry',
      animal_scale: 250,
    })
    render(<Members farmers={[member]} cooperativeId={2} onMemberAdded={vi.fn()} loading={false} />)

    fireEvent.click(screen.getByRole('button', { name: 'Add member' }))
    fireEvent.change(screen.getByLabelText('Production focus *'), { target: { value: 'animal' } })

    expect(screen.queryByLabelText(/Crop type/)).toBeNull()
    expect(screen.getByLabelText(/Animal type/)).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Full name *'), { target: { value: 'Kojo Owusu' } })
    fireEvent.change(screen.getByLabelText('Phone number *'), { target: { value: '0240000000' } })
    fireEvent.change(screen.getByLabelText(/Animal type/), { target: { value: 'Poultry' } })
    fireEvent.change(screen.getByLabelText(/Number of animals/), { target: { value: '250' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add member →' }))

    await waitFor(() => expect(farmersApi.createFarmer).toHaveBeenCalledWith(expect.objectContaining({
      cooperative_id: 2,
      production_focus: 'animal',
      animal_type: 'Poultry',
      animal_scale: 250,
    })))
    expect(farmersApi.createFarmer.mock.calls[0][0]).not.toHaveProperty('crop_type')
  })

  it('shows both profile sections for mixed production', () => {
    render(<Members farmers={[member]} cooperativeId={2} onMemberAdded={vi.fn()} loading={false} />)

    fireEvent.click(screen.getByRole('button', { name: 'Add member' }))
    fireEvent.change(screen.getByLabelText('Production focus *'), { target: { value: 'mixed' } })

    expect(screen.getByLabelText(/Crop type/)).toBeTruthy()
    expect(screen.getByLabelText(/Animal type/)).toBeTruthy()
  })

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

  it('announces export failures to the user', async () => {
    exportDashboardReport.mockRejectedValue(new Error('Report service unavailable'))
    render(<Members farmers={[member]} cooperativeId={2} onMemberAdded={vi.fn()} loading={false} />)

    fireEvent.click(screen.getByRole('button', { name: 'Export filtered Members as CSV' }))

    expect((await screen.findByRole('alert')).textContent).toContain('Report service unavailable')
  })
})
