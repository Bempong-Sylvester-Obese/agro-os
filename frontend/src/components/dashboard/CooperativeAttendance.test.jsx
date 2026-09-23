import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import CooperativeAttendance from './CooperativeAttendance'
import { fetchCooperativeAttendance, recordMeetingAttendance } from '../../api/farmers'
import { getUserRole } from '../../utils/auth'

vi.mock('../../api/farmers', () => ({
  fetchCooperativeAttendance: vi.fn(),
  recordMeetingAttendance: vi.fn(),
}))

vi.mock('../../utils/auth', () => ({
  getUserRole: vi.fn(() => 'admin'),
}))

const farmers = [
  { id: 1, name: 'Ama Mensah', phone: '0241111111' },
  { id: 2, name: 'Kofi Boateng', phone: '0242222222' },
]

describe('CooperativeAttendance', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getUserRole.mockReturnValue('admin')
    fetchCooperativeAttendance.mockResolvedValue([
      { id: 10, farmer_id: 1, event_name: 'AGM', event_date: '2026-08-01T10:00:00', attended: true },
    ])
    recordMeetingAttendance.mockResolvedValue({ recorded: 2, present: 1 })
  })
  afterEach(cleanup)

  it('loads recent records through the farmers API helper', async () => {
    render(<CooperativeAttendance cooperativeId={5} farmers={farmers} />)
    expect(await screen.findByText('AGM')).toBeTruthy()
    expect(fetchCooperativeAttendance).toHaveBeenCalledWith(5, [1, 2])
    expect(screen.getByText('Ama Mensah', { selector: 'td' })).toBeTruthy()
    expect(screen.getByText('Present')).toBeTruthy()
  })

  it('records a meeting for every member, then refreshes and notifies the dashboard', async () => {
    const onRecorded = vi.fn()
    render(<CooperativeAttendance cooperativeId={5} farmers={farmers} onRecorded={onRecorded} />)
    await screen.findByText('AGM')

    const form = screen.getByRole('form', { name: 'Log meeting attendance' })
    fireEvent.change(within(form).getByLabelText('Event date'), { target: { value: '2026-09-20' } })
    fireEvent.change(within(form).getByLabelText('Event name'), { target: { value: 'Monthly General Meeting' } })
    fireEvent.click(within(form).getByLabelText(/Ama Mensah/))
    expect(within(form).getByText('1 of 2 present')).toBeTruthy()

    fireEvent.click(within(form).getByRole('button', { name: 'Log attendance' }))

    await waitFor(() => expect(recordMeetingAttendance).toHaveBeenCalledWith(
      5,
      { 1: true, 2: false },
      { eventName: 'Monthly General Meeting', eventDate: '2026-09-20' },
    ))
    expect(await screen.findByRole('status')).toBeTruthy()
    expect(screen.getByRole('status').textContent).toContain('1 of 2 members present')
    await waitFor(() => expect(fetchCooperativeAttendance).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(onRecorded).toHaveBeenCalledWith(expect.objectContaining({ recorded: 2, present: 1 })))
    expect(within(form).getByLabelText('Event name').value).toBe('')
  })

  it('shows a real error state instead of an alert when recording fails', async () => {
    recordMeetingAttendance.mockRejectedValue(Object.assign(new Error('Insufficient permissions'), { status: 403 }))
    render(<CooperativeAttendance cooperativeId={5} farmers={farmers} />)
    await screen.findByText('AGM')

    const form = screen.getByRole('form', { name: 'Log meeting attendance' })
    fireEvent.change(within(form).getByLabelText('Event date'), { target: { value: '2026-09-20' } })
    fireEvent.change(within(form).getByLabelText('Event name'), { target: { value: 'Training' } })
    fireEvent.click(within(form).getByRole('button', { name: 'Log attendance' }))

    expect(await within(form).findByRole('alert')).toBeTruthy()
    expect(within(form).getByRole('alert').textContent).toContain('Insufficient permissions')
  })

  it('offers a retry when loading records fails', async () => {
    fetchCooperativeAttendance.mockRejectedValueOnce(new TypeError('network down'))
    render(<CooperativeAttendance cooperativeId={5} farmers={farmers} />)
    const banner = await screen.findByRole('alert')
    expect(banner.textContent).toContain('Failed to load attendance records')
    fireEvent.click(within(banner).getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('AGM')).toBeTruthy()
  })

  it('hides the recording form from roles that cannot record attendance', async () => {
    getUserRole.mockReturnValue('sales_officer')
    render(<CooperativeAttendance cooperativeId={5} farmers={farmers} />)
    await screen.findByText('AGM')
    expect(screen.queryByRole('form', { name: 'Log meeting attendance' })).toBeNull()
  })
})
