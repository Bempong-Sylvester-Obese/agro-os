import { useEffect, useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { clearAuthSession, fetchCurrentUser, getAuthToken, getAuthUser, getRefreshToken, isAuthTokenUsable, logoutSession, refreshAccessToken, storeAuthUser, userFromAuthToken, userFromMeResponse } from './api/auth'
import { isTransportFailure } from './api/config'
import Navbar from './components/Navbar'
import { pageKeyFromPath } from './constants/routes'
import HomePage from './pages/HomePage'
import SolutionsPage from './pages/SolutionsPage'
import FeaturesPage from './pages/FeaturesPage'
import PricingPage from './pages/PricingPage'
import BookDemoPage from './pages/BookDemoPage'
import CompliancePage from './pages/CompliancePage'
import InvestorRelationsPage from './pages/InvestorRelationsPage'
import DashboardPage from './pages/DashboardPage'
import { DashboardGateSkeleton } from './components/dashboard/DashboardSkeleton'
import AuthPage from './pages/AuthPage'
import SubscriptionPage from './pages/SubscriptionPage'
import { PageMotion } from './components/Motion'

function safeNextPath(next) {
  if (!next || !next.startsWith('/') || next.startsWith('//')) return '/dashboard'
  return next
}

function ScrollToHash() {
  const { hash, pathname } = useLocation()

  useEffect(() => {
    if (!hash) return undefined
    const id = hash.slice(1)
    const timer = window.setTimeout(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 80)
    return () => window.clearTimeout(timer)
  }, [hash, pathname])

  return null
}

function DashboardGate({ user, authReady, onLogout }) {
  const location = useLocation()
  if (!authReady) return <DashboardGateSkeleton />
  if (!user || !isAuthTokenUsable()) {
    const next = encodeURIComponent(`${location.pathname}${location.search}${location.hash}`)
    return <Navigate to={`/login?next=${next}`} replace />
  }
  return <DashboardPage user={user} onLogout={onLogout} />
}

function AppShell({ user, authReady, onAuth, onLogout }) {
  const location = useLocation()
  const pageKey = pageKeyFromPath(location.pathname)

  useEffect(() => {
    const root = document.documentElement
    root.classList.remove('page-dashboard', 'page-login')
    if (pageKey === 'dashboard') root.classList.add('page-dashboard')
    if (pageKey === 'login') root.classList.add('page-login')

    const themeMeta = document.querySelector('meta[name="theme-color"]')
    if (themeMeta) {
      themeMeta.setAttribute('content', pageKey === 'dashboard' ? '#f4f6f4' : '#f7f4ef')
    }
  }, [pageKey])

  const showNavbar = pageKey !== 'login' && pageKey !== 'dashboard'

  return (
    <div className="app-shell">
      <ScrollToHash />
      {showNavbar && <Navbar isAuthenticated={Boolean(user)} onLogout={onLogout} />}
      <AnimatePresence mode="wait" initial={false}>
        <PageMotion key={pageKey} pageKey={pageKey} className={`page-motion--${pageKey}`}>
          <Routes location={location}>
            <Route path="/" element={<HomePage user={user} />} />
            <Route path="/solutions" element={<SolutionsPage user={user} />} />
            <Route path="/features" element={<FeaturesPage user={user} />} />
            <Route path="/pricing" element={<PricingPage />} />
            <Route path="/subscribe/:plan" element={<SubscriptionPage />} />
            <Route path="/book-demo" element={<BookDemoPage />} />
            <Route path="/compliance" element={<CompliancePage />} />
            <Route path="/investors" element={<InvestorRelationsPage />} />
            <Route path="/login" element={<AuthPage onAuth={onAuth} />} />
            <Route path="/dashboard" element={<DashboardGate user={user} authReady={authReady} onLogout={onLogout} />} />
            <Route path="/dashboard/:section" element={<DashboardGate user={user} authReady={authReady} onLogout={onLogout} />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </PageMotion>
      </AnimatePresence>
    </div>
  )
}

function AppRouter() {
  const navigate = useNavigate()
  const [user, setUser] = useState(null)
  const [authReady, setAuthReady] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function boot() {
      let token = getAuthToken()
      const storedUser = getAuthUser()

      if (!isAuthTokenUsable(token) && getRefreshToken()) {
        try {
          token = await refreshAccessToken()
        } catch {
          if (!cancelled) {
            clearAuthSession()
            setAuthReady(true)
          }
          return
        }
      }

      if (!isAuthTokenUsable(token)) {
        if (storedUser || token) clearAuthSession()
        if (!cancelled) setAuthReady(true)
        return
      }

      const bootstrap = storedUser || userFromAuthToken(token)
      if (!bootstrap) {
        clearAuthSession()
        if (!cancelled) setAuthReady(true)
        return
      }
      if (!storedUser) storeAuthUser(bootstrap)
      if (!cancelled) {
        setUser(bootstrap)
        setAuthReady(true)
      }

      try {
        const me = await fetchCurrentUser()
        if (cancelled) return
        const hydrated = { ...bootstrap, ...userFromMeResponse(me) }
        storeAuthUser(hydrated)
        setUser(hydrated)
      } catch (err) {
        if (cancelled) return
        if (isTransportFailure(err)) return
        if (err?.status === 401 || err?.status === 404 || err?.status >= 500) return
        clearAuthSession()
        setUser(null)
      }
    }

    boot()
    return () => {
      cancelled = true
    }
  }, [])

  function handleAuth(u) {
    storeAuthUser(u)
    setUser(u)
    const next = new URLSearchParams(window.location.search).get('next')
    navigate(safeNextPath(next))
    window.scrollTo({ top: 0, behavior: 'instant' })
  }

  function handleLogout() {
    logoutSession().finally(() => {
      clearAuthSession()
      setUser(null)
      navigate('/')
      window.scrollTo({ top: 0, behavior: 'instant' })
    })
  }

  return <AppShell user={user} authReady={authReady} onAuth={handleAuth} onLogout={handleLogout} />
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRouter />
    </BrowserRouter>
  )
}
