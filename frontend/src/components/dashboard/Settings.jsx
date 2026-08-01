// src/components/dashboard/Settings.jsx
import React, { useEffect, useRef, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { confirmDemoReset, previewDemoReset } from '../../api/admin'
import { createSubscriptionCheckout, updateCooperative } from '../../api/cooperatives'
import { formatTransportError } from '../../api/config'
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
    moolre_account_number: ''
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
  const resetInputRef = useRef(null)

  useEffect(() => {
    if (cooperative) {
      setForm({
        name: cooperative.name || '',
        location: cooperative.location || '',
        description: cooperative.description || '',
        default_currency: cooperative.currency || cooperative.default_currency || 'GHS',
        moolre_account_number: cooperative.moolre_account_number || ''
      })
    }
  }, [cooperative])

  useEffect(() => {
    if (!resetDialogOpen) return undefined
    const focusFrame = requestAnimationFrame(() => resetInputRef.current?.focus())
    return () => cancelAnimationFrame(focusFrame)
  }, [resetDialogOpen])

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
      const { default_currency, ...rest } = form
      await updateCooperative(cooperative.id, {
        ...rest,
        currency: default_currency,
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
                  <label htmlFor="settings-moolre-account" style={labelStyle}>Moolre Account Number</label>
                  <input id="settings-moolre-account" style={inputStyle} type="text" value={form.moolre_account_number} onChange={e => setForm({...form, moolre_account_number: e.target.value})} placeholder="e.g. 1089700..." required disabled={saving}/>
                </div>
              </div>
            </div>
            <div style={{ height: 1, background: 'var(--border)', margin: '12px 0' }} />

            {/* Platform Subscription */}
            <div>
              <h3 className="serif" style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Platform Subscription</h3>
              <p style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 16 }}>Manage your cooperative's plan and billing status.</p>
              
              <div className="settings-form-row" style={{ marginBottom: 16, alignItems: 'center' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>Current Plan Status</div>
                  <div style={{ fontWeight: 600, color: cooperative.subscription_status === 'active' ? '#047857' : '#991B1B' }}>
                    {cooperative.subscription_status === 'active' ? 'Active' : 'Inactive / Evaluation'}
                  </div>
                  {cooperative.subscription_expires_at && (
                    <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>
                      Expires: {new Date(cooperative.subscription_expires_at).toLocaleDateString()}
                    </div>
                  )}
                </div>
                <div style={{ flex: 1, textAlign: 'right' }}>
                  <button 
                    type="button" 
                    className="btn-lg" 
                    onClick={async () => {
                      try {
                        setSaving(true)
                        const res = await createSubscriptionCheckout(cooperativeId, 'growth')
                        if (res.authorization_url) {
                          window.location.href = res.authorization_url
                        }
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
      <style>{`@keyframes spin { to { transform: rotate(360deg); } } .spin { animation: spin 1s linear infinite; }`}</style>
    </div>
  )
}
