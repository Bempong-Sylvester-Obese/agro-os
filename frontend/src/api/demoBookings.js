import { API_URL, fetchJson } from './config'

export function createDemoBooking(booking) {
  return fetchJson(`${API_URL}/marketing/demo-bookings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(booking),
  })
}
