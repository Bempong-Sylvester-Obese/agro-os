// src/pages/DashboardPage.jsx
import { useEffect, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { Navigate, useNavigate, useParams } from 'react-router-dom'
import { resolveCooperativeId } from '../utils/auth'
import { formatTransportError } from '../api/config'
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
import Activity from '../components/dashboard/Activity'
import DashboardUserMenu from '../components/dashboard/DashboardUserMenu'
import { SidebarCoopSkeleton } from '../components/dashboard/DashboardSkeleton'
import { BarChart3, Users, CreditCard, Star, MessageSquare, Settings, Sprout, Banknote, Tractor, Phone, RefreshCw, ClipboardList } from 'lucide-react'

const NAV_GROUPS = [
  {
    label: 'Operations',
    items: [
      { key: 'overview', icon: <BarChart3 size={18} />, label: 'Overview' },
      { key: 'members', icon: <Users size={18} />, label: 'Members' },
      { key: 'production', icon: <Tractor size={18} />, label: 'Production' },
      { key: 'scores', icon: <Star size={18} />, label: 'Agro-AI scores' },
    ],
  },
  {
    label: 'Finance',
    items: [
      { key: 'payments', icon: <CreditCard size={18} />, label: 'Payments' },
      { key: 'loans', icon: <Banknote size={18} />, label: 'Loans' },
    ],
  },
  {
    label: 'Communications',
    items: [
      { key: 'sms', icon: <MessageSquare size={18} />, label: 'SMS broadcasts' },
      { key: 'ussd', icon: <Phone size={18} />, label: 'USSD activity' },
    ],
  },
  {
    label: 'Governance',
    items: [
      { key: 'activity', icon: <ClipboardList size={18} />, label: 'Activity log' },
    ],
  },
]
const NAV_ITEMS = NAV_GROUPS.flatMap((group) => group.items)

const TITLES = {
  overview: 'Overview',
  members:  'Members',
  payments: 'Payments',
  loans:    'Loans',
  production: 'Production',
  scores:   'Agro-AI credit scores',
  sms:      'SMS broadcasts',
  ussd:     'USSD activity',
  activity: 'Administrator activity',
  settings: 'Settings',
}

const SECTION_RESOURCES = {
  overview: ['farmers', 'transactions'],
  members: ['farmers'],
  payments: ['farmers', 'transactions'],
  loans: ['farmers', 'loans'],
  production: ['farmers', 'productions'],
  scores: ['farmers'],
  settings: ['cooperative'],
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
  const [cooperativeId, setCooperativeId] = useState(() => resolveCooperativeId(user))
  const [loading, setLoading]           = useState(true)
  const [resourceErrors, setResourceErrors] = useState({})
  const [lastUpdated, setLastUpdated] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const reduceMotion = useReducedMotion()

  const loadAll = async () => {
    if (lastUpdated) setRefreshing(true)
    else setLoading(true)
    const idHint = resolveCooperativeId(user)
    const resourceNames = ['farmers', 'transactions', 'loans', 'productions']
    const results = await Promise.allSettled([
      fetchFarmers(idHint),
      fetchTransactions(idHint),
      fetchLoans(idHint),
      fetchProductions(idHint),
    ])
    const [farmersR, txR, loansR, prodsR] = results
    const errors = {}
    results.forEach((result, index) => {
      if (result.status === 'rejected') {
        errors[resourceNames[index]] = formatTransportError(result.reason)
      }
    })
    if (farmersR.status === 'fulfilled') setFarmers(farmersR.value)
    if (txR.status === 'fulfilled') setTransactions(txR.value)
    if (loansR.status === 'fulfilled') setLoans(loansR.value)
    if (prodsR.status === 'fulfilled') setProductions(prodsR.value)

    const farmersData = farmersR.status === 'fulfilled' ? farmersR.value : farmers
    const resolvedId = resolveCooperativeId(user, farmersData)
    setCooperativeId(resolvedId)
    if (resolvedId) {
      try {
        setCooperative(await fetchCooperative(resolvedId))
      } catch (error) {
        errors.cooperative = formatTransportError(error)
      }
    }
    setResourceErrors(errors)
    if (results.some((result) => result.status === 'fulfilled')) setLastUpdated(new Date())
    setLoading(false)
    setRefreshing(false)
  }

  const refreshLoans = async () => {
    const idHint = cooperativeId ?? resolveCooperativeId(user)
    try {
      setLoans(await fetchLoans(idHint))
      setResourceErrors((current) => {
        const next = { ...current }
        delete next.loans
        return next
      })
      setLastUpdated(new Date())
    } catch (error) {
      setResourceErrors((current) => ({
        ...current,
        loans: formatTransportError(error),
      }))
    }
  }

  useEffect(() => {
    setCooperativeId((prev) => prev ?? resolveCooperativeId(user))
  }, [user])

  useEffect(() => { loadAll() }, [user])

  useEffect(() => {
    setSection(sectionFromUrl)
  }, [sectionFromUrl])

  function goToSection(key) {
    setSection(key)
    navigate(dashboardPath(key))
  }

  const sectionErrors = (SECTION_RESOURCES[section] || [])
    .filter((resource) => resourceErrors[resource])
    .map((resource) => `${resource}: ${resourceErrors[resource]}`)
  const hasStaleSectionData = sectionErrors.length > 0

  // Called after a member is added — refreshes only the farmers list
  const handleMemberAdded = () => {
    fetchFarmers(cooperativeId).then(setFarmers).catch(() => {})
  }

  if (urlSection && !DASHBOARD_SECTIONS.includes(urlSection)) {
    return <Navigate to={dashboardPath('overview')} replace />
  }

  return (
    <div className="admin-shell">
      {/* ── Sidebar ── */}
      <div className="admin-side">
        <div className="admin-side-head">
          <div className="admin-side-brand">
            <div className="admin-side-mark">
              <Sprout size={18} aria-hidden="true" />
            </div>
            <div className="admin-side-title">AgroOS</div>
          </div>
          <div className="admin-side-sub">
            <span className="admin-side-sub-label">Cooperative</span>
            <span className="admin-side-sub-name" title={cooperative?.name}>
              {loading ? <SidebarCoopSkeleton /> : (cooperative?.name ?? 'My Cooperative')}
            </span>
          </div>
        </div>
        <label className="admin-mobile-section">
          <span>Dashboard section</span>
          <select value={section} onChange={(event) => goToSection(event.target.value)}>
            {NAV_ITEMS.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
            <option value="settings">Settings</option>
          </select>
        </label>

        <nav className="admin-nav" aria-label="Dashboard sections">
          {NAV_GROUPS.map((group) => (
            <div className="admin-nav-group" key={group.label}>
              <div className="admin-nav-lbl">{group.label}</div>
              {group.items.map(({ key, icon, label }) => (
                <button
                  key={key}
                  className={`admin-nav-item${section === key ? ' on' : ''}`}
                  onClick={() => goToSection(key)}
                  aria-current={section === key ? 'page' : undefined}
                >
                  {icon} {label}
                </button>
              ))}
            </div>
          ))}

          <div className="admin-nav-lbl">Account</div>
          <button
            className={`admin-nav-item${section === 'settings' ? ' on' : ''}`}
            onClick={() => goToSection('settings')}
            aria-current={section === 'settings' ? 'page' : undefined}
          >
            <Settings size={18} style={{ marginRight: 8 }} /> Settings
          </button>
        </nav>
      </div>

      {/* ── Main panel ── */}
      <div className="admin-main">
        <div className="admin-topbar">
          <div className="admin-topbar-heading">
            <h1 className="admin-page-title serif">{TITLES[section]}</h1>
            {lastUpdated && (
              <span className="admin-last-updated">
                Updated {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
          </div>
          <div className="admin-topbar-actions">
            <button
              type="button"
              className="admin-refresh"
              onClick={loadAll}
              disabled={loading || refreshing}
              aria-label="Refresh all dashboard data"
            >
              <RefreshCw size={15} className={refreshing ? 'spin' : ''} />
              <span>{refreshing ? 'Refreshing' : 'Refresh'}</span>
            </button>
            <DashboardUserMenu user={user} onLogout={onLogout} />
          </div>
        </div>

        <div className="admin-content">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={section}
              initial={reduceMotion ? false : { opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -4 }}
              transition={{ duration: reduceMotion ? 0 : 0.18, ease: 'easeOut' }}
            >
          {hasStaleSectionData && (
            <div
              className="info-banner info-banner-row"
              style={{
                background: '#FEF2F2',
                borderColor: '#FECACA',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 16,
              }}
            >
              <span>
                <strong>Some data could not be refreshed.</strong>{' '}
                {lastUpdated ? 'Showing the latest available records.' : sectionErrors.join(' · ')}
              </span>
              <button
                type="button"
                className="btn-lg"
                style={{ padding: '8px 16px', fontSize: 13, flexShrink: 0 }}
                onClick={loadAll}
              >
                Retry
              </button>
            </div>
          )}
          {section === 'overview' && (
            <Overview
              farmers={farmers}
              transactions={transactions}
              loading={loading}
              onNavigate={goToSection}
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
              cooperativeId={cooperativeId}
              loading={loading}
              onRefresh={loadAll}
              dataStale={hasStaleSectionData}
            />
          )}
          {section === 'scores' && (
            <Scores farmers={farmers} cooperativeId={cooperativeId} loading={loading} />
          )}
          {section === 'sms' && (
            <SMS
              cooperativeId={cooperativeId ?? resolveCooperativeId(user)}
              memberCount={farmers.length}
            />
          )}
          {section === 'loans' && (
            <Loans
              farmers={farmers}
              loans={loans}
              cooperativeId={cooperativeId}
              loading={loading}
              onRefresh={refreshLoans}
              dataStale={hasStaleSectionData}
            />
          )}
          {section === 'production' && (
            <Production
              farmers={farmers}
              productions={productions}
              cooperativeId={cooperativeId}
              loading={loading}
              onRefresh={loadAll}
            />
          )}
          {section === 'settings' && (
            <SettingsView
              cooperative={cooperative}
              cooperativeId={cooperativeId ?? resolveCooperativeId(user)}
              loading={loading}
              onRefresh={loadAll}
            />
          )}
          {section === 'ussd' && (
            <USSD />
          )}
          {section === 'activity' && (
            <Activity />
          )}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
