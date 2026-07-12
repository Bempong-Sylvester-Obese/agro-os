import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { clearAuthSession, getAuthToken, getAuthUser, storeAuthUser, userFromAuthToken } from './api/auth'
import Navbar from './components/Navbar'
import { pageKeyFromPath } from './constants/routes'
import HomePage from './pages/HomePage'
import SolutionsPage from './pages/SolutionsPage'
import FeaturesPage from './pages/FeaturesPage'
import PricingPage from './pages/PricingPage'
import BookDemoPage from './pages/BookDemoPage'
import DashboardPage from './pages/DashboardPage'
import { DashboardGateSkeleton } from './components/dashboard/DashboardSkeleton'
import AuthPage from './pages/AuthPage'

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
  if (!user) {
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
      <Routes>
        <Route path="/" element={<HomePage user={user} />} />
        <Route path="/solutions" element={<SolutionsPage user={user} />} />
        <Route path="/features" element={<FeaturesPage user={user} />} />
        <Route path="/pricing" element={<PricingPage />} />
        <Route path="/book-demo" element={<BookDemoPage />} />
        <Route path="/login" element={<AuthPage onAuth={onAuth} />} />
        <Route path="/dashboard" element={<DashboardGate user={user} authReady={authReady} onLogout={onLogout} />} />
        <Route path="/dashboard/:section" element={<DashboardGate user={user} authReady={authReady} onLogout={onLogout} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}

function AppRouter() {
  const navigate = useNavigate()
  const [user, setUser] = useState(null)
  const [authReady, setAuthReady] = useState(false)

  useEffect(() => {
    const token = getAuthToken()
    const storedUser = getAuthUser()

    if (!token) {
      if (storedUser) clearAuthSession()
      setAuthReady(true)
      return
    }

    if (storedUser) {
      setUser(storedUser)
    } else {
      const fromToken = userFromAuthToken(token)
      if (fromToken) {
        storeAuthUser(fromToken)
        setUser(fromToken)
      } else {
        clearAuthSession()
      }
    }

    setAuthReady(true)
  }, [])

  function handleAuth(u) {
    storeAuthUser(u)
    setUser(u)
    const next = new URLSearchParams(window.location.search).get('next')
    navigate(safeNextPath(next))
    window.scrollTo({ top: 0, behavior: 'instant' })
  }

  function handleLogout() {
    clearAuthSession()
    setUser(null)
    navigate('/')
    window.scrollTo({ top: 0, behavior: 'instant' })
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
