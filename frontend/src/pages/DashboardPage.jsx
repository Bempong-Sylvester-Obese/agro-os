// src/pages/DashboardPage.jsx
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { DASHBOARD_SECTIONS, dashboardPath } from '../constants/routes'
import { fetchAgroAiDashboard } from '../api/agroAi'
import { fetchCooperative } from '../api/cooperatives'
import { createFarmer, fetchFarmers, resolveCooperativeIdForFarmers } from '../api/farmers'
import Overview from '../components/dashboard/Overview'
import Members from '../components/dashboard/Members'
import Payments from '../components/dashboard/Payments'
import Loans from '../components/dashboard/Loans'
import Production from '../components/dashboard/Production'
import Scores from '../components/dashboard/Scores'
import SMS from '../components/dashboard/SMS'
import USSD from '../components/dashboard/USSD'

const TRUST_SCORE_POLL_MS = 15000

const NAV_ITEMS = [
  { key: 'overview', icon: '📊', label: 'Overview' },
  { key: 'members', icon: '👥', label: 'Members' },
  { key: 'payments', icon: '💳', label: 'Payments' },
  { key: 'loans', icon: '🌾', label: 'Loans' },
  { key: 'production', icon: '🌱', label: 'Production' },
  { key: 'scores', icon: '⭐', label: 'Trust & Agro-AI scores' },
  { key: 'sms', icon: '📱', label: 'SMS broadcasts' },
  { key: 'ussd', icon: '☎️', label: 'USSD activity' },
]

const TITLES = {
  overview: 'Overview',
  members: 'Members',
  payments: 'Payments',
  loans: 'Input loans',
  production: 'Production tracking',
  scores: 'Trust & Agro-AI scores',
  sms: 'SMS broadcasts',
  ussd: 'USSD activity',
  settings: 'Settings',
}

const REGIONS = ['Ashanti', 'Northern', 'Gr. Accra', 'Brong-Ahafo', 'Eastern', 'Volta', 'Western', 'Central', 'Upper East', 'Upper West']

const EMPTY_FORM = { name: '', phone: '', region: 'Ashanti', crop_type: 'Maize' }

function globalSourceLabel(sources) {
  if (sources.some((source) => source === 'loading')) return { label: 'Loading…', tone: 'muted' }
  if (sources.every((source) => source === 'api')) return { label: 'Live API', tone: 'live' }
  if (sources.some((source) => source === 'api')) return { label: 'Mixed · partial live', tone: 'mixed' }
  return { label: 'Demo data', tone: 'demo' }
}

export default function DashboardPage({ user, onLogout }) {
  const { section: sectionParam } = useParams()
  const navigate = useNavigate()
  const section = DASHBOARD_SECTIONS.includes(sectionParam) ? sectionParam : 'overview'
  const [agroAi, setAgroAi] = useState(null)
  const [agroAiState, setAgroAiState] = useState({ loading: true, error: '', source: 'loading' })
  const [dbFarmers, setDbFarmers] = useState(null)
  const [farmersState, setFarmersState] = useState({ loading: true, error: '', source: 'loading' })
  const [cooperative, setCooperative] = useState(null)
  const [coopState, setCoopState] = useState({ loading: true, error: '', source: 'loading' })
  const [modal, setModal] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [formErr, setFormErr] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    if (sectionParam && !DASHBOARD_SECTIONS.includes(sectionParam)) {
      navigate('/dashboard', { replace: true })
    }
  }, [sectionParam, navigate])

  useEffect(() => {
    if (sidebarOpen) {
      document.body.classList.add('no-scroll')
    } else {
      document.body.classList.remove('no-scroll')
    }
    return () => document.body.classList.remove('no-scroll')
  }, [sidebarOpen])

  function selectSection(key) {
    navigate(dashboardPath(key))
    setSidebarOpen(false)
  }

  const loadAgroAi = useCallback(() => {
    setAgroAiState((state) => ({ ...state, loading: true, error: '' }))
    fetchAgroAiDashboard()
      .then((data) => {
        setAgroAi(data)
        setAgroAiState({
          loading: false,
          error: '',
          source: data.source,
        })
      })
      .catch((err) => {
        setAgroAiState({
          loading: false,
          error: err.message || 'Failed to load Agro-AI data',
          source: 'error',
        })
      })
  }, [])

  const loadFarmers = useCallback(() => {
    setFarmersState((state) => ({ ...state, loading: true, error: '' }))
    fetchFarmers()
      .then((data) => {
        setDbFarmers(data)
        setFarmersState({ loading: false, error: '', source: data.source })
      })
      .catch((err) => {
        setFarmersState({
          loading: false,
          error: err.message || 'Failed to load members',
          source: 'error',
        })
      })
  }, [])

  const loadCooperative = useCallback(async () => {
    setCoopState({ loading: true, error: '', source: 'loading' })
    try {
      const coopId = await resolveCooperativeIdForFarmers()
      const data = await fetchCooperative(coopId)
      setCooperative(data.cooperative)
      setCoopState({ loading: false, error: '', source: data.source })
    } catch (err) {
      setCoopState({
        loading: false,
        error: err.message || 'Failed to load cooperative',
        source: 'error',
      })
    }
  }, [])

  useEffect(() => {
    loadAgroAi()
    loadFarmers()
    loadCooperative()
  }, [loadAgroAi, loadFarmers, loadCooperative])

  useEffect(() => {
    const intervalId = setInterval(loadFarmers, TRUST_SCORE_POLL_MS)
    return () => clearInterval(intervalId)
  }, [loadFarmers])

  const globalSource = useMemo(
    () => globalSourceLabel([agroAiState.source, farmersState.source, coopState.source]),
    [agroAiState.source, farmersState.source, coopState.source],
  )

  const dashboardLoading = agroAiState.loading || farmersState.loading

  function openModal() {
    setForm(EMPTY_FORM)
    setFormErr('')
    setModal(true)
  }

  function closeModal() {
    setModal(false)
  }

  function handleField(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }))
  }

  async function handleAddMember(e) {
    e.preventDefault()
    setFormErr('')
    if (!form.name.trim()) {
      setFormErr('Full name is required.')
      return
    }
    if (!form.phone.trim()) {
      setFormErr('Phone number is required.')
      return
    }

    setSubmitting(true)
    try {
      const cooperativeId = cooperative?.id || await resolveCooperativeIdForFarmers()
      await createFarmer({
        name: form.name.trim(),
        phone: form.phone.trim(),
        location: form.region,
        crop_type: form.crop_type,
        cooperative_id: cooperativeId,
      })
      setModal(false)
      loadFarmers()
    } catch (err) {
      setFormErr(err.message || 'Failed to add member.')
    } finally {
      setSubmitting(false)
    }
  }

  const initials = user?.initials ?? '??'
  const approverName = user?.name ?? 'Cooperative Admin'
  const coopName = cooperative?.name || user?.cooperative || 'Cooperative'

  return (
    <>
      {sidebarOpen && (
        <div
          className="admin-backdrop"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      <div className={`admin-shell${sidebarOpen ? ' admin-shell--open' : ''}`}>
        <div className={`admin-side${sidebarOpen ? ' admin-side--open' : ''}`}>
          <div className="admin-side-head">
            <div className="admin-side-title">AgroOS</div>
            <div className="admin-side-sub">{coopState.loading ? 'Loading…' : coopName}</div>
          </div>

          <div className="admin-nav">
            <div className="admin-nav-lbl">Main</div>
            {NAV_ITEMS.map(({ key, icon, label }) => (
              <button
                key={key}
                className={`admin-nav-item${section === key ? ' on' : ''}`}
                onClick={() => selectSection(key)}
              >
                <span className="admin-nav-icon" aria-hidden="true">{icon}</span>
                <span className="admin-nav-text">{label}</span>
              </button>
            ))}

            <div className="admin-nav-lbl">Account</div>
            <button
              className={`admin-nav-item${section === 'settings' ? ' on' : ''}`}
              onClick={() => selectSection('settings')}
            >
              <span className="admin-nav-icon" aria-hidden="true">⚙️</span>
              Settings
            </button>
            <button className="admin-nav-item" onClick={onLogout}>
              <span className="admin-nav-icon" aria-hidden="true">🚪</span>
              Sign out
            </button>
          </div>
        </div>

        <div className="admin-main">
          <div className="admin-topbar">
            <div className="admin-topbar-l">
              <button
                type="button"
                className="admin-menu-btn"
                onClick={() => setSidebarOpen((open) => !open)}
                aria-label={sidebarOpen ? 'Close menu' : 'Open menu'}
                aria-expanded={sidebarOpen}
              >
                ☰
              </button>
              <div className="admin-page-title serif">{TITLES[section]}</div>
            </div>
            <div className="admin-topbar-r">
              <span
                className={`admin-topbar-badge bdg ${globalSource.tone === 'live' ? 'bdg-green' : globalSource.tone === 'demo' ? 'bdg-amber' : 'bdg-amber'}`}
              >
                {globalSource.label}
              </span>
              {section !== 'loans' && (
                <button
                  type="button"
                  className="btn-nav admin-topbar-add"
                  style={{ fontSize: 12, padding: '6px 14px' }}
                  onClick={openModal}
                >
                  + Add member
                </button>
              )}
              <span style={{ fontSize: 20, cursor: 'pointer' }}>🔔</span>
              <div className="admin-avatar">{initials}</div>
            </div>
          </div>

          <div className="admin-content">
            {dashboardLoading && section === 'overview' && (
              <div className="info-banner" style={{ marginBottom: 20 }}>
                Loading dashboard data from the API…
              </div>
            )}

            {section === 'overview' && <Overview agroAi={agroAi} dbFarmers={dbFarmers} />}
            {section === 'members' && (
              <Members
                dbFarmers={dbFarmers}
                agroAi={agroAi}
                onAddMember={openModal}
                loading={farmersState.loading}
                source={farmersState.source}
              />
            )}
            {section === 'payments' && <Payments dbFarmers={dbFarmers} />}
            {section === 'loans' && <Loans approverName={approverName} />}
            {section === 'production' && <Production />}
            {section === 'scores' && <Scores agroAi={agroAi} dbFarmers={dbFarmers} onRecalculated={loadFarmers} />}
            {section === 'sms' && <SMS />}
            {section === 'ussd' && <USSD />}
            {section === 'settings' && (
              <div className="admin-card" style={{ padding: 32 }}>
                <div className="admin-card-head" style={{ marginBottom: 20 }}>
                  <span className="admin-card-title serif">Cooperative profile</span>
                  <span className="admin-card-action">
                    {coopState.source === 'api' ? 'Live API' : 'Demo fallback'}
                  </span>
                </div>
                {coopState.loading ? (
                  <div style={{ color: 'var(--muted)' }}>Loading cooperative profile…</div>
                ) : (
                  <div className="modal-row">
                    <div className="auth-field">
                      <label className="auth-label">Name</label>
                      <div>{cooperative?.name || coopName}</div>
                    </div>
                    <div className="auth-field">
                      <label className="auth-label">Location</label>
                      <div>{cooperative?.location || '—'}</div>
                    </div>
                    <div className="auth-field">
                      <label className="auth-label">Currency</label>
                      <div>{cooperative?.currency || 'GHS'}</div>
                    </div>
                    <div className="auth-field">
                      <label className="auth-label">Moolre wallet</label>
                      <div>{cooperative?.moolre_account_number || 'Not configured'}</div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {modal && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <div>
                <div className="modal-title serif">Add new member</div>
                <div className="modal-sub">Register a farmer to the cooperative CRM.</div>
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
                    placeholder="e.g. +233551234567"
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
                    {REGIONS.map((r) => <option key={r}>{r}</option>)}
                  </select>
                </div>
                <div className="auth-field">
                  <label className="auth-label">Primary crop</label>
                  <input
                    className="auth-input"
                    name="crop_type"
                    placeholder="e.g. Maize"
                    value={form.crop_type}
                    onChange={handleField}
                  />
                </div>
              </div>

              <div className="modal-actions">
                <button type="button" className="btn-out-lg" style={{ fontSize: 13, padding: '10px 22px' }} onClick={closeModal}>
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-lg"
                  style={{ fontSize: 13, padding: '10px 22px' }}
                  disabled={submitting}
                >
                  {submitting ? 'Saving…' : 'Add member →'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}
