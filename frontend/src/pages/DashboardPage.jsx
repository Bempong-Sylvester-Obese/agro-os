// src/pages/DashboardPage.jsx
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { resolveCooperativeId } from '../utils/auth'
import { DASHBOARD_SECTIONS, dashboardPath } from '../constants/routes'
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
import USSD from '../components/dashboard/USSD'
import DashboardUserMenu from '../components/dashboard/DashboardUserMenu'
import { SidebarCoopSkeleton } from '../components/dashboard/DashboardSkeleton'
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
  ussd:     'USSD activity',
  settings: 'Settings',
}

export default function DashboardPage({ user, onLogout }) {
  const navigate = useNavigate()
  const { section: urlSection } = useParams()
  const sectionFromUrl = urlSection && DASHBOARD_SECTIONS.includes(urlSection) ? urlSection : 'overview'
  const [section, setSection] = useState(sectionFromUrl)
  const [farmers, setFarmers]           = useState([])
  const [transactions, setTransactions] = useState([])
  const [loans, setLoans]               = useState([])
  const [productions, setProductions]   = useState([])
  const [cooperative, setCooperative]   = useState(null)
  const [cooperativeId, setCooperativeId] = useState(null)
  const [loading, setLoading]           = useState(true)

  const loadAll = () => {
    setLoading(true)
    const idHint = resolveCooperativeId(user)

    Promise.all([
      fetchFarmers(idHint).catch(() => []),
      fetchTransactions(idHint).catch(() => []),
      fetchLoans(idHint).catch(() => []),
      fetchProductions(idHint).catch(() => []),
    ]).then(async ([farmersData, txData, loansData, prodsData]) => {
      const resolvedId = resolveCooperativeId(user, farmersData)
      setCooperativeId(resolvedId)
      const coop = resolvedId
        ? await fetchCooperative(resolvedId).catch(() => null)
        : null
      setCooperative(coop)
      setFarmers(farmersData)
      setTransactions(txData)
      setLoans(loansData)
      setProductions(prodsData)
      setLoading(false)
    })
  }

  useEffect(() => { loadAll() }, [user])

  useEffect(() => {
    setSection(sectionFromUrl)
  }, [sectionFromUrl])

  function goToSection(key) {
    setSection(key)
    navigate(dashboardPath(key))
  }

  // Called after a member is added — refreshes only the farmers list
  const handleMemberAdded = () => {
    fetchFarmers(cooperativeId).then(setFarmers).catch(() => {})
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
            {loading ? <SidebarCoopSkeleton /> : (cooperative?.name ?? 'My Cooperative')}
          </div>
        </div>

        <div className="admin-nav">
          <div className="admin-nav-lbl">Main</div>
          {NAV_ITEMS.map(({ key, icon, label }) => (
            <button
              key={key}
              className={`admin-nav-item${section === key ? ' on' : ''}`}
              onClick={() => goToSection(key)}
            >
              {icon} {label}
            </button>
          ))}

          <div className="admin-nav-lbl">Account</div>
          <button
            className={`admin-nav-item${section === 'settings' ? ' on' : ''}`}
            onClick={() => goToSection('settings')}
          >
            <Settings size={18} style={{ marginRight: 8 }} /> Settings
          </button>
        </div>
      </div>

      {/* ── Main panel ── */}
      <div className="admin-main">
        <div className="admin-topbar">
          <div className="admin-page-title serif">{TITLES[section]}</div>
          <DashboardUserMenu user={user} onLogout={onLogout} />
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
              cooperativeId={cooperativeId}
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
              cooperativeId={cooperativeId}
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
              cooperativeId={cooperativeId}
              loading={loading}
              onRefresh={loadAll}
            />
          )}
          {section === 'ussd' && (
            <USSD />
          )}
        </div>
      </div>
    </div>
  )
}
