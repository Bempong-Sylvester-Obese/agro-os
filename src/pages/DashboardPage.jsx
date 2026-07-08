// src/pages/DashboardPage.jsx
import { useState, useRef, useEffect, useCallback } from 'react'
import Overview from '../components/dashboard/Overview'
import Members  from '../components/dashboard/Members'
import Payments from '../components/dashboard/Payments'
import Scores   from '../components/dashboard/Scores'
import SMS      from '../components/dashboard/SMS'
import { farmersApi, transactionsApi } from '../lib/api'

// Using Phosphor Icons via CDN (loaded in index.html)
// ph-chart-bar, ph-users, ph-credit-card, ph-star, ph-chat, ph-gear, ph-sign-out

const NAV_ITEMS = [
  { key: 'overview', phIcon: 'ph-chart-bar',    label: 'Overview' },
  { key: 'members',  phIcon: 'ph-users',         label: 'Members' },
  { key: 'payments', phIcon: 'ph-credit-card',   label: 'Payments' },
  { key: 'scores',   phIcon: 'ph-star',          label: 'AgroCredit scores' },
  { key: 'sms',      phIcon: 'ph-chat',          label: 'SMS broadcasts' },
]

const TITLES = {
  overview: 'Overview',
  members:  'Members',
  payments: 'Payments',
  scores:   'AgroCredit scores',
  sms:      'SMS broadcasts',
  settings: 'Settings',
}

const REGIONS = ['Ashanti', 'Northern', 'Gr. Accra', 'Brong-Ahafo', 'Eastern', 'Volta', 'Western', 'Central', 'Upper East', 'Upper West']

function scoreTier(score) {
  const n = parseInt(score, 10)
  if (n >= 80) return 'sh'
  if (n >= 60) return 'sm'
  return 'sl'
}

function formatMemberId(numericId) {
  return `GH-${String(numericId).padStart(4, '0')}`
}

/**
 * Turn a Farmer record from the API into the shape the dashboard UI expects,
 * optionally attaching a dues status computed from that farmer's most
 * recent dues transaction.
 */
function toMember(farmer, duesByFarmerId) {
  const score = Math.round(farmer.trust_score ?? 0)
  return {
    farmerId: farmer.id,
    id: formatMemberId(farmer.id),
    name: farmer.name,
    phone: farmer.phone,
    region: farmer.location || '—',
    dues: duesByFarmerId?.[farmer.id] ?? 'Pending',
    score: String(score),
    tier: scoreTier(score),
  }
}

const EMPTY_FORM = { name: '', phone: '', region: 'Ashanti', crop_type: '', acreage: '' }

// Profile dropdown menu
function ProfileDropdown({ user, onNavigate, onLogout, onClose }) {
  const ref = useRef()
  useEffect(() => {
    function handler(e) { if (ref.current && !ref.current.contains(e.target)) onClose() }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [onClose])

  return (
    <div ref={ref} style={{
      position: 'absolute', top: 'calc(100% + 8px)', right: 0,
      background: '#fff', border: '1px solid var(--border)',
      borderRadius: 12, boxShadow: '0 8px 32px rgba(0,0,0,.14)',
      minWidth: 220, zIndex: 300,
      animation: 'modal-in 0.15s ease',
    }}>
      {/* User info */}
      <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', marginBottom: 2 }}>{user?.name ?? 'User'}</div>
        <div style={{ fontSize: 11, color: 'var(--muted)' }}>{user?.email ?? ''}</div>
        <div style={{ marginTop: 6 }}>
          <span style={{
            background: 'rgba(82,183,136,.15)', color: 'var(--g)',
            fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 99, letterSpacing: '.04em',
          }}>{user?.role ?? 'Member'}</span>
        </div>
      </div>

      {/* Menu items */}
      {[
        { icon: 'ph-user-circle', label: 'My profile',     action: () => { onNavigate('settings'); onClose() } },
        { icon: 'ph-gear',        label: 'Settings',       action: () => { onNavigate('settings'); onClose() } },
        { icon: 'ph-users',       label: 'Team members',   action: () => { onNavigate('members');  onClose() } },
        { icon: 'ph-credit-card', label: 'Billing & plan', action: () => { onNavigate('settings'); onClose() } },
        { icon: 'ph-question',    label: 'Help & support',  action: onClose },
      ].map(({ icon, label, action }) => (
        <button
          key={label}
          onClick={action}
          style={{
            display: 'flex', alignItems: 'center', gap: 10,
            width: '100%', padding: '10px 16px', background: 'none',
            border: 'none', cursor: 'pointer', fontSize: 13,
            color: 'var(--text)', textAlign: 'left',
            transition: 'background 0.1s',
          }}
          onMouseEnter={e => e.currentTarget.style.background = 'var(--sage)'}
          onMouseLeave={e => e.currentTarget.style.background = 'none'}
        >
          <i className={`${icon} ph-bold`} style={{ fontSize: 15, color: 'var(--g)' }} />
          {label}
        </button>
      ))}

      <div style={{ borderTop: '1px solid var(--border)', marginTop: 4 }}>
        <button
          onClick={() => { onLogout(); onClose() }}
          style={{
            display: 'flex', alignItems: 'center', gap: 10,
            width: '100%', padding: '10px 16px', background: 'none',
            border: 'none', cursor: 'pointer', fontSize: 13,
            color: '#c0392b', textAlign: 'left',
            transition: 'background 0.1s',
          }}
          onMouseEnter={e => e.currentTarget.style.background = 'rgba(220,80,80,.06)'}
          onMouseLeave={e => e.currentTarget.style.background = 'none'}
        >
          <i className="ph-sign-out ph-bold" style={{ fontSize: 15 }} />
          Sign out
        </button>
      </div>
    </div>
  )
}

export default function DashboardPage({ user, onLogout }) {
  const [section, setSection]     = useState('overview')
  const [members, setMembers]     = useState([])
  const [loading, setLoading]     = useState(true)
  const [loadError, setLoadError] = useState('')
  const [modal, setModal]         = useState(false)
  const [form, setForm]           = useState(EMPTY_FORM)
  const [formErr, setFormErr]     = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)

  const cooperativeId = user?.cooperative_id

  const loadMembers = useCallback(async () => {
    if (!cooperativeId) return
    setLoading(true)
    setLoadError('')
    try {
      const farmers = await farmersApi.list(cooperativeId)

      // Pull dues transactions so we can show a real Paid/Pending/Overdue badge.
      // (Best-effort — if this fails we still show members with default status.)
      let duesByFarmerId = {}
      try {
        const dues = await transactionsApi.list({ transaction_type: 'dues', limit: 500 })
        const byFarmer = {}
        for (const tx of dues) {
          const existing = byFarmer[tx.farmer_id]
          if (!existing || new Date(tx.created_at) > new Date(existing.created_at)) {
            byFarmer[tx.farmer_id] = tx
          }
        }
        duesByFarmerId = Object.fromEntries(
          Object.entries(byFarmer).map(([farmerId, tx]) => [
            farmerId,
            tx.status === 'completed' ? 'Paid' : tx.status === 'failed' ? 'Overdue' : 'Pending',
          ])
        )
      } catch { /* non-fatal — dues badges just fall back to 'Pending' */ }

      setMembers(farmers.map(f => toMember(f, duesByFarmerId)))
    } catch (err) {
      setLoadError(err.message || 'Could not load members from the AgroOS API.')
    } finally {
      setLoading(false)
    }
  }, [cooperativeId])

  useEffect(() => { loadMembers() }, [loadMembers])

  function openModal()  { setForm(EMPTY_FORM); setFormErr(''); setModal(true) }
  function closeModal() { setModal(false) }

  function handleField(e) {
    setForm(f => ({ ...f, [e.target.name]: e.target.value }))
  }

  async function handleAddMember(e) {
    e.preventDefault()
    setFormErr('')
    if (!form.name.trim())  { setFormErr('Full name is required.'); return }
    if (!form.phone.trim()) { setFormErr('Phone number is required.'); return }

    setSubmitting(true)
    try {
      await farmersApi.create({
        name: form.name.trim(),
        phone: form.phone.trim(),
        location: form.region,
        crop_type: form.crop_type.trim() || null,
        acreage: form.acreage ? parseFloat(form.acreage) : null,
        cooperative_id: cooperativeId,
      })
      setModal(false)
      await loadMembers() // re-pull the full, authoritative list from the DB
    } catch (err) {
      setFormErr(err.message || 'Could not add this member. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const initials = user?.initials ?? '??'

  return (
    <>
      <div className="admin-shell">
        {/* ── Sidebar ── */}
        <div className="admin-side">
          <div className="admin-side-head">
            <div className="admin-side-title">AgroOS</div>
            <div className="admin-side-sub">{user?.cooperative_name ?? 'Cooperative'}</div>
          </div>

          <div className="admin-nav">
            <div className="admin-nav-lbl">Main</div>
            {NAV_ITEMS.map(({ key, phIcon, label }) => (
              <button
                key={key}
                className={`admin-nav-item${section === key ? ' on' : ''}`}
                onClick={() => setSection(key)}
              >
                <i className={`${phIcon} ph-bold`} style={{ fontSize: 16 }} />
                {label}
              </button>
            ))}

            <div className="admin-nav-lbl">Account</div>
            <button
              className={`admin-nav-item${section === 'settings' ? ' on' : ''}`}
              onClick={() => setSection('settings')}
            >
              <i className="ph-gear ph-bold" style={{ fontSize: 16 }} />
              Settings
            </button>
            <button className="admin-nav-item" onClick={onLogout}>
              <i className="ph-sign-out ph-bold" style={{ fontSize: 16 }} />
              Sign out
            </button>
          </div>
        </div>

        {/* ── Main panel ── */}
        <div className="admin-main">
          <div className="admin-topbar">
            <div className="admin-page-title serif">{TITLES[section]}</div>
            <div className="admin-topbar-r">
              <button className="btn-nav" style={{ fontSize: 12, padding: '6px 14px' }} onClick={openModal}>
                + Add member
              </button>
              {/* Avatar with dropdown */}
              <div style={{ position: 'relative' }}>
                <div
                  className="admin-avatar"
                  onClick={() => setProfileOpen(p => !p)}
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                  title="Profile menu"
                >
                  {initials}
                </div>
                {profileOpen && (
                  <ProfileDropdown
                    user={user}
                    onNavigate={setSection}
                    onLogout={onLogout}
                    onClose={() => setProfileOpen(false)}
                  />
                )}
              </div>
            </div>
          </div>

          <div className="admin-content">
            {loadError && (
              <div className="auth-error" style={{ marginBottom: 16 }}>
                {loadError} <button className="auth-switch-btn" onClick={loadMembers}>Retry</button>
              </div>
            )}
            {loading && !loadError && (
              <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--muted)' }}>Loading live data from AgroOS API…</div>
            )}
            {!loading && (
              <>
                {section === 'overview'  && <Overview members={members} />}
                {section === 'members'   && <Members  members={members} onAddMember={openModal} />}
                {section === 'payments'  && <Payments members={members} />}
                {section === 'scores'    && <Scores members={members} onRecalculated={loadMembers} />}
                {section === 'sms'       && <SMS cooperativeId={cooperativeId} sentBy={user?.name} />}
                {section === 'settings'  && (
                  <div>
                    {/* Profile section */}
                    <div className="admin-card" style={{ marginBottom: 20, padding: 32 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 24 }}>
                        <div style={{
                          width: 64, height: 64, borderRadius: '50%',
                          background: 'var(--g)', color: '#fff',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          fontSize: 22, fontWeight: 700,
                        }}>{initials}</div>
                        <div>
                          <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text)', marginBottom: 4 }}>{user?.name ?? 'User'}</div>
                          <div style={{ fontSize: 13, color: 'var(--muted)' }}>{user?.email ?? ''}</div>
                          <span style={{
                            background: 'rgba(82,183,136,.15)', color: 'var(--g)',
                            fontSize: 11, fontWeight: 700, padding: '2px 10px', borderRadius: 99, display: 'inline-block', marginTop: 6,
                          }}>{user?.role ?? 'Member'}</span>
                        </div>
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                        {[
                          ['Full name', user?.name ?? '—'],
                          ['Email', user?.email ?? '—'],
                          ['Role', user?.role ?? '—'],
                          ['Cooperative', user?.cooperative_name ?? '—'],
                        ].map(([label, val]) => (
                          <div key={label}>
                            <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.04em', marginBottom: 4 }}>{label}</div>
                            <div style={{ fontSize: 14, color: 'var(--text)' }}>{val}</div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Settings cards */}
                    {[
                      ['⚙️', 'Cooperative settings', 'Cooperative profile, branding, and USSD configuration.'],
                      ['👥', 'Team & roles', 'Manage team members, invite colleagues, and set permission levels.'],
                      ['💳', 'Billing & plan', 'View your current plan, upgrade, and manage payment methods.'],
                      ['🔗', 'Moolre integration', 'MoMo collection settings, USSD menu, and API credentials.'],
                    ].map(([icon, title, desc]) => (
                      <div key={title} className="admin-card" style={{ padding: 20, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 16, cursor: 'pointer' }}
                        onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--g)'}
                        onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}
                      >
                        <div style={{ fontSize: 28 }}>{icon}</div>
                        <div>
                          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 2 }}>{title}</div>
                          <div style={{ fontSize: 12, color: 'var(--muted)' }}>{desc}</div>
                        </div>
                        <i className="ph-caret-right ph-bold" style={{ marginLeft: 'auto', color: 'var(--muted)', fontSize: 16 }} />
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* ── Add Member Modal ── */}
      {modal && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-head">
              <div>
                <div className="modal-title serif">Add new member</div>
                <div className="modal-sub">Fill in the farmer's details to register them to the cooperative.</div>
              </div>
              <button className="modal-close" onClick={closeModal}>✕</button>
            </div>

            {formErr && <div className="auth-error" style={{ margin: '0 0 16px' }}>{formErr}</div>}

            <form onSubmit={handleAddMember} className="modal-form">
              <div className="modal-row">
                <div className="auth-field">
                  <label className="auth-label">Full name *</label>
                  <input
                    className="auth-input"
                    name="name"
                    placeholder="e.g. Kwame Boateng"
                    value={form.name}
                    onChange={handleField}
                    required
                  />
                </div>
                <div className="auth-field">
                  <label className="auth-label">Phone number *</label>
                  <input
                    className="auth-input"
                    name="phone"
                    placeholder="e.g. 024 xxx xxxx"
                    value={form.phone}
                    onChange={handleField}
                    required
                  />
                </div>
              </div>

              <div className="modal-row">
                <div className="auth-field">
                  <label className="auth-label">Region</label>
                  <select className="auth-input auth-select" name="region" value={form.region} onChange={handleField}>
                    {REGIONS.map(r => <option key={r}>{r}</option>)}
                  </select>
                </div>
                <div className="auth-field">
                  <label className="auth-label">Crop type</label>
                  <input
                    className="auth-input"
                    name="crop_type"
                    placeholder="e.g. Cocoa"
                    value={form.crop_type}
                    onChange={handleField}
                  />
                </div>
              </div>

              <div className="auth-field">
                <label className="auth-label">Acreage <span style={{ color: 'var(--muted)', fontWeight: 400 }}>(optional)</span></label>
                <input
                  className="auth-input"
                  name="acreage"
                  type="number"
                  step="0.1"
                  min="0"
                  placeholder="e.g. 3.5"
                  value={form.acreage}
                  onChange={handleField}
                />
              </div>

              <div style={{ fontSize: 11, color: 'var(--muted)', margin: '-4px 0 4px' }}>
                A new member starts with a default AgroCredit score of 0 until their first
                trust score calculation, once they have payment, production, or attendance history.
              </div>

              <div className="modal-actions">
                <button type="button" className="btn-out-lg" style={{ fontSize: 13, padding: '10px 22px' }} onClick={closeModal} disabled={submitting}>
                  Cancel
                </button>
                <button type="submit" className="btn-lg" style={{ fontSize: 13, padding: '10px 22px' }} disabled={submitting}>
                  {submitting ? 'Adding…' : 'Add member →'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}
