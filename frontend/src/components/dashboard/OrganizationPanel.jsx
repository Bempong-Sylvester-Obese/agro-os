// src/components/dashboard/OrganizationPanel.jsx
import React, { useCallback, useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { getAuthUser, storeAuthUser } from '../../api/auth'
import { formatTransportError } from '../../api/config'
import {
  createOrganization,
  createOrganizationCooperative,
  fetchOrganizationBilling,
  switchOrganizationCooperative,
} from '../../api/organizations'

const inputStyle = {
  width: '100%', padding: '10px 12px', border: '1.5px solid var(--border)', borderRadius: 8, fontSize: 14,
  fontFamily: "'DM Sans', sans-serif", outline: 'none', background: '#fff', color: 'var(--text)', boxSizing: 'border-box', marginTop: 6,
}
const labelStyle = { fontSize: 13, fontWeight: 600 }
const th = { padding: '8px 6px', textAlign: 'left', color: 'var(--muted)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '.6px' }
const td = { padding: '8px 6px', borderTop: '1px solid var(--border)', fontSize: 13 }

function fmtDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleDateString()
}

function meterText(m) {
  if (!m || m.included === false) return '—'
  return m.unlimited ? `${m.used} / ∞` : `${m.used} / ${m.limit}`
}

/**
 * Enterprise organization card for Settings.
 *
 * - No organization: an admin can create one from the current cooperative.
 * - Organization admin: contract status, member cooperatives with plan/usage,
 *   consolidated payment totals, add-cooperative form, and per-row "Switch".
 */
const defaultReloadPage = () => window.location.reload()

export default function OrganizationPanel({ cooperative, cooperativeId, user: userProp, reloadPage = defaultReloadPage }) {
  const user = userProp || getAuthUser()
  const organizationId = user?.organization_id || null
  const [billing, setBilling] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(null)
  const [notice, setNotice] = useState(null)
  const [orgForm, setOrgForm] = useState({ name: '', billing_email: '' })
  const [coopForm, setCoopForm] = useState({ name: '', location: '', organization_type: 'cooperative' })
  const [showAdd, setShowAdd] = useState(false)

  const reload = useCallback(async () => {
    if (!organizationId) return
    try {
      setBilling(await fetchOrganizationBilling(organizationId))
      setError(null)
    } catch (err) {
      setBilling(null)
      setError(formatTransportError(err))
    }
  }, [organizationId])

  useEffect(() => { reload() }, [reload])

  if (!user || (user.role || 'admin') !== 'admin') return null

  async function handleCreateOrg(event) {
    event.preventDefault()
    if (!orgForm.name.trim()) return
    setBusy('create-org')
    setError(null)
    try {
      const org = await createOrganization({
        name: orgForm.name.trim(),
        billing_email: orgForm.billing_email.trim() || null,
      })
      storeAuthUser({ ...(getAuthUser() || {}), organization_id: org.id })
      setNotice(`${org.name} created. Reloading…`)
      reloadPage()
    } catch (err) {
      setError(err.message || 'Could not create organization')
      setBusy(null)
    }
  }

  async function handleAddCoop(event) {
    event.preventDefault()
    if (!coopForm.name.trim()) return
    setBusy('add-coop')
    setError(null)
    try {
      const created = await createOrganizationCooperative(organizationId, {
        name: coopForm.name.trim(),
        location: coopForm.location.trim() || null,
        organization_type: coopForm.organization_type,
      })
      setNotice(`${created.name} added to the organization.`)
      setCoopForm({ name: '', location: '', organization_type: 'cooperative' })
      setShowAdd(false)
      await reload()
    } catch (err) {
      setError(err.message || 'Could not add cooperative')
    } finally {
      setBusy(null)
    }
  }

  async function handleSwitch(id) {
    setBusy(`switch-${id}`)
    setError(null)
    try {
      await switchOrganizationCooperative(organizationId, id)
      reloadPage()
    } catch (err) {
      setError(err.message || 'Could not switch cooperative')
      setBusy(null)
    }
  }

  return (
    <div>
      <h3 className="serif" style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Organization</h3>

      {error && <div role="alert" style={{ padding: 12, background: '#FEF2F2', color: '#991B1B', borderRadius: 8, fontSize: 13, marginBottom: 16 }}>{error}</div>}
      {notice && <div role="status" style={{ padding: 12, background: '#ecfdf5', color: '#047857', borderRadius: 8, fontSize: 13, marginBottom: 16 }}>{notice}</div>}

      {!organizationId ? (
        <>
          <p style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 12, lineHeight: 1.5 }}>
            Run several cooperatives under one Enterprise account: {cooperative?.name || 'this cooperative'} becomes the
            first member, you become the organization administrator, and billing can be consolidated once an Enterprise
            agreement is in place.
          </p>
          <form onSubmit={handleCreateOrg} className="settings-form-row" style={{ gap: 12, alignItems: 'flex-end' }}>
            <div style={{ flex: 2 }}>
              <label htmlFor="org-name" style={labelStyle}>Organization name</label>
              <input id="org-name" style={inputStyle} value={orgForm.name} onChange={(e) => setOrgForm({ ...orgForm, name: e.target.value })} required minLength={2} disabled={Boolean(busy)} />
            </div>
            <div style={{ flex: 2 }}>
              <label htmlFor="org-billing-email" style={labelStyle}>Billing email (optional)</label>
              <input id="org-billing-email" type="email" style={inputStyle} value={orgForm.billing_email} onChange={(e) => setOrgForm({ ...orgForm, billing_email: e.target.value })} disabled={Boolean(busy)} />
            </div>
            <div style={{ flex: 1 }}>
              <button type="submit" className="btn-lg" disabled={Boolean(busy) || !orgForm.name.trim()} style={{ padding: '10px 16px', display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                {busy === 'create-org' ? <><Loader2 size={16} className="spin" /> Creating…</> : 'Create organization'}
              </button>
            </div>
          </form>
        </>
      ) : !billing ? (
        <div style={{ fontSize: 13, color: 'var(--muted)' }}>{error ? 'Organization details are unavailable right now.' : 'Loading organization…'}</div>
      ) : (
        <>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, marginBottom: 16, background: 'var(--background)', borderRadius: 10, padding: 16 }}>
            <div style={{ flex: '1 1 160px' }}>
              <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.8px', marginBottom: 4 }}>Organization</div>
              <div style={{ fontSize: 18, fontWeight: 700 }}>{billing.organization.name}</div>
            </div>
            <div style={{ flex: '1 1 140px' }}>
              <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.8px', marginBottom: 4 }}>Enterprise contract</div>
              <div style={{ fontSize: 14, fontWeight: 600, textTransform: 'capitalize' }}>
                {billing.organization.subscription_status}
                {billing.organization.subscription_live && billing.organization.subscription_expires_at && (
                  <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--muted)' }}> · until {fmtDate(billing.organization.subscription_expires_at)}</span>
                )}
              </div>
            </div>
            <div style={{ flex: '1 1 140px' }}>
              <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.8px', marginBottom: 4 }}>Cooperatives</div>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{billing.totals.cooperatives}</div>
            </div>
            <div style={{ flex: '1 1 140px' }}>
              <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.8px', marginBottom: 4 }}>Members</div>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{billing.totals.members}</div>
            </div>
            <div style={{ flex: '1 1 140px' }}>
              <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.8px', marginBottom: 4 }}>Total paid</div>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{billing.totals.currency} {Number(billing.totals.paid).toLocaleString()}</div>
            </div>
          </div>

          {!billing.organization.subscription_live && (
            <div role="note" style={{ padding: '10px 14px', background: '#EFF6FF', border: '1px solid #BFDBFE', color: '#1E3A8A', borderRadius: 8, fontSize: 13, marginBottom: 16 }}>
              The Enterprise agreement is {billing.organization.subscription_status}. Each cooperative is billed on its own plan until the
              contract is activated; once active, all member cooperatives inherit the Enterprise plan.
            </div>
          )}

          <div style={{ overflowX: 'auto', marginBottom: 12 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }} aria-label="Organization cooperatives">
              <thead>
                <tr>
                  <th style={th}>Cooperative</th>
                  <th style={th}>Plan</th>
                  <th style={th}>Status</th>
                  <th style={th}>Members</th>
                  <th style={th}>SMS (month)</th>
                  <th style={th} />
                </tr>
              </thead>
              <tbody>
                {billing.cooperatives.map((c) => {
                  const isActive = c.id === (cooperativeId ?? user.cooperative_id) || c.is_active_scope
                  return (
                    <tr key={c.id}>
                      <td style={td}>
                        <strong>{c.name}</strong>
                        {isActive && <span style={{ marginLeft: 6, fontSize: 10, padding: '1px 6px', borderRadius: 999, background: '#ECFDF5', color: '#047857', fontWeight: 700 }}>ACTIVE</span>}
                        {c.location && <div style={{ fontSize: 11, color: 'var(--muted)' }}>{c.location}</div>}
                      </td>
                      <td style={td}>
                        {c.effective_plan_name || c.effective_plan_key}
                        {c.inherits_organization_plan && <div style={{ fontSize: 11, color: 'var(--muted)' }}>inherited</div>}
                      </td>
                      <td style={{ ...td, textTransform: 'capitalize' }}>{String(c.subscription_status).replace(/_/g, ' ')}</td>
                      <td style={td}>{meterText(c.members)}</td>
                      <td style={td}>{meterText(c.sms)}</td>
                      <td style={{ ...td, textAlign: 'right' }}>
                        {!isActive && (
                          <button type="button" className="dashboard-modal-btn-secondary" onClick={() => handleSwitch(c.id)} disabled={Boolean(busy)} style={{ fontSize: 12 }}>
                            {busy === `switch-${c.id}` ? 'Switching…' : 'Switch'}
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {showAdd ? (
            <form onSubmit={handleAddCoop} style={{ border: '1px solid var(--border)', borderRadius: 10, padding: 16, marginBottom: 12 }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Add a cooperative</div>
              <div className="settings-form-row" style={{ gap: 12, alignItems: 'flex-end' }}>
                <div style={{ flex: 2 }}>
                  <label htmlFor="org-coop-name" style={labelStyle}>Name</label>
                  <input id="org-coop-name" style={inputStyle} value={coopForm.name} onChange={(e) => setCoopForm({ ...coopForm, name: e.target.value })} required minLength={2} disabled={Boolean(busy)} />
                </div>
                <div style={{ flex: 2 }}>
                  <label htmlFor="org-coop-location" style={labelStyle}>Location</label>
                  <input id="org-coop-location" style={inputStyle} value={coopForm.location} onChange={(e) => setCoopForm({ ...coopForm, location: e.target.value })} disabled={Boolean(busy)} />
                </div>
                <div style={{ flex: 1 }}>
                  <label htmlFor="org-coop-type" style={labelStyle}>Type</label>
                  <select id="org-coop-type" style={inputStyle} value={coopForm.organization_type} onChange={(e) => setCoopForm({ ...coopForm, organization_type: e.target.value })} disabled={Boolean(busy)}>
                    <option value="cooperative">Cooperative</option>
                    <option value="solo_farm">Solo farm</option>
                  </select>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 10, marginTop: 12 }}>
                <button type="submit" className="btn-lg" disabled={Boolean(busy) || !coopForm.name.trim()} style={{ padding: '10px 16px' }}>
                  {busy === 'add-coop' ? <><Loader2 size={16} className="spin" /> Adding…</> : 'Add cooperative'}
                </button>
                <button type="button" className="dashboard-modal-btn-secondary" onClick={() => setShowAdd(false)} disabled={Boolean(busy)}>Cancel</button>
              </div>
            </form>
          ) : (
            <button type="button" className="btn-lg" onClick={() => setShowAdd(true)} disabled={Boolean(busy)} style={{ padding: '10px 16px', background: '#3B82F6', color: 'white' }}>
              Add cooperative
            </button>
          )}
        </>
      )}
    </div>
  )
}
