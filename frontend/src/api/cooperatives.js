const API_URL = import.meta.env.VITE_API_URL || 'https://previewbackendagro-os.onrender.com'

function authHeaders() {
  const token = localStorage.getItem('agro_os_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

/**
 * Fetch a cooperative by ID. Returns null on any error.
 */
export async function fetchCooperative(cooperativeId) {
  if (!cooperativeId) return null
  const res = await fetch(`${API_URL}/cooperatives/${cooperativeId}`, {
    headers: authHeaders(),
  })
  if (!res.ok) return null
  return res.json()
}

export async function updateCooperative(cooperativeId, data) {
  const res = await fetch(`${API_URL}/cooperatives/${cooperativeId}`, {
    method: 'PUT',
    headers: {
      ...authHeaders(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  })
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Failed to update cooperative')
  }
  return res.json()
}
