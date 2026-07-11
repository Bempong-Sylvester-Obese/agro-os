const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function login(email, password) {
  const response = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Login failed')
  }
  return await response.json()
}

/**
 * New combined onboarding signup — creates a cooperative + admin user in one shot.
 * @param {string} email
 * @param {string} password
 * @param {string} cooperativeName  - Name of the farm / cooperative
 * @param {string} [location]       - Optional location
 * @param {number} [memberCount]    - Approximate size of cooperative
 */
export async function signup({ email, password, cooperativeName, location, memberCount }) {
  const response = await fetch(`${API_URL}/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      password,
      cooperative_name: cooperativeName,
      location: location || null,
      member_count: memberCount ? parseInt(memberCount, 10) : null,
    }),
  })
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Registration failed')
  }
  return await response.json()
}

export async function register(email, password, cooperativeId = null) {
  const response = await fetch(`${API_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, cooperative_id: cooperativeId }),
  })
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Registration failed')
  }
  return await response.json()
}
