// src/pages/DashboardPage.jsx
import { useEffect, useState } from 'react'
import { getAuthInfo } from '../utils/auth'
import { fetchFarmers } from '../api/farmers'
import { fetchCooperative } from '../api/cooperatives'
import { fetchTransactions } from '../api/transactions'
import { fetchLoans } from '../api/loans'
import { fetchProductions } from '../api/production'
import Overview from '../components/dashboard/Overview'
import Members  from '../components/dashboard/Members'
import Payments from '../components/dashboard/Payments'
import Scores   from '../components/dashboard/Scores'
import SMS      from '../components/dashboard/SMS'
import Loans    from '../components/dashboard/Loans'
import Production from '../components/dashboard/Production'
import SettingsView from '../components/dashboard/Settings'
import DashboardUserMenu from '../components/dashboard/DashboardUserMenu'
import { BarChart3, Users, CreditCard, Star, MessageSquare, Settings, Sprout, Banknote, Tractor } from 'lucide-react'

const NAV_ITEMS = [
  { key: 'overview', icon: <BarChart3 size={18} />, label: 'Overview' },
  { key: 'members',  icon: <Users size={18} />,    label: 'Members' },
  { key: 'payments', icon: <CreditCard size={18} />, label: 'Payments' },
  { key: 'loans',    icon: <Banknote size={18} />,  label: 'Loans' },
  { key: 'production', icon: <Tractor size={18} />, label: 'Production' },
  { key: 'scores',   icon: <Star size={18} />,      label: 'Agro-AI scores' },
  { key: 'sms',      icon: <MessageSquare size={18} />, label: 'SMS broadcasts' },
]

const TITLES = {
  overview: 'Overview',
  members:  'Members',
  payments: 'Payments',
  loans:    'Loans',
  production: 'Production',
  scores:   'Agro-AI credit scores',
  sms:      'SMS broadcasts',
  settings: 'Settings',
}

export default function DashboardPage({ user, onLogout }) {
  const [section, setSection]           = useState('overview')
  const [farmers, setFarmers]           = useState([])
  const [transactions, setTransactions] = useState([])
  const [loans, setLoans]               = useState([])
  const [productions, setProductions]   = useState([])
  const [cooperative, setCooperative]   = useState(null)
  const [loading, setLoading]           = useState(true)

  // Decode JWT once — cooperative_id scopes all queries
  const { cooperative_id } = getAuthInfo()

  const loadAll = () => {
    setLoading(true)
    Promise.all([
      fetchCooperative(cooperative_id).catch(() => null),
      fetchFarmers(cooperative_id).catch(() => []),
      fetchTransactions(cooperative_id).catch(() => []),
      fetchLoans(cooperative_id).catch(() => []),
      fetchProductions(cooperative_id).catch(() => []),
    ]).then(([coop, farmersData, txData, loansData, prodsData]) => {
      setCooperative(coop)
      setFarmers(farmersData)
      setTransactions(txData)
      setLoans(loansData)
      setProductions(prodsData)
      setLoading(false)
    })
  }

  useEffect(() => { loadAll() }, [cooperative_id])

  // Called after a member is added — refreshes only the farmers list
  const handleMemberAdded = () => {
    fetchFarmers(cooperative_id).then(setFarmers).catch(() => {})
  }

  return (
    <div className="admin-shell">
      {/* ── Sidebar ── */}
      <div className="admin-side">
        <div className="admin-side-head">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
            <Sprout size={16} color="var(--gl)" />
            <div className="admin-side-title">AgroOS</div>
          </div>
          <div className="admin-side-sub">
            {loading ? '...' : (cooperative?.name ?? 'My Cooperative')}
          </div>
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
            <Settings size={18} style={{ marginRight: 8 }} /> Settings
          </button>
        </div>
      </div>

      {/* ── Main panel ── */}
      <div className="admin-main">
        <div className="admin-topbar">
          <div className="admin-page-title serif">{TITLES[section]}</div>
          <DashboardUserMenu
            user={user}
            onLogout={onLogout}
            onOpenSettings={() => setSection('settings')}
          />
        </div>

        <div className="admin-content">
          {section === 'overview' && (
            <Overview
              farmers={farmers}
              transactions={transactions}
              loading={loading}
            />
          )}
          {section === 'members' && (
            <Members
              farmers={farmers}
              cooperativeId={cooperative_id}
              onMemberAdded={handleMemberAdded}
              loading={loading}
            />
          )}
          {section === 'payments' && (
            <Payments
              farmers={farmers}
              transactions={transactions}
              loading={loading}
              onRefresh={loadAll}
            />
          )}
          {section === 'scores' && (
            <Scores farmers={farmers} loading={loading} />
          )}
          {section === 'sms' && (
            <SMS
              cooperativeId={cooperative_id}
              memberCount={farmers.length}
            />
          )}
          {section === 'loans' && (
            <Loans
              farmers={farmers}
              loans={loans}
              loading={loading}
              onRefresh={loadAll}
            />
          )}
          {section === 'production' && (
            <Production
              farmers={farmers}
              productions={productions}
              loading={loading}
              onRefresh={loadAll}
            />
          )}
          {section === 'settings' && (
            <SettingsView
              cooperative={cooperative}
              onRefresh={loadAll}
            />
          )}
        </div>
      </div>
    </div>
  )
}
