import { API_URL, apiFetch, authHeaders, parseResponseError } from './config'

export async function exportDashboardReport(report, cooperativeId, filters = {}) {
  const params = new URLSearchParams()
  if (cooperativeId) params.set('cooperative_id', cooperativeId)
  Object.entries(filters).forEach(([key, value]) => {
    if (value != null && value !== '') params.set(key, value)
  })

  const response = await apiFetch(`${API_URL}/reports/${report}.csv?${params}`, {
    headers: authHeaders(),
  })
  if (!response.ok) throw await parseResponseError(response)

  const blob = await response.blob()
  const disposition = response.headers.get('content-disposition') || ''
  const filename = disposition.match(/filename="?([^"]+)"?/)?.[1] || `${report}.csv`
  const url = window.URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.URL.revokeObjectURL(url)
}
