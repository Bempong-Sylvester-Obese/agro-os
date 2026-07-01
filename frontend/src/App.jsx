// src/App.jsx
import { useState } from 'react'
import { clearAuthToken } from './api/auth'
import Navbar        from './components/Navbar'
import HomePage      from './pages/HomePage'
import SolutionsPage from './pages/SolutionsPage'
import FeaturesPage  from './pages/FeaturesPage'
import PricingPage   from './pages/PricingPage'
import DashboardPage from './pages/DashboardPage'
import LoginPage     from './pages/LoginPage'

export default function App() {
  const [page, setPage]     = useState('home')
  const [user, setUser]     = useState(null)   // null = not logged in

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
    clearAuthToken()
    setUser(null)
    setPage('home')
  }

  return (
    <>
      {page !== 'login' && (
        <Navbar activePage={page} setPage={handleSetPage} />
      )}

      {page === 'home'      && <HomePage      setPage={handleSetPage} />}
      {page === 'solutions' && <SolutionsPage setPage={handleSetPage} />}
      {page === 'features'  && <FeaturesPage  setPage={handleSetPage} />}
      {page === 'pricing'   && <PricingPage   setPage={handleSetPage} />}
      {page === 'login'     && <LoginPage     onAuth={handleAuth} />}
      {page === 'dashboard' && user && (
        <DashboardPage user={user} onLogout={handleLogout} />
      )}
    </>
  )
}
