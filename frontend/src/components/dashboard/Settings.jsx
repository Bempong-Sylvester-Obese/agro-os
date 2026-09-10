// src/components/dashboard/Settings.jsx
import React, { useEffect, useRef, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { confirmDemoReset, previewDemoReset } from '../../api/admin'
import { createSubscriptionCheckout, updateCooperative } from '../../api/cooperatives'
import { formatTransportError } from '../../api/config'
import { fetchFarmers } from '../../api/farmers'
import { SettingsSkeleton } from './DashboardSkeleton'
import GovernanceSettings from './GovernanceSettings'
import DashboardModal, { ModalField } from './DashboardModal'

const RESET_COUNT_LABELS = {
  memberships: 'Farmer memberships',
  transactions: 'Transactions',
  loans: 'Loans',
  productions: 'Production records',
  trust_scores: 'Trust scores',
  attendances: 'Attendance records',
  webhook_events: 'Payment webhook events',
  communications: 'Communication logs',
  ussd_sessions: 'USSD sessions',
  ai_predictions: 'AI prediction logs',
}

export default function Settings({ cooperative, cooperativeId, loading, onRefresh }) {
  const [form, setForm] = useState({
    name: '',
    location: '',
    description: '',
    default_currency: 'GHS',
    integration_account_number: ''
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [successMsg, setSuccessMsg] = useState(null)
  const [resetPreview, setResetPreview] = useState(null)
  const [resetPhrase, setResetPhrase] = useState('')
  const [resetStatus, setResetStatus] = useState('idle')
  const [resetError, setResetError] = useState(null)
  const [resetDialogOpen, setResetDialogOpen] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [memberCount, setMemberCount] = useState(null)
  const resetInputRef = useRef(null)

  useEffect(() => {
    if (cooperative) {
      setForm({
        name: cooperative.name || '',
        location: cooperative.location || '',
        description: cooperative.description || '',
        default_currency: cooperative.currency || cooperative.default_currency || 'GHS',
        integration_account_number: cooperative.moolre_account_number || ''
      })
    }
  }, [cooperative])

  useEffect(() => {
    if (!resetDialogOpen) return undefined
    const focusFrame = requestAnimationFrame(() => resetInputRef.current?.focus())
    return () => cancelAnimationFrame(focusFrame)
  }, [resetDialogOpen])

  useEffect(() => {
    if (!cooperativeId || !cooperative) return
    const plan = (cooperative.subscription_plan || '').toLowerCase()
    if (plan === 'starter' || plan === 'growth') {
      let cancelled = false
      const loadMemberCount = async () => {
        const pageSize = 100
        let count = 0
        while (true) {
          const page = await fetchFarmers(cooperativeId, null, count, pageSize)
          count += page.length
          if (page.length < pageSize) break
        }
        if (!cancelled) setMemberCount(count)
      }
      loadMemberCount().catch(() => {
        if (!cancelled) setMemberCount(null)
      })
      return () => {
        cancelled = true
      }
    }
  }, [cooperativeId, cooperative])

  if (loading) return <SettingsSkeleton />

  if (!cooperative) {
    return (
      <div style={{ padding: 32, maxWidth: 480 }}>
        <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 8 }}>Could not load cooperative settings</div>
        <p style={{ fontSize: 14, color: 'var(--muted)', marginBottom: 16, lineHeight: 1.5 }}>
          {cooperativeId
            ? 'Your cooperative profile could not be fetched. Check your connection and try again.'
            : 'No cooperative is linked to your account. Log in with a cooperative admin account or complete signup.'}
        </p>
        {onRefresh && (
          <button type="button" className="btn-lg" style={{ padding: '10px 20px', fontSize: 13 }} onClick={onRefresh}>
            Retry
          </button>
        )}
      </div>
    )
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setSuccessMsg(null)

    try {
      const { default_currency, integration_account_number, ...rest } = form
      await updateCooperative(cooperative.id, {
        ...rest,
        currency: default_currency,
        moolre_account_number: integration_account_number,
      })
      setSuccessMsg('Settings updated successfully.')
      if (onRefresh) onRefresh()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleOpenReset = async () => {
    setResetStatus('loading')
    setResetError(null)
    setResetPhrase('')
    try {
      const preview = await previewDemoReset()
      setResetPreview(preview)
      setResetStatus('eligible')
      setResetDialogOpen(true)
    } catch (err) {
      if (err?.status === 403 || err?.status === 404) {
        setResetStatus('unavailable')
      } else {
        setResetStatus('error')
        setResetError(formatTransportError(err))
      }
    }
  }

  const handleConfirmReset = async (event) => {
    event.preventDefault()
    if (!resetPreview || resetPhrase !== resetPreview.confirmation_phrase) return
    setResetting(true)
    setResetError(null)
    try {
      await confirmDemoReset(resetPreview.confirmation_token, resetPhrase)
      setResetDialogOpen(false)
      setResetPreview(null)
      setResetPhrase('')
      setResetStatus('success')
      if (onRefresh) await onRefresh()
    } catch (err) {
      setResetError(formatTransportError(err))
    } finally {
      setResetting(false)
    }
  }

  const inputStyle = {
    width: '100%', padding: '10px 12px', border: '1.5px solid var(--border)',
    borderRadius: 8, fontSize: 14, fontFamily: "'DM Sans', sans-serif",
    outline: 'none', background: '#fff', color: 'var(--text)', boxSizing: 'border-box',
    marginTop: 6
  }

  const labelStyle = { fontSize: 13, fontWeight: 600 }

  const planNames = { starter: 'Starter', solo: 'Solo Farm', growth: 'Growth', enterprise: 'Enterprise' }
  const planName = planNames[cooperative?.subscription_plan?.toLowerCase()] || 'Unknown Plan'

  const statusColors = {
    active: 'green',
    trial: 'blue',
    past_due: 'orange',
    expired: 'red',
    cancelled: 'gray',
  }
  const statusColor = statusColors[cooperative?.subscription_status] || 'gray'

  const planMaxMembers = cooperative?.subscription_plan?.toLowerCase() === 'starter' ? 10
    : cooperative?.subscription_plan?.toLowerCase() === 'growth' ? 500
    : null

  const showMemberBar = planMaxMembers && memberCount !== null
  const memberPct = showMemberBar ? Math.min((memberCount / planMaxMembers) * 100, 100) : 0

  const isExpiring = cooperative?.subscription_status === 'expired' || cooperative?.subscription_status === 'past_due'

  return (
    <div style={{ maxWidth: 800 }}>
      <div className="admin-card">
        <div className="admin-card-head" style={{ borderBottom: '1px solid var(--border)', padding: '24px 28px' }}>
          <div>
            <div className="serif" style={{ fontWeight: 700, fontSize: 20 }}>Cooperative Settings</div>
            <div style={{ fontSize: 13, color: 'var(--muted)', marginTop: 4 }}>Update your organization's profile and payment configurations</div>
          </div>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: '28px' }}>
          {error && <div style={{ padding: 12, background: '#FEF2F2', color: '#991B1B', borderRadius: 8, fontSize: 13, marginBottom: 20 }}>{error}</div>}
          {successMsg && <div style={{ padding: 12, background: '#ecfdf5', color: '#047857', borderRadius: 8, fontSize: 13, marginBottom: 20 }}>{successMsg}</div>}
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* General Profile */}
            <div>
              <h3 className="serif" style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>General Profile</h3>
              <div className="settings-form-row" style={{ marginBottom: 16 }}>
                <div style={{ flex: 2 }}>
                  <label htmlFor="settings-name" style={labelStyle}>Cooperative Name</label>
                  <input id="settings-name" style={inputStyle} type="text" value={form.name} onChange={e => setForm({...form, name: e.target.value})} required disabled={saving}/>
                </div>
                <div style={{ flex: 1 }}>
                  <label htmlFor="settings-location" style={labelStyle}>Location / Region</label>
                  <input id="settings-location" style={inputStyle} type="text" value={form.location} onChange={e => setForm({...form, location: e.target.value})} disabled={saving}/>
                </div>
              </div>
              <div>
                <label htmlFor="settings-description" style={labelStyle}>Description</label>
                <textarea 
                  id="settings-description"
                  style={{ ...inputStyle, minHeight: 80, resize: 'vertical' }} 
                  value={form.description} 
                  onChange={e => setForm({...form, description: e.target.value})} 
                  disabled={saving}
                />
              </div>

              <div style={{ marginTop: 16 }}>
                <label style={labelStyle}>Cooperative USSD Onboarding Code</label>
                <input 
                  style={{...inputStyle, background: 'var(--background)'}} 
                  type="text" 
                  value={cooperative.ussd_code || 'Not Generated'} 
                  disabled 
                  readOnly 
                />
                <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>Farmers can use this code to join your cooperative via USSD.</p>
              </div>
            </div>

            <div style={{ height: 1, background: 'var(--border)', margin: '12px 0' }} />

            {/* Financial Configuration */}
            <div>
              <h3 className="serif" style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Financial Configuration</h3>
              <p style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 16 }}>Enter your cooperative's dedicated Moolre sub-wallet account number. This account will receive all transaction splits and loan repayments.</p>
              
              <div className="settings-form-row" style={{ marginBottom: 16 }}>
                <div style={{ flex: 1 }}>
                  <label htmlFor="settings-currency" style={labelStyle}>Default Currency</label>
                  <select id="settings-currency" style={inputStyle} value={form.default_currency} onChange={e => setForm({...form, default_currency: e.target.value})} disabled={saving}>
                    <option value="GHS">Ghana Cedi (GHS)</option>
                    <option value="USD">US Dollar (USD)</option>
                  </select>
                </div>
                <div style={{ flex: 2 }}>
                  <label htmlFor="settings-integration-account" style={labelStyle}>Moolre Account Number</label>
                  <input id="settings-integration-account" style={inputStyle} type="text" value={form.integration_account_number} onChange={e => setForm({...form, integration_account_number: e.target.value})} placeholder="e.g. 1089700..." required disabled={saving}/>
                </div>
              </div>
            </div>
            <div style={{ height: 1, background: 'var(--border)', margin: '12px 0' }} />

            {/* Platform Subscription */}
            <div>
              <h3 className="serif" style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Platform Subscription</h3>
              <p style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 16 }}>Manage your cooperative's plan and billing status.</p>

              {isExpiring && (
                <div role="alert" style={{
                  padding: '12px 16px', background: '#FFFBEB', border: '1px solid #FBBF24',
                  borderRadius: 8, fontSize: 13, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8
                }}>
                  <span style={{ fontWeight: 700, color: '#92400E' }}>
                    {cooperative.subscription_status === 'expired' ? 'Subscription expired.' : 'Payment past due.'}
                  </span>
                  <span style={{ color: '#78350F' }}>Some features may be limited. Renew your plan to restore full access.</span>
                </div>
              )}

              <div style={{
                display: 'flex', flexWrap: 'wrap', gap: 16, marginBottom: 16,
                background: 'var(--background)', borderRadius: 10, padding: 16
              }}>
                <div style={{ flex: '1 1 140px' }}>
                  <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.8px', marginBottom: 4 }}>Current Plan</div>
                  <div style={{ fontSize: 18, fontWeight: 700 }}>{planName}</div>
                </div>
                <div style={{ flex: '1 1 140px' }}>
                  <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.8px', marginBottom: 4 }}>Status</div>
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                    <span style={{
                      width: 8, height: 8, borderRadius: '50%', display: 'inline-block',
                      background: statusColor
                    }} />
                    <span style={{ fontSize: 14, fontWeight: 600, textTransform: 'capitalize' }}>
                      {(cooperative?.subscription_status || 'inactive').replace(/_/g, ' ')}
                    </span>
                  </div>
                </div>
                {planMaxMembers && (
                  <div style={{ flex: '1 1 140px' }}>
                    <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.8px', marginBottom: 4 }}>Max Members</div>
                    <div style={{ fontSize: 14, fontWeight: 600 }}>{planMaxMembers.toLocaleString()}</div>
                  </div>
                )}
                {cooperative?.subscription_expires_at && (
                  <div style={{ flex: '1 1 140px' }}>
                    <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.8px', marginBottom: 4 }}>Expires</div>
                    <div style={{ fontSize: 14, fontWeight: 600 }}>
                      {new Date(cooperative.subscription_expires_at).toLocaleDateString()}
                    </div>
                  </div>
                )}
              </div>

              {showMemberBar && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                    <span>Active members: {memberCount} of {planMaxMembers}</span>
                    <span>{Math.round(memberPct)}%</span>
                  </div>
                  <div style={{ height: 8, background: '#E5E7EB', borderRadius: 4, overflow: 'hidden' }}>
                    <div style={{
                      height: '100%', width: `${memberPct}%`,
                      background: memberPct >= 90 ? '#F59E0B' : memberPct >= 70 ? '#3B82F6' : '#10B981',
                      borderRadius: 4, transition: 'width .3s ease'
                    }} />
                  </div>
                </div>
              )}

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 16 }}>
                {cooperative?.subscription_plan?.toLowerCase() === 'starter' && (
                  <button
                    type="button"
                    className="btn-lg"
                    onClick={async () => {
                      try {
                        setSaving(true)
                        const res = await createSubscriptionCheckout(cooperativeId, 'growth')
                        if (res.authorization_url) window.location.href = res.authorization_url
                      } catch (err) {
                        setError(err.message)
                        setSaving(false)
                      }
                    }}
                    disabled={saving}
                    style={{ padding: '10px 16px', display: 'inline-flex', alignItems: 'center', gap: 8, background: '#10B981', color: 'white' }}
                  >
                    Upgrade to Growth (GHS 299/mo)
                  </button>
                )}
                {cooperative?.subscription_plan?.toLowerCase() === 'growth' && (
                  <button
                    type="button"
                    className="btn-lg"
                    onClick={async () => {
                      try {
                        setSaving(true)
                        await updateCooperative(cooperativeId, { subscription_plan: 'starter' })
                        setSuccessMsg('Plan downgraded to Starter.')
                        if (onRefresh) onRefresh()
                      } catch (err) {
                        setError(err.message)
                      } finally {
                        setSaving(false)
                      }
                    }}
                    disabled={saving}
                    style={{ padding: '10px 16px', display: 'inline-flex', alignItems: 'center', gap: 8, background: '#6B7280', color: 'white' }}
                  >
                    Downgrade to Starter
                  </button>
                )}
                {cooperative?.subscription_plan?.toLowerCase() === 'solo' && (
                  <button
                    type="button"
                    className="btn-lg"
                    onClick={() => window.location.href = '/pricing'}
                    style={{ padding: '10px 16px', display: 'inline-flex', alignItems: 'center', gap: 8, background: '#3B82F6', color: 'white' }}
                  >
                    View Plans &amp; Pricing
                  </button>
                )}
                {/* Fallback upgrade / renew for any other state */}
                {!['starter', 'growth', 'solo'].includes(cooperative?.subscription_plan?.toLowerCase()) && (
                  <button
                    type="button"
                    className="btn-lg"
                    onClick={async () => {
                      try {
                        setSaving(true)
                        const res = await createSubscriptionCheckout(cooperativeId, 'growth')
                        if (res.authorization_url) window.location.href = res.authorization_url
                      } catch (err) {
                        setError(err.message)
                        setSaving(false)
                      }
                    }}
                    disabled={saving}
                    style={{ padding: '10px 16px', display: 'inline-flex', alignItems: 'center', gap: 8, background: '#10B981', color: 'white' }}
                  >
                    Upgrade / Renew Plan
                  </button>
                )}
              </div>

              {/* Billing history stub */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Billing History</div>
                <div style={{
                  border: '1px dashed var(--border)', borderRadius: 8, padding: 20,
                  textAlign: 'center', color: 'var(--muted)', fontSize: 13
                }}>
                  Billing history coming soon.
                </div>
              </div>
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 12 }}>
              <button type="submit" className="btn-lg" disabled={saving} style={{ padding: '12px 24px', display: 'flex', alignItems: 'center', gap: 8 }}>
                {saving ? <><Loader2 size={16} className="spin" /> Saving...</> : 'Save Settings'}
              </button>
            </div>
          </div>
        </form>
      </div>
      <GovernanceSettings cooperativeId={cooperativeId} />

      {!import.meta.env.PROD && (
        <>
          <section
            className="admin-card"
            aria-labelledby="demo-reset-title"
            style={{ marginTop: 24, border: '1px solid #FCA5A5' }}
          >
            <div style={{ padding: '24px 28px' }}>
              <div id="demo-reset-title" className="serif" style={{ fontWeight: 700, fontSize: 18, color: '#991B1B' }}>
                Demo data danger zone
              </div>
              <p style={{ fontSize: 13, color: 'var(--muted)', lineHeight: 1.6, margin: '8px 0 16px' }}>
                Permanently remove operational demo records while preserving the demo cooperative and admin users.
                This action cannot be undone.
              </p>

              {resetStatus === 'unavailable' ? (
                <div style={{ padding: 14, background: '#F8FAFC', borderRadius: 8, fontSize: 13, lineHeight: 1.6 }}>
                  Demo reset is not available for this workspace. In production, retain records according to your
                  organization&apos;s data policy and use an approved archive or retention process instead of deleting
                  operational history.
                </div>
              ) : (
                <>
                  {resetStatus === 'success' && (
                    <div role="status" style={{ padding: 12, background: '#ECFDF5', color: '#047857', borderRadius: 8, fontSize: 13, marginBottom: 16 }}>
                      Demo data was reset successfully.
                    </div>
                  )}
                  {resetStatus === 'error' && resetError && (
                    <div role="alert" style={{ padding: 12, background: '#FEF2F2', color: '#991B1B', borderRadius: 8, fontSize: 13, marginBottom: 16 }}>
                      {resetError}
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={handleOpenReset}
                    disabled={resetStatus === 'loading'}
                    style={{
                      border: '1px solid #DC2626', background: '#fff', color: '#B91C1C', borderRadius: 8,
                      padding: '10px 16px', fontWeight: 700, cursor: resetStatus === 'loading' ? 'wait' : 'pointer',
                      display: 'inline-flex', alignItems: 'center', gap: 8,
                    }}
                  >
                    {resetStatus === 'loading' ? <><Loader2 size={16} className="spin" /> Checking eligibility...</> : 'Review demo reset'}
                  </button>
                </>
              )}
            </div>
          </section>

          {resetDialogOpen && resetPreview && (
            <DashboardModal
              title="Confirm demo data reset"
              subtitle={`These records will be permanently removed. This preview expires in ${resetPreview.expires_in_seconds} seconds.`}
              onClose={() => setResetDialogOpen(false)}
              label="Confirm demo data reset"
              wide
              closeOnBackdrop={!resetting}
              closeDisabled={resetting}
              as="form"
              bodyProps={{ onSubmit: handleConfirmReset }}
            >
              <div className="dashboard-modal-body">
                <dl className="dashboard-modal-count-list">
                  {Object.entries(RESET_COUNT_LABELS).map(([key, label]) => (
                    <React.Fragment key={key}>
                      <dt>{label}</dt>
                      <dd>{resetPreview[key] ?? 0}</dd>
                    </React.Fragment>
                  ))}
                </dl>

                <ModalField
                  htmlFor="demo-reset-confirmation"
                  label={<>Type <strong>{resetPreview.confirmation_phrase}</strong> to confirm</>}
                >
                  <input
                    ref={resetInputRef}
                    id="demo-reset-confirmation"
                    className="dashboard-modal-input"
                    type="text"
                    value={resetPhrase}
                    onChange={(event) => setResetPhrase(event.target.value)}
                    autoComplete="off"
                    disabled={resetting}
                  />
                </ModalField>

                {resetError && (
                  <div role="alert" className="dashboard-form-error">{resetError}</div>
                )}

                <div className="dashboard-modal-actions">
                  <button
                    type="button"
                    className="dashboard-modal-btn-secondary"
                    onClick={() => setResetDialogOpen(false)}
                    disabled={resetting}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn-lg"
                    disabled={resetting || resetPhrase !== resetPreview.confirmation_phrase}
                    style={{ background: '#B91C1C' }}
                  >
                    {resetting ? <><Loader2 size={16} className="spin" /> Resetting…</> : 'Reset demo data'}
                  </button>
                </div>
              </div>
            </DashboardModal>
          )}
        </>
      )}
      <style>{`@keyframes spin { to { transform: rotate(360deg); } } .spin { animation: spin 1s linear infinite; }`}</style>
    </div>
  )
}
