import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import BookDemoPage from './BookDemoPage'

describe('BookDemoPage', () => {
  let originalIntersectionObserver
  let originalScrollTo
  let originalCreateObjectURL
  let originalRevokeObjectURL

  beforeEach(() => {
    originalIntersectionObserver = globalThis.IntersectionObserver
    originalScrollTo = window.scrollTo
    originalCreateObjectURL = window.URL.createObjectURL
    originalRevokeObjectURL = window.URL.revokeObjectURL
    globalThis.IntersectionObserver = class {
      observe() { return undefined }
      unobserve() { return undefined }
      disconnect() { return undefined }
    }
    window.scrollTo = vi.fn()
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
    if (originalIntersectionObserver === undefined) delete globalThis.IntersectionObserver
    else globalThis.IntersectionObserver = originalIntersectionObserver
    if (originalScrollTo === undefined) delete window.scrollTo
    else window.scrollTo = originalScrollTo
    if (originalCreateObjectURL === undefined) delete window.URL.createObjectURL
    else window.URL.createObjectURL = originalCreateObjectURL
    if (originalRevokeObjectURL === undefined) delete window.URL.revokeObjectURL
    else window.URL.revokeObjectURL = originalRevokeObjectURL
  })

  function completeForm() {
    fireEvent.change(screen.getByLabelText(/Full name/i), { target: { value: 'Ama Mensah' } })
    fireEvent.change(screen.getByLabelText(/Work email/i), { target: { value: 'ama@example.com' } })
    fireEvent.change(screen.getByLabelText(/Organisation \*/i), { target: { value: 'Test Cooperative' } })
    fireEvent.change(screen.getByLabelText(/Preferred consultation date/i), { target: { value: '2099-08-20' } })
    fireEvent.click(screen.getByRole('button', { name: /9:00/i }))
  }

  it('accepts the legacy enterprise flag and uses the persisted booking reference', async () => {
    const persisted = {
      name: 'Ama Mensah',
      email: 'ama@example.com',
      phone: '',
      cooperative: 'Test Cooperative',
      size: '1–50 members',
      topic: 'Enterprise implementation',
      notes: '',
      selected_date: '2099-08-20',
      selected_time: '09:00',
      is_enterprise: true,
      reference: 'AGO-PERSISTED-42',
    }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => persisted,
    })

    render(
      <MemoryRouter initialEntries={['/book-demo?enterprise=true']}>
        <BookDemoPage />
      </MemoryRouter>,
    )
    completeForm()
    fireEvent.click(screen.getByRole('button', { name: /Request consultation/i }))

    expect(await screen.findByText('AGO-PERSISTED-42')).toBeTruthy()
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toMatchObject({
      selected_date: '2099-08-20',
      selected_time: '09:00',
      is_enterprise: true,
      topic: 'Enterprise implementation',
    })

    let calendarBlob
    window.URL.createObjectURL = vi.fn((blob) => {
      calendarBlob = blob
      return 'blob:calendar'
    })
    window.URL.revokeObjectURL = vi.fn()
    vi.spyOn(globalThis.HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    fireEvent.click(screen.getByRole('button', { name: /Add to calendar/i }))

    const calendarText = await new Promise((resolve) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result)
      reader.readAsText(calendarBlob)
    })
    expect(calendarText).toContain('UID:AGO-PERSISTED-42@agroos')
  })

  it('shows API failures without clearing the form', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 503,
      statusText: 'Service Unavailable',
      text: async () => JSON.stringify({ detail: 'Booking service unavailable' }),
    })

    render(
      <MemoryRouter initialEntries={['/book-demo']}>
        <BookDemoPage />
      </MemoryRouter>,
    )
    completeForm()
    fireEvent.click(screen.getByRole('button', { name: /Request consultation/i }))

    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('Booking service unavailable'))
    expect(screen.getByLabelText(/Full name/i).value).toBe('Ama Mensah')
    expect(screen.getByLabelText(/Work email/i).value).toBe('ama@example.com')
    expect(screen.getByLabelText(/Preferred consultation date/i).value).toBe('2099-08-20')
  })
})
