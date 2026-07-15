import { afterEach, describe, expect, it, vi } from 'vitest'
import { createDemoBooking } from './demoBookings'

describe('demo bookings api', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('posts the booking contract and returns persisted data', async () => {
    const booking = {
      name: 'Ama Mensah',
      email: 'ama@example.com',
      phone: '+233240000000',
      cooperative: 'Test Cooperative',
      size: '51–200 members',
      topic: 'Enterprise implementation',
      notes: 'Migration planning',
      selected_date: '2026-08-20',
      selected_time: '10:00',
      is_enterprise: true,
    }
    const persisted = { ...booking, reference: 'AGO-ABC123' }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => persisted,
    })

    await expect(createDemoBooking(booking)).resolves.toEqual(persisted)
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/marketing\/demo-bookings$/)
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual(booking)
  })
})
