// src/components/dashboard/OrganizationSwitcher.jsx
import React, { useEffect, useState } from 'react'
import { fetchMyOrganization, switchOrganizationCooperative } from '../../api/organizations'

/**
 * Sidebar control for organization administrators: switch the active
 * cooperative among the organization's members. Renders nothing for users
 * without an organization. After a switch the page reloads so every
 * cooperative-scoped view re-fetches under the new scope.
 */
export default function OrganizationSwitcher({ user, activeCooperativeId, onSwitched }) {
  const [org, setOrg] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const organizationId = user?.organization_id

  useEffect(() => {
    if (!organizationId) return undefined
    let cancelled = false
    fetchMyOrganization()
      .then((data) => { if (!cancelled) setOrg(data) })
      .catch(() => { if (!cancelled) setOrg(null) })
    return () => { cancelled = true }
  }, [organizationId])

  if (!organizationId || !org || !Array.isArray(org.cooperatives) || org.cooperatives.length < 2) return null

  const current = activeCooperativeId ?? org.cooperatives.find((c) => c.is_active_scope)?.id ?? ''

  async function handleChange(event) {
    const nextId = Number(event.target.value)
    if (!nextId || nextId === current) return
    setBusy(true)
    setError(null)
    try {
      await switchOrganizationCooperative(org.id, nextId)
      if (onSwitched) onSwitched(nextId)
      else window.location.reload()
    } catch (err) {
      setError(err.message || 'Could not switch cooperative')
      setBusy(false)
    }
  }

  return (
    <div className="admin-side-org" data-testid="organization-switcher">
      <label className="admin-side-sub-label" htmlFor="org-switcher-select">{org.name}</label>
      <select
        id="org-switcher-select"
        value={current}
        onChange={handleChange}
        disabled={busy}
        aria-label="Switch cooperative"
        style={{
          width: '100%', marginTop: 4, fontSize: 11, padding: '4px 6px', borderRadius: 6,
          background: 'rgba(255,255,255,.08)', color: 'rgba(255,255,255,.85)', border: '1px solid rgba(255,255,255,.15)',
        }}
      >
        {org.cooperatives.map((c) => (
          <option key={c.id} value={c.id} style={{ color: '#111' }}>{c.name}</option>
        ))}
      </select>
      {error && <div role="alert" style={{ fontSize: 10, color: '#FCA5A5', marginTop: 4 }}>{error}</div>}
    </div>
  )
}
