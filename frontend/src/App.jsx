// src/App.jsx
import { useState } from 'react'
import Navbar        from './components/Navbar'
import HomePage      from './pages/HomePage'
import SolutionsPage from './pages/SolutionsPage'
import FeaturesPage  from './pages/FeaturesPage'
import PricingPage   from './pages/PricingPage'
import DashboardPage from './pages/DashboardPage'
import LoginPage     from './pages/LoginPage'
import BookDemoPage  from './pages/BookDemoPage'
import GetStartedModal from './components/GetStartedModal'

export default function App() {
  const [page, setPage]             = useState('home')
  const [user, setUser]             = useState(null)
  const [showGetStarted, setShowGetStarted] = useState(false)

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
    setUser(null)
    setPage('home')
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
