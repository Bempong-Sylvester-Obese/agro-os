// src/App.jsx
import { useState } from 'react'
import Navbar        from './components/Navbar'
import HomePage      from './pages/HomePage'
import SolutionsPage from './pages/SolutionsPage'
import FeaturesPage  from './pages/FeaturesPage'
import PricingPage   from './pages/PricingPage'
import DashboardPage from './pages/DashboardPage'
import AuthPage      from './pages/AuthPage'

export default function App() {
  const [page, setPage] = useState('home')
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('agro_os_token'))

  const handleLoginSuccess = () => {
    setIsAuthenticated(true)
    setPage('dashboard')
  }

  const handleLogout = () => {
    localStorage.removeItem('agro_os_token')
    setIsAuthenticated(false)
    setPage('home')
  }

  return (
    <>
      <Navbar activePage={page} setPage={setPage} isAuthenticated={isAuthenticated} onLogout={handleLogout} />

      {page === 'home'      && <HomePage      setPage={setPage} />}
      {page === 'solutions' && <SolutionsPage setPage={setPage} />}
      {page === 'features'  && <FeaturesPage  setPage={setPage} />}
      {page === 'pricing'   && <PricingPage   setPage={setPage} />}
      {page === 'auth'      && <AuthPage      setPage={setPage} onLoginSuccess={handleLoginSuccess} />}
      {page === 'dashboard' && (isAuthenticated ? <DashboardPage /> : <AuthPage setPage={setPage} onLoginSuccess={handleLoginSuccess} />)}
    </>
  )
}
