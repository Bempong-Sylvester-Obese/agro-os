// src/pages/DashboardPage.jsx
import { useEffect, useState } from 'react'
import { fetchAgroAiDashboard } from '../api/agroAi'
import { fetchFarmers } from '../api/farmers'
import Overview from '../components/dashboard/Overview'
import Members from '../components/dashboard/Members'
import Payments from '../components/dashboard/Payments'
import Scores from '../components/dashboard/Scores'
import SMS from '../components/dashboard/SMS'
import Loans    from '../components/dashboard/Loans'
import Scores   from '../components/dashboard/Scores'
import SMS      from '../components/dashboard/SMS'
import { MEMBERS_SEED } from '../data/payments'
import { scoreTier } from '../utils/scores'

const TRUST_SCORE_POLL_MS = 15000

const NAV_ITEMS = [
  { key: 'overview', icon: '📊', label: 'Overview' },
  { key: 'members', icon: '👥', label: 'Members' },
  { key: 'payments', icon: '💳', label: 'Payments' },
  { key: 'scores', icon: '⭐', label: 'Scores' },
  { key: 'sms', icon: '📱', label: 'SMS broadcasts' },
  { key: 'loans',    icon: '🌾', label: 'Loans' },
  { key: 'scores',   icon: '⭐', label: 'Agro-AI scores' },
  { key: 'sms',      icon: '📱', label: 'SMS broadcasts' },
]

const TITLES = {
  overview: 'Overview',
  members: 'Members',
  payments: 'Payments',
  scores: 'Trust & Agro-AI scores',
  sms: 'SMS broadcasts',
  loans:    'Input loans',
  scores:   'Agro-AI credit scores',
  sms:      'SMS broadcasts',
  settings: 'Settings',
}

const REGIONS = ['Ashanti', 'Northern', 'Gr. Accra', 'Brong-Ahafo', 'Eastern', 'Volta', 'Western', 'Central', 'Upper East', 'Upper West']

function nextId(members) {
  const nums = members.map((m) => parseInt(m.id.replace('GH-', ''), 10)).filter(Boolean)
  const max = nums.length ? Math.max(...nums) : 0
  return `GH-${String(max + 1).padStart(4, '0')}`
}

const EMPTY_FORM = { name: '', phone: '', region: 'Ashanti', dues: 'Pending', score: '50' }

export default function DashboardPage({ user, onLogout }) {
  const [section, setSection] = useState('overview')
  const [members, setMembers] = useState(MEMBERS_SEED)
  const [agroAi, setAgroAi] = useState(null)
  const [dbFarmers, setDbFarmers] = useState(null)
  const [modal, setModal] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [formErr, setFormErr] = useState('')

  function openModal() {
    setForm(EMPTY_FORM)
    setFormErr('')
    setModal(true)
  }

  function closeModal() {
    setModal(false)
  }
  const [section, setSection]   = useState('overview')
  const [agroAi, setAgroAi]     = useState(null)
  const [members, setMembers]   = useState(MEMBERS_SEED)
  const [modal, setModal]       = useState(false)
  const [form, setForm]         = useState(EMPTY_FORM)
  const [formErr, setFormErr]   = useState('')

  useEffect(() => {
    let mounted = true

    fetchAgroAiDashboard().then((data) => {
      if (mounted) setAgroAi(data)
    })

    return () => {
      mounted = false
    }
  }, [])

  function openModal()  { setForm(EMPTY_FORM); setFormErr(''); setModal(true) }
  function closeModal() { setModal(false) }

  function handleField(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }))
  }

  function handleAddMember(e) {
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
    const score = parseInt(form.score, 10)
    if (Number.isNaN(score) || score < 0 || score > 100) {
      setFormErr('Score must be between 0 and 100.')
      return
    }

    const newMember = {
      id: nextId(members),
      name: form.name.trim(),
      phone: form.phone.trim(),
      region: form.region,
      dues: form.dues,
      score: String(score),
      tier: scoreTier(score),
    }
    setMembers((prev) => [...prev, newMember])
    setModal(false)
  }

  useEffect(() => {
    let mounted = true

    fetchAgroAiDashboard().then((data) => {
      if (mounted) setAgroAi(data)
    })

    return () => {
      mounted = false
    }
  }, [])
  const initials = user?.initials ?? '??'
  const approverName = user?.name ?? 'Cooperative Admin'

  useEffect(() => {
    let mounted = true

    const loadFarmers = () => {
      fetchFarmers().then((data) => {
        if (mounted) setDbFarmers(data)
      })
    }

    loadFarmers()
    const intervalId = setInterval(loadFarmers, TRUST_SCORE_POLL_MS)

    return () => {
      mounted = false
      clearInterval(intervalId)
    }
  }, [])

  const initials = user?.initials ?? '??'

  return (
    <>
      <div className="admin-shell">
        <div className="admin-side">
          <div className="admin-side-head">
            <div className="admin-side-title">AgroOS</div>
            <div className="admin-side-sub">{user?.cooperative ?? 'Cooperative'}</div>
          </div>

          <div className="admin-nav">
            <div className="admin-nav-lbl">Main</div>
            {NAV_ITEMS.map(({ key, icon, label }) => (
              <button
                key={key}
                className={`admin-nav-item${section === key ? ' on' : ''}`}
                onClick={() => setSection(key)}
              >
                {icon} {label}
              </button>
            ))}

            <div className="admin-nav-lbl">Account</div>
            <button
              className={`admin-nav-item${section === 'settings' ? ' on' : ''}`}
              onClick={() => setSection('settings')}
            >
              ⚙️ Settings
            </button>
            <button className="admin-nav-item" onClick={onLogout}>
              🚪 Sign out
            </button>
          </div>
        </div>

        <div className="admin-main">
          <div className="admin-topbar">
            <div className="admin-page-title serif">{TITLES[section]}</div>
            <div className="admin-topbar-r">
              {section !== 'loans' && (
                <button className="btn-nav" style={{ fontSize: 12, padding: '6px 14px' }} onClick={openModal}>
                  + Add member
                </button>
              )}
              <span style={{ fontSize: 20, cursor: 'pointer' }}>🔔</span>
              <div className="admin-avatar">{initials}</div>
            </div>
          </div>

          <div className="admin-content">
            {section === 'overview' && <Overview agroAi={agroAi} dbFarmers={dbFarmers} />}
            {section === 'members' && (
              <Members
                dbFarmers={dbFarmers}
                agroAi={agroAi}
                onAddMember={openModal}
              />
            )}
            {section === 'payments' && <Payments />}
            {section === 'scores' && <Scores agroAi={agroAi} dbFarmers={dbFarmers} />}
            {section === 'sms' && <SMS />}
            {section === 'settings' && (
            {section === 'overview'  && <Overview agroAi={agroAi} />}
            {section === 'members'   && <Members farmers={agroAi?.farmers} onAddMember={openModal} />}
            {section === 'payments'  && <Payments />}
            {section === 'loans'     && <Loans approverName={approverName} />}
            {section === 'scores'    && <Scores agroAi={agroAi} />}
            {section === 'sms'       && <SMS />}
            {section === 'settings'  && (
              <div className="admin-card" style={{ padding: 48, textAlign: 'center' }}>
                <div style={{ fontSize: 48, marginBottom: 14 }}>⚙️</div>
                <div className="serif" style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>Settings</div>
                <div style={{ fontSize: 14, color: 'var(--muted)' }}>
                  Cooperative profile, team roles, USSD configuration, and Moolre integration settings.
                </div>
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
                <div className="modal-sub">Fill in the farmer&apos;s details to register them to the cooperative.</div>
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
                    {REGIONS.map((r) => <option key={r}>{r}</option>)}
                  </select>
                </div>
                <div className="auth-field">
                  <label className="auth-label">Dues status</label>
                  <select className="auth-input auth-select" name="dues" value={form.dues} onChange={handleField}>
                    <option>Paid</option>
                    <option>Pending</option>
                    <option>Overdue</option>
                  </select>
                </div>
              </div>

              <div className="auth-field">
                <label className="auth-label">
                  Initial Trust Score <span style={{ color: 'var(--muted)', fontWeight: 400 }}>(0 – 100)</span>
                </label>
                <div className="score-slider-wrap">
                  <input
                    type="range"
                    min="0"
                    max="100"
                    name="score"
                    value={form.score}
                    onChange={handleField}
                    className="score-slider"
                  />
                  <span className={`score-bdg ${scoreTier(form.score)}`} style={{ minWidth: 40, fontSize: 14 }}>
                    {form.score}
                  </span>
                </div>
              </div>

              <div className="modal-actions">
                <button type="button" className="btn-out-lg" style={{ fontSize: 13, padding: '10px 22px' }} onClick={closeModal}>
                  Cancel
                </button>
                <button type="submit" className="btn-lg" style={{ fontSize: 13, padding: '10px 22px' }}>
                  Add member →
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}
