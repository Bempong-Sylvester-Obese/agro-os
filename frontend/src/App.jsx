import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { clearAuthToken } from './api/auth'
import Navbar from './components/Navbar'
import { pageKeyFromPath } from './constants/routes'
import HomePage from './pages/HomePage'
import SolutionsPage from './pages/SolutionsPage'
import FeaturesPage from './pages/FeaturesPage'
import PricingPage from './pages/PricingPage'
import BookDemoPage from './pages/BookDemoPage'
import DashboardPage from './pages/DashboardPage'
import LoginPage from './pages/LoginPage'

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

function DashboardGate({ user, onLogout }) {
  if (!user) return <Navigate to="/login" replace />
  return <DashboardPage user={user} onLogout={onLogout} />
}

function AppShell({ user, onAuth, onLogout }) {
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
      {showNavbar && <Navbar />}
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/solutions" element={<SolutionsPage />} />
        <Route path="/features" element={<FeaturesPage />} />
        <Route path="/pricing" element={<PricingPage />} />
        <Route path="/book-demo" element={<BookDemoPage />} />
        <Route path="/login" element={<LoginPage onAuth={onAuth} />} />
        <Route path="/dashboard" element={<DashboardGate user={user} onLogout={onLogout} />} />
        <Route path="/dashboard/:section" element={<DashboardGate user={user} onLogout={onLogout} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}

function AppRouter() {
  const navigate = useNavigate()
  const [user, setUser] = useState(null)

  function handleAuth(u) {
    setUser(u)
    navigate('/dashboard')
    window.scrollTo({ top: 0, behavior: 'instant' })
  }

  function handleLogout() {
    clearAuthToken()
    setUser(null)
    navigate('/')
    window.scrollTo({ top: 0, behavior: 'instant' })
  }

  return <AppShell user={user} onAuth={handleAuth} onLogout={handleLogout} />
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRouter />
    </BrowserRouter>
  )
}
