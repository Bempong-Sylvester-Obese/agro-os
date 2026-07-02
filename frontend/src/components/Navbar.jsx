// src/components/Navbar.jsx
import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { pageKeyFromPath } from '../constants/routes'
import { useAppNavigate } from '../hooks/useAppNavigate'

export default function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()
  const setPage = useAppNavigate()
  const activePage = pageKeyFromPath(location.pathname)

  const links = [
    { key: 'home',      label: 'Home' },
    { key: 'solutions', label: 'Solutions' },
    { key: 'features',  label: 'Features' },
    { key: 'pricing',   label: 'Pricing' },
    { key: 'dashboard', label: 'Dashboard' },
  ]

  useEffect(() => {
    if (menuOpen) {
      document.body.classList.add('no-scroll')
    } else {
      document.body.classList.remove('no-scroll')
    }
    return () => document.body.classList.remove('no-scroll')
  }, [menuOpen])

  function navigate(key, options) {
    setPage(key, options)
    setMenuOpen(false)
  }

  return (
    <nav className={`nav${menuOpen ? ' nav--open' : ''}`}>
      <a
        className="nav-logo"
        href="/"
        onClick={(e) => { e.preventDefault(); navigate('home') }}
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

      <div className="nav-tabs">
        {links.map(({ key, label }) => (
          <a
            key={key}
            href={key === 'home' ? '/' : `/${key}`}
            className={`nav-tab${activePage === key ? ' active' : ''}`}
            onClick={(e) => { e.preventDefault(); navigate(key) }}
          >
            {label}
          </a>
        ))}
      </div>

      <div className="nav-right">
        <a
          href="/login"
          className="btn-ghost"
          onClick={(e) => { e.preventDefault(); navigate('login', { loginMode: 'login' }) }}
        >
          Log in
        </a>
        <a
          href="/login?mode=signup"
          className="btn-nav"
          onClick={(e) => { e.preventDefault(); navigate('login', { loginMode: 'signup' }) }}
        >
          Get started free
        </a>
      </div>

      <button
        type="button"
        className="nav-toggle"
        onClick={() => setMenuOpen((open) => !open)}
        aria-label={menuOpen ? 'Close menu' : 'Open menu'}
        aria-expanded={menuOpen}
      >
        {menuOpen ? '✕' : '☰'}
      </button>
    </nav>
  )
}
