// src/components/Navbar.jsx
import { useLocation } from 'react-router-dom'
import { pageKeyFromPath } from '../constants/routes'
import { useAppNavigate } from '../hooks/useAppNavigate'

export default function Navbar({ isAuthenticated, onLogout }) {
  const setPage = useAppNavigate()
  const { pathname } = useLocation()
  const activePage = pageKeyFromPath(pathname)

  const links = [
    { key: 'home', label: 'Home' },
    { key: 'solutions', label: 'Solutions' },
    { key: 'features', label: 'Features' },
    { key: 'pricing', label: 'Pricing' },
    { key: 'dashboard', label: 'Dashboard' },
  ]

  return (
    <nav className="nav">
      <a
        className="nav-logo"
        href="/"
        onClick={(e) => { e.preventDefault(); setPage('home') }}
      >
        <div className="nav-logo-mark">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
            stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22V12"/>
            <path d="M12 12C12 7 7 3 3 5c0 4 3 7 9 7z"/>
            <path d="M12 12C12 7 17 3 21 5c0 4-3 7-9 7z"/>
          </svg>
        </div>
        <span className="nav-logo-text">AgroOS</span>
      </a>

      {activePage !== 'dashboard' && (
        <div className="nav-tabs">
          {links.map(({ key, label }) => (
            <a
              key={key}
              href={`/${key === 'home' ? '' : key}`}
              className={`nav-tab${activePage === key ? ' active' : ''}`}
              onClick={(e) => { e.preventDefault(); setPage(key) }}
            >
              {label}
            </a>
          ))}
        </div>
      )}

      <div className="nav-right">
        {isAuthenticated ? (
          <>
            {activePage !== 'dashboard' && (
              <a href="/dashboard" className="btn-ghost" onClick={(e) => { e.preventDefault(); setPage('dashboard') }}>Dashboard</a>
            )}
            <a href="#" className="btn-nav" onClick={(e) => { e.preventDefault(); onLogout?.() }}>Log out</a>
          </>
        ) : (
          <>
            <a href="/login" className="btn-ghost" onClick={(e) => { e.preventDefault(); setPage('login') }}>Log in</a>
            <a href="/login" className="btn-nav" onClick={(e) => { e.preventDefault(); setPage('login', { loginMode: 'signup' }) }}>Get started free</a>
          </>
        )}
      </div>
    </nav>
  )
}
