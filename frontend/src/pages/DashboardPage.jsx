// src/pages/DashboardPage.jsx
import { useEffect, useState } from 'react'
import { fetchAgroAiDashboard } from '../api/agroAi'
import Overview from '../components/dashboard/Overview'
import Members  from '../components/dashboard/Members'
import Payments from '../components/dashboard/Payments'
import Scores   from '../components/dashboard/Scores'
import SMS      from '../components/dashboard/SMS'

const NAV_ITEMS = [
  { key: 'overview', icon: '📊', label: 'Overview' },
  { key: 'members',  icon: '👥', label: 'Members' },
  { key: 'payments', icon: '💳', label: 'Payments' },
  { key: 'scores',   icon: '⭐', label: 'Agro-AI scores' },
  { key: 'sms',      icon: '📱', label: 'SMS broadcasts' },
]

const TITLES = {
  overview: 'Overview',
  members:  'Members',
  payments: 'Payments',
  scores:   'Agro-AI credit scores',
  sms:      'SMS broadcasts',
  settings: 'Settings',
}

export default function DashboardPage() {
  const [section, setSection] = useState('overview')
  const [agroAi, setAgroAi] = useState(null)

  useEffect(() => {
    let mounted = true

    fetchAgroAiDashboard().then((data) => {
      if (mounted) setAgroAi(data)
    })

    return () => {
      mounted = false
    }
  }, [])

  return (
    <div className="admin-shell">
      {/* ── Sidebar ── */}
      <div className="admin-side">
        <div className="admin-side-head">
          <div className="admin-side-title">AgroOS</div>
          <div className="admin-side-sub">Ashanti Farmers Co-op</div>
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
        </div>
      </div>

      {/* ── Main panel ── */}
      <div className="admin-main">
        <div className="admin-topbar">
          <div className="admin-page-title serif">{TITLES[section]}</div>
          <div className="admin-topbar-r">
            <button className="btn-nav" style={{ fontSize: 12, padding: '6px 14px' }}>+ Add member</button>
            <span style={{ fontSize: 20, cursor: 'pointer' }}>🔔</span>
            <div className="admin-avatar">KA</div>
          </div>
        </div>

        <div className="admin-content">
          {section === 'overview'  && <Overview agroAi={agroAi} />}
          {section === 'members'   && <Members farmers={agroAi?.farmers} />}
          {section === 'payments'  && <Payments />}
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
  )
}
