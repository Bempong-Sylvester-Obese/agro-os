import { TOKEN_KEY } from '../api/auth'

/**
 * Resolve the cooperative ID from JWT, stored user, loaded farmers, or env fallback.
 */
export function resolveCooperativeId(user = null, farmers = []) {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    try {
      const segment = token.split('.')[1]
      const base64 = segment.replace(/-/g, '+').replace(/_/g, '/')
      const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4)
      const payload = JSON.parse(atob(padded))
      if (payload.cooperative_id != null) return payload.cooperative_id
    } catch {
      // fall through
    }
  }
  if (user?.cooperative_id != null) return user.cooperative_id
  const fromFarmer = farmers.find((f) => f.cooperative_id != null)
  if (fromFarmer) return fromFarmer.cooperative_id
  const envId = import.meta.env.VITE_COOPERATIVE_ID
  if (envId) return Number(envId)
  return null
}

/**
 * Decodes the stored JWT to extract cooperative_id, user_id, and email.
 * No crypto verification — server-side auth is authoritative.
 */
export function getAuthInfo() {
  const token = localStorage.getItem(TOKEN_KEY)
  if (!token) return { cooperative_id: null, email: null, user_id: null }
  try {
    const segment = token.split('.')[1]
    const base64 = segment.replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4)
    const payload = JSON.parse(atob(padded))
    return {
      cooperative_id: payload.cooperative_id ?? null,
      user_id: payload.user_id ?? null,
      email: payload.sub ?? null,
    }
  } catch {
    return { cooperative_id: null, email: null, user_id: null }
  }
}

/** Returns 1–2 uppercase initials from an email address. */
export function getInitials(email) {
  if (!email) return '?'
  const name = email.split('@')[0]
  const parts = name.split(/[._\-+]/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return name.slice(0, 2).toUpperCase()
}
