import { API_URL, authHeaders, fetchJson } from './config'

export function previewDemoReset() {
  return fetchJson(`${API_URL}/admin/demo-reset/preview`, {
    headers: authHeaders(),
  })
}

export function confirmDemoReset(confirmationToken, confirmationPhrase) {
  return fetchJson(`${API_URL}/admin/demo-reset/confirm`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify({
      confirmation_token: confirmationToken,
      confirmation_phrase: confirmationPhrase,
    }),
  })
}
