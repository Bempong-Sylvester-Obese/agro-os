// src/App.jsx
import { useState, useEffect } from 'react'
import Navbar        from './components/Navbar'
import HomePage      from './pages/HomePage'
import SolutionsPage from './pages/SolutionsPage'
import FeaturesPage  from './pages/FeaturesPage'
import PricingPage   from './pages/PricingPage'
import DashboardPage from './pages/DashboardPage'
import LoginPage     from './pages/LoginPage'
import BookDemoPage  from './pages/BookDemoPage'
import GetStartedModal from './components/GetStartedModal'
import { authApi, getToken, setToken } from './lib/api'

export default function App() {
  const [page, setPage]             = useState('home')
  const [user, setUser]             = useState(null)
  const [checkingSession, setCheckingSession] = useState(true)
  const [showGetStarted, setShowGetStarted] = useState(false)

  // On load, if a token is stored, try to restore the session from the API.
  useEffect(() => {
    const token = getToken()
    if (!token) { setCheckingSession(false); return }

    authApi.me()
      .then(u => { setUser(u); setPage('dashboard') })
      .catch(() => { setToken(null) })
      .finally(() => setCheckingSession(false))
  }, [])

  function handleSetPage(p) {
    if (p === 'dashboard' && !user) {
      setPage('login')
    } else {
      setPage(p)
    }
  }

  function handleAuth(u) {
    setUser(u)
    setPage('dashboard')
  }

  function handleLogout() {
    setToken(null)
    setUser(null)
    setPage('home')
  }

  if (checkingSession) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', color: 'var(--muted)', fontFamily: "'DM Sans',sans-serif" }}>
        Loading AgroOS…
      </div>
    )
  }

  return (
    <>
      {page !== 'login' && (
        <Navbar
          activePage={page}
          setPage={handleSetPage}
          onGetStarted={() => setShowGetStarted(true)}
        />
      )}

      {page === 'home'      && <HomePage      setPage={handleSetPage} onGetStarted={() => setShowGetStarted(true)} />}
      {page === 'solutions' && <SolutionsPage setPage={handleSetPage} onGetStarted={() => setShowGetStarted(true)} />}
      {page === 'features'  && <FeaturesPage  setPage={handleSetPage} onGetStarted={() => setShowGetStarted(true)} />}
      {page === 'pricing'   && <PricingPage   setPage={handleSetPage} onGetStarted={() => setShowGetStarted(true)} />}
      {page === 'login'     && <LoginPage     onAuth={handleAuth} />}
      {page === 'book-demo' && <BookDemoPage  setPage={handleSetPage} />}
      {page === 'dashboard' && user && (
        <DashboardPage user={user} onLogout={handleLogout} />
      )}

      {showGetStarted && (
        <GetStartedModal onClose={() => setShowGetStarted(false)} onLogin={() => { setShowGetStarted(false); setPage('login') }} />
      )}
    </>
  )
}
