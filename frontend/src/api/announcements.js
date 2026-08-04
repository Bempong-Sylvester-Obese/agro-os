import { API_URL, apiFetch, authHeaders } from './config'

export async function fetchAnnouncements(cooperativeId) {
  const res = await apiFetch(`${API_URL}/announcements/?cooperative_id=${cooperativeId}`, {
    headers: authHeaders(),
  })
  if (!res.ok) {
    const e = await res.json().catch(() => ({}))
    throw new Error(e.detail || 'Failed to load announcements')
  }
  return res.json()
}

export async function createAnnouncement(cooperativeId, payload) {
  const res = await apiFetch(`${API_URL}/announcements/?cooperative_id=${cooperativeId}`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const e = await res.json().catch(() => ({}))
    throw new Error(e.detail || 'Failed to create announcement')
  }
  return res.json()
}

export async function deleteAnnouncement(cooperativeId, id) {
  const res = await apiFetch(`${API_URL}/announcements/${id}?cooperative_id=${cooperativeId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (!res.ok) {
    const e = await res.json().catch(() => ({}))
    throw new Error(e.detail || 'Failed to delete announcement')
  }
}
