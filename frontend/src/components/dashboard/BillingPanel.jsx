// src/components/dashboard/BillingPanel.jsx
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Loader2 } from 'lucide-react'
import {
  cancelSubscription,
  createSubscriptionCheckout,
  fetchCooperativeUsage,
  fetchSubscriptionHistory,
  fetchSubscriptionStatus,
  renewSubscription,
  resumeSubscription,
  updateCooperative,
} from '../../api/cooperatives'
import { formatTransportError } from '../../api/config'
import { fetchPlans } from '../../api/plans'
import UsageMeters from './UsageMeters'

const STATUS_COLORS = {
  active: 'green',
  trial: 'blue',
  past_due: 'orange',
  expired: 'red',
  cancelled: 'gray',
}

const STATUS_COPY = {
  trial: (s) => `Growth trial · ${s.days_remaining ?? 0} day${s.days_remaining === 1 ? '' : 's'} left. Pick a plan to keep paid features after the trial.`,
  past_due: (s) => `Payment past due. Paid features stay on for ${s.days_remaining ?? 0} more day${s.days_remaining === 1 ? '' : 's'} of grace — renew to avoid losing them.`,
  expired: () => 'Subscription expired. You are on the free tier; renew or choose a plan to restore paid features.',
  cancelled: (s) => `Cancellation scheduled. Paid features remain until ${fmtDate(s.expires_at)}; resume any time before then.`,
}

function fmtDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleDateString()
}

function fmtMoney(amount, currency = 'GHS') {
  if (amount == null) return '—'
  return `${currency} ${Number(amount).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`
}

const labelStyle = { fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.8px', marginBottom: 4 }
const cellStyle = { flex: '1 1 140px' }
const btn = (bg) => ({
  padding: '10px 16px', display: 'inline-flex', alignItems: 'center', gap: 8, background: bg, color: 'white',
})

/**
 * Billing portal for cooperative admins. Everything is driven by the plan
 * catalogue (`GET /plans`), the lifecycle view (`GET /subscriptions/status`),
 * usage (`GET /cooperatives/{id}/usage`) and intents (`GET /subscriptions/history`).
 * No plan, price, or limit is hardcoded here.
 */
export default function BillingPanel({ cooperative, cooperativeId, onRefresh }) {
  const [plans, setPlans] = useState([])
  const [status, setStatus] = useState(null)
  const [usage, setUsage] = useState(null)
  const [history, setHistory] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [usageError, setUsageError] = useState(null)
  const [busy, setBusy] = useState(null) // action key in flight
  const [actionError, setActionError] = useState(null)
  const [notice, setNotice] = useState(null)
  const [selectedPlan, setSelectedPlan] = useState('')
  const [selectedBand, setSelectedBand] = useState('')
  const [confirmCancel, setConfirmCancel] = useState(false)

  const reload = useCallback(async () => {
    if (!cooperativeId) return
    setLoadError(null)
    const [plansRes, statusRes, usageRes, historyRes] = await Promise.allSettled([
      fetchPlans(),
      fetchSubscriptionStatus(cooperativeId),
      fetchCooperativeUsage(cooperativeId),
      fetchSubscriptionHistory(cooperativeId),
    ])
    if (plansRes.status === 'fulfilled') setPlans(plansRes.value || [])
    if (statusRes.status === 'fulfilled') setStatus(statusRes.value)
    else setLoadError(formatTransportError(statusRes.reason))
    if (usageRes.status === 'fulfilled') { setUsage(usageRes.value); setUsageError(null) }
    else { setUsage(null); setUsageError(formatTransportError(usageRes.reason)) }
    if (historyRes.status === 'fulfilled') setHistory(historyRes.value)
    else setHistory({ items: [], error: formatTransportError(historyRes.reason) })
  }, [cooperativeId])

  useEffect(() => {
    let cancelled = false
    reload().catch((err) => {
      if (!cancelled) setLoadError(formatTransportError(err))
    })
    return () => { cancelled = true }
  }, [reload, cooperative?.subscription_plan, cooperative?.subscription_status])

  const currentPlanKey = (status?.plan_key || cooperative?.subscription_plan || 'starter').toLowerCase()
  const currentStatus = status?.status || cooperative?.subscription_status || 'active'
  const currentPlan = plans.find((p) => p.key === currentPlanKey)
  const track = cooperative?.organization_type === 'solo_farm' ? 'farmer' : 'cooperative'

  // Plans an admin can move to from the portal: same track, purchasable
  // (has a price or bands), not the current plan+band.
  const purchasable = useMemo(
    () => plans.filter((p) => p.track === track && (p.price > 0 || (p.bands || []).some((b) => b.price != null))),
    [plans, track],
  )
  const freePlan = plans.find((p) => p.track === track && !(p.price > 0) && !p.bands)
  const contactPlan = plans.find((p) => p.track === track && !(p.price > 0) && p.key === 'enterprise')

  useEffect(() => {
    if (!selectedPlan && purchasable.length > 0) {
      const preferred = purchasable.find((p) => p.key === currentPlanKey) || purchasable.find((p) => p.featured) || purchasable[0]
      setSelectedPlan(preferred.key)
    }
  }, [purchasable, selectedPlan, currentPlanKey])

  const selected = purchasable.find((p) => p.key === selectedPlan)
  const selectableBands = (selected?.bands || []).filter((b) => b.price != null)
  useEffect(() => {
    if (!selected) return
    if (selectableBands.length === 0) { setSelectedBand(''); return }
    const keep = selectableBands.find((b) => b.key === selectedBand)
    if (!keep) {
      const onRecord = selected.key === currentPlanKey ? selectableBands.find((b) => b.key === status?.band) : null
      setSelectedBand((onRecord || selectableBands[0]).key)
    }
  }, [selected, selectableBands, selectedBand, currentPlanKey, status?.band])

  const selectedBandObj = selectableBands.find((b) => b.key === selectedBand)
  const selectedPrice = selectedBandObj ? selectedBandObj.price : selected?.price
  const isSameAsCurrent = selected && selected.key === currentPlanKey && (selectedBandObj?.key || null) === (status?.band || null)
    && ['active', 'cancelled'].includes(currentStatus)

  const isPaidOnRecord = Boolean(currentPlan && currentPlanKey !== freePlan?.key && currentStatus !== 'trial')

  async function run(key, fn, { redirect = false, successMessage } = {}) {
    setBusy(key)
    setActionError(null)
    setNotice(null)
    try {
      const res = await fn()
      if (redirect && res?.authorization_url) {
        window.location.href = res.authorization_url
        return
      }
      if (successMessage) setNotice(successMessage)
      await reload()
      if (onRefresh) onRefresh()
    } catch (err) {
      setActionError(err.message || 'Action failed')
    } finally {
      setBusy(null)
    }
  }

  const checkout = () => run('checkout', () => createSubscriptionCheckout(cooperativeId, selected.key, selectedBandObj?.key || null), { redirect: true })
  const renew = () => run('renew', () => renewSubscription(cooperativeId), { redirect: true })
  const cancel = (immediately) => run('cancel', () => cancelSubscription(cooperativeId, { immediately }), {
    successMessage: immediately ? 'Subscription cancelled. You are now on the free tier.' : 'Cancellation scheduled for the end of the current period.',
  }).then(() => setConfirmCancel(false))
  const resume = () => run('resume', () => resumeSubscription(cooperativeId), { successMessage: 'Cancellation withdrawn. Your plan will continue.' })
  const downgrade = () => run('downgrade', () => updateCooperative(cooperativeId, { subscription_plan: freePlan.key }), {
    successMessage: `Plan changed to ${freePlan.name}.`,
  })

  const statusCopy = STATUS_COPY[currentStatus]?.(status || {})
  const alertTone = ['past_due', 'expired'].includes(currentStatus)
    ? { bg: '#FFFBEB', border: '#FBBF24', fg: '#92400E' }
    : { bg: '#EFF6FF', border: '#BFDBFE', fg: '#1E3A8A' }

  return (
    <div>
      <h3 className="serif" style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Platform Subscription</h3>
      <p style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 16 }}>Manage your organisation's plan, billing status, and payment history.</p>

      {loadError && (
        <div role="alert" style={{ padding: 12, background: '#FEF2F2', color: '#991B1B', borderRadius: 8, fontSize: 13, marginBottom: 16 }}>
          Billing status could not be loaded ({loadError}). Showing the last known plan.
        </div>
      )}
      {actionError && <div role="alert" style={{ padding: 12, background: '#FEF2F2', color: '#991B1B', borderRadius: 8, fontSize: 13, marginBottom: 16 }}>{actionError}</div>}
      {notice && <div role="status" style={{ padding: 12, background: '#ecfdf5', color: '#047857', borderRadius: 8, fontSize: 13, marginBottom: 16 }}>{notice}</div>}

      {statusCopy && (
        <div role="alert" style={{
          padding: '12px 16px', background: alertTone.bg, border: `1px solid ${alertTone.border}`, color: alertTone.fg,
          borderRadius: 8, fontSize: 13, marginBottom: 16,
        }}>
          {statusCopy}
        </div>
      )}

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, marginBottom: 16, background: 'var(--background)', borderRadius: 10, padding: 16 }}>
        <div style={cellStyle}>
          <div style={labelStyle}>Current Plan</div>
          <div style={{ fontSize: 18, fontWeight: 700 }}>{currentPlan?.name || currentPlanKey}</div>
          {status?.band && currentPlan?.bands && (
            <div style={{ fontSize: 12, color: 'var(--muted)' }}>{currentPlan.bands.find((b) => b.key === status.band)?.label || status.band}</div>
          )}
        </div>
        <div style={cellStyle}>
          <div style={labelStyle}>Status</div>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', display: 'inline-block', background: STATUS_COLORS[currentStatus] || 'gray' }} />
            <span style={{ fontSize: 14, fontWeight: 600, textTransform: 'capitalize' }}>{currentStatus.replace(/_/g, ' ')}</span>
          </div>
        </div>
        {usage?.effective_plan_key && usage.effective_plan_key !== currentPlanKey && (
          <div style={cellStyle}>
            <div style={labelStyle}>{currentStatus === 'trial' ? 'Trial Access' : 'Enforced As'}</div>
            <div style={{ fontSize: 14, fontWeight: 600 }}>{usage.effective_plan_name || usage.effective_plan_key}</div>
          </div>
        )}
        {status?.expires_at && (
          <div style={cellStyle}>
            <div style={labelStyle}>{currentStatus === 'trial' ? 'Trial Ends' : currentStatus === 'cancelled' ? 'Access Until' : 'Renews / Expires'}</div>
            <div style={{ fontSize: 14, fontWeight: 600 }}>{fmtDate(status.expires_at)}</div>
          </div>
        )}
        {currentPlan && (
          <div style={cellStyle}>
            <div style={labelStyle}>Price</div>
            <div style={{ fontSize: 14, fontWeight: 600 }}>
              {status?.band && currentPlan.bands
                ? fmtMoney(currentPlan.bands.find((b) => b.key === status.band)?.price, currentPlan.currency)
                : currentPlan.display_price}
              {currentPlan.price > 0 && <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--muted)' }}> / month</span>}
            </div>
          </div>
        )}
      </div>

      <UsageMeters usage={usage} error={usageError} />

      {/* Plan picker */}
      {purchasable.length > 0 && (
        <div style={{ border: '1px solid var(--border)', borderRadius: 10, padding: 16, marginBottom: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>
            {isPaidOnRecord ? 'Change plan' : 'Choose a plan'}
          </div>
          <div className="settings-form-row" style={{ gap: 12, alignItems: 'flex-end' }}>
            <div style={{ flex: 2 }}>
              <label htmlFor="billing-plan" style={{ fontSize: 13, fontWeight: 600 }}>Plan</label>
              <select
                id="billing-plan"
                value={selectedPlan}
                onChange={(e) => setSelectedPlan(e.target.value)}
                disabled={Boolean(busy)}
                style={{ width: '100%', padding: '10px 12px', border: '1.5px solid var(--border)', borderRadius: 8, fontSize: 14, marginTop: 6, background: '#fff' }}
              >
                {purchasable.map((p) => (
                  <option key={p.key} value={p.key}>{p.name} — {p.display_price}{p.cadence ? ` ${p.cadence}` : ''}</option>
                ))}
              </select>
            </div>
            {selectableBands.length > 0 && (
              <div style={{ flex: 2 }}>
                <label htmlFor="billing-band" style={{ fontSize: 13, fontWeight: 600 }}>Size</label>
                <select
                  id="billing-band"
                  value={selectedBand}
                  onChange={(e) => setSelectedBand(e.target.value)}
                  disabled={Boolean(busy)}
                  style={{ width: '100%', padding: '10px 12px', border: '1.5px solid var(--border)', borderRadius: 8, fontSize: 14, marginTop: 6, background: '#fff' }}
                >
                  {selectableBands.map((b) => (
                    <option key={b.key} value={b.key}>{b.label} — {fmtMoney(b.price, selected.currency)}</option>
                  ))}
                </select>
              </div>
            )}
            <div style={{ flex: 1 }}>
              <button
                type="button"
                className="btn-lg"
                onClick={checkout}
                disabled={Boolean(busy) || !selected || isSameAsCurrent || selectedPrice == null}
                style={btn('#10B981')}
                title={isSameAsCurrent ? 'This is your current plan. Use Renew to extend it.' : undefined}
              >
                {busy === 'checkout' ? <><Loader2 size={16} className="spin" /> Redirecting…</> : (
                  isSameAsCurrent ? 'Current plan' : `Pay ${fmtMoney(selectedPrice, selected?.currency)}`
                )}
              </button>
            </div>
          </div>
          {selected?.features?.length > 0 && (
            <ul style={{ margin: '12px 0 0', paddingLeft: 18, fontSize: 12, color: 'var(--muted)', columns: 2 }}>
              {selected.features.map((f) => <li key={f}>{f}</li>)}
            </ul>
          )}
          {contactPlan && (
            <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 10 }}>
              Need {contactPlan.name}? <a href="/pricing" style={{ fontWeight: 600 }}>{contactPlan.cta}</a>.
            </div>
          )}
        </div>
      )}

      {/* Lifecycle actions */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 16 }}>
        {isPaidOnRecord && ['active', 'past_due', 'expired'].includes(currentStatus) && (
          <button type="button" className="btn-lg" onClick={renew} disabled={Boolean(busy)} style={btn('#3B82F6')}>
            {busy === 'renew' ? <><Loader2 size={16} className="spin" /> Redirecting…</> : `Renew ${currentPlan.name}`}
          </button>
        )}
        {isPaidOnRecord && currentStatus === 'cancelled' && (
          <button type="button" className="btn-lg" onClick={resume} disabled={Boolean(busy)} style={btn('#3B82F6')}>
            {busy === 'resume' ? <><Loader2 size={16} className="spin" /> Resuming…</> : 'Resume subscription'}
          </button>
        )}
        {isPaidOnRecord && ['active', 'past_due'].includes(currentStatus) && !confirmCancel && (
          <button type="button" className="btn-lg" onClick={() => setConfirmCancel(true)} disabled={Boolean(busy)} style={btn('#6B7280')}>
            Cancel subscription
          </button>
        )}
        {freePlan && isPaidOnRecord && currentPlanKey === 'growth' && !confirmCancel && (
          <button type="button" className="btn-lg" onClick={downgrade} disabled={Boolean(busy)} style={btn('#6B7280')}>
            {busy === 'downgrade' ? <><Loader2 size={16} className="spin" /> Saving…</> : `Downgrade to ${freePlan.name}`}
          </button>
        )}
      </div>

      {confirmCancel && (
        <div role="dialog" aria-label="Confirm cancellation" style={{ border: '1px solid #FCA5A5', borderRadius: 10, padding: 16, marginBottom: 16, background: '#FFF7F7' }}>
          <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 6 }}>Cancel {currentPlan?.name}?</div>
          <p style={{ fontSize: 13, color: 'var(--muted)', margin: '0 0 12px', lineHeight: 1.5 }}>
            By default your paid features stay on until {fmtDate(status?.expires_at)} and you move to {freePlan?.name || 'the free tier'} afterwards.
            Cancelling immediately drops to {freePlan?.name || 'the free tier'} now; no refund is issued for the unused period.
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            <button type="button" className="btn-lg" onClick={() => cancel(false)} disabled={Boolean(busy)} style={btn('#B91C1C')}>
              {busy === 'cancel' ? <><Loader2 size={16} className="spin" /> Cancelling…</> : 'Cancel at period end'}
            </button>
            <button type="button" className="btn-lg" onClick={() => cancel(true)} disabled={Boolean(busy)} style={btn('#7F1D1D')}>
              Cancel immediately
            </button>
            <button type="button" className="dashboard-modal-btn-secondary" onClick={() => setConfirmCancel(false)} disabled={Boolean(busy)}>
              Keep my plan
            </button>
          </div>
        </div>
      )}

      {/* Payment history */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
          <div style={{ fontSize: 13, fontWeight: 600 }}>Payment History</div>
          {history?.items?.length > 0 && (
            <div style={{ fontSize: 12, color: 'var(--muted)' }}>Total paid: {fmtMoney(history.total_paid, history.currency)}</div>
          )}
        </div>
        {history?.error ? (
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>Payment history is unavailable right now ({history.error}).</div>
        ) : !history ? (
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>Loading payment history…</div>
        ) : history.items.length === 0 ? (
          <div style={{ border: '1px dashed var(--border)', borderRadius: 8, padding: 20, textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>
            No payments yet. Payments appear here as soon as a checkout is created.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ textAlign: 'left', color: 'var(--muted)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '.6px' }}>
                  <th style={{ padding: '8px 6px' }}>Date</th>
                  <th style={{ padding: '8px 6px' }}>Plan</th>
                  <th style={{ padding: '8px 6px' }}>Type</th>
                  <th style={{ padding: '8px 6px' }}>Amount</th>
                  <th style={{ padding: '8px 6px' }}>Status</th>
                  <th style={{ padding: '8px 6px' }}>Reference</th>
                </tr>
              </thead>
              <tbody>
                {history.items.map((row) => (
                  <tr key={row.id} style={{ borderTop: '1px solid var(--border)' }}>
                    <td style={{ padding: '8px 6px', whiteSpace: 'nowrap' }}>{fmtDate(row.paid_at || row.created_at)}</td>
                    <td style={{ padding: '8px 6px' }}>{row.plan_name}{row.band_label ? <span style={{ color: 'var(--muted)' }}> · {row.band_label}</span> : null}</td>
                    <td style={{ padding: '8px 6px', textTransform: 'capitalize' }}>{row.kind === 'pre_checkout' ? 'Signup' : 'Upgrade / renewal'}</td>
                    <td style={{ padding: '8px 6px', whiteSpace: 'nowrap' }}>{fmtMoney(row.amount, row.currency)}</td>
                    <td style={{ padding: '8px 6px' }}>
                      <span style={{
                        fontSize: 11, padding: '2px 8px', borderRadius: 999, fontWeight: 600,
                        background: row.outcome === 'paid' ? '#ECFDF5' : '#FFFBEB',
                        color: row.outcome === 'paid' ? '#047857' : '#92400E',
                      }}>
                        {row.outcome === 'paid' ? 'Paid' : 'Pending'}
                      </span>
                    </td>
                    <td style={{ padding: '8px 6px', fontFamily: 'monospace', fontSize: 11, color: 'var(--muted)' }}>{row.provider_transaction_id || row.reference}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
