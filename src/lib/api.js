// src/lib/api.js
// Central API client — every network call the dashboard makes goes through here.
// Configure the backend URL via VITE_API_URL (see frontend/.env.example).

export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const TOKEN_KEY = 'agro_os_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

class ApiError extends Error {
  constructor(message, status, data) {
    super(message)
    this.status = status
    this.data = data
  }
}

async function request(path, { method = 'GET', body, auth = true, params } = {}) {
  let url = `${API_URL}${path}`
  if (params) {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
    ).toString()
    if (qs) url += `?${qs}`
  }

  const headers = { 'Content-Type': 'application/json' }
  if (auth) {
    const token = getToken()
    if (token) headers['Authorization'] = `Bearer ${token}`
  }

  let res
  try {
    res = await fetch(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch (err) {
    throw new ApiError(
      `Could not reach the AgroOS API at ${API_URL}. Is the backend running?`,
      0,
      null
    )
  }

  if (res.status === 204) return null

  let data = null
  const text = await res.text()
  if (text) {
    try { data = JSON.parse(text) } catch { data = text }
  }

  if (!res.ok) {
    const message = (data && (data.detail || data.message)) || `Request failed (${res.status})`
    throw new ApiError(typeof message === 'string' ? message : JSON.stringify(message), res.status, data)
  }

  return data
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export const authApi = {
  signup: (payload) => request('/auth/signup', { method: 'POST', body: payload, auth: false }),
  login: (payload) => request('/auth/login', { method: 'POST', body: payload, auth: false }),
  me: () => request('/auth/me'),
}

// ---------------------------------------------------------------------------
// Cooperatives
// ---------------------------------------------------------------------------

export const cooperativesApi = {
  get: (id) => request(`/cooperatives/${id}`),
}

// ---------------------------------------------------------------------------
// Farmers (Members)
// ---------------------------------------------------------------------------

export const farmersApi = {
  list: (cooperativeId) => request('/farmers/', { params: { cooperative_id: cooperativeId, limit: 500 } }),
  create: (payload) => request('/farmers/', { method: 'POST', body: payload }),
  get: (id) => request(`/farmers/${id}`),
  update: (id, payload) => request(`/farmers/${id}`, { method: 'PUT', body: payload }),
  deactivate: (id) => request(`/farmers/${id}`, { method: 'DELETE' }),
  trustScore: (id) => request(`/farmers/${id}/trust-score`),
  recalculateTrustScore: (id) => request(`/farmers/${id}/recalculate-trust-score`, { method: 'POST' }),
}

// ---------------------------------------------------------------------------
// Transactions (Payments)
// ---------------------------------------------------------------------------

export const transactionsApi = {
  list: (params) => request('/transactions/', { params }),
  collectDues: (payload) => request('/transactions/dues/collect', { method: 'POST', body: payload }),
}

// ---------------------------------------------------------------------------
// Loans
// ---------------------------------------------------------------------------

export const loansApi = {
  list: (params) => request('/loans/', { params }),
  create: (payload) => request('/loans/', { method: 'POST', body: payload }),
  approve: (id, payload) => request(`/loans/${id}/approve`, { method: 'POST', body: payload }),
  reject: (id) => request(`/loans/${id}/reject`, { method: 'POST' }),
  disburse: (id) => request(`/loans/${id}/disburse`, { method: 'POST' }),
  repay: (id) => request(`/loans/${id}/repay`, { method: 'POST' }),
}

// ---------------------------------------------------------------------------
// Communications (SMS)
// ---------------------------------------------------------------------------

export const communicationsApi = {
  broadcast: (payload) => request('/communications/sms/broadcast', { method: 'POST', body: payload }),
  duesReminder: (payload) => request('/communications/sms/dues-reminder', { method: 'POST', body: payload }),
  logs: (params) => request('/communications/logs', { params }),
}

// ---------------------------------------------------------------------------
// Agro-AI credit scoring
// ---------------------------------------------------------------------------

export const agroAiApi = {
  creditSummary: () => request('/api/agro-ai/credit-summary'),
}

export { ApiError }
