import React from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Announcements from './Announcements'
import { fetchAnnouncements } from '../../api/announcements'

vi.mock('../../api/announcements', () => ({
  fetchAnnouncements: vi.fn(),
  createAnnouncement: vi.fn(),
  deleteAnnouncement: vi.fn(),
}))

describe('Announcements', () => {
  beforeEach(() => {
    fetchAnnouncements.mockResolvedValue([
      {
        id: 9,
        title: 'Monthly meeting',
        body: 'Meet at the cooperative office.',
        send_sms: false,
        created_at: '2026-08-17T10:00:00',
      },
    ])
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('keeps announcements read-only for operational roles', async () => {
    render(<Announcements cooperativeId={4} userRole="farm_manager" />)

    expect(await screen.findByText('Monthly meeting')).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Post announcement' })).toBeNull()
    expect(screen.queryByRole('button', { name: /Delete announcement/ })).toBeNull()
  })

  it('exposes labelled delete controls only to administrators', async () => {
    render(<Announcements cooperativeId={4} userRole="admin" />)

    expect(await screen.findByRole('button', {
      name: 'Delete announcement: Monthly meeting',
    })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Post announcement' })).toBeTruthy()
  })
})
