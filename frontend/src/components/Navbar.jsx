// src/components/Navbar.jsx
import { useCallback, useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { Menu, X } from 'lucide-react'
import { pageKeyFromPath, MARKETING_PATHS } from '../constants/routes'
import { useAppNavigate } from '../hooks/useAppNavigate'

export default function Navbar({ isAuthenticated, onLogout }) {
  const setPage = useAppNavigate()
  const { pathname } = useLocation()
  const activePage = pageKeyFromPath(pathname)
  const [menuOpen, setMenuOpen] = useState(false)
  const reduceMotion = useReducedMotion()

  const links = [
    { key: 'home', label: 'Home' },
    { key: 'solutions', label: 'Solutions' },
    { key: 'features', label: 'Features' },
    { key: 'pricing', label: 'Pricing' },
    { key: 'bookDemo', label: 'Book demo' },
    { key: 'dashboard', label: 'Dashboard' },
  ]

  const closeMenu = useCallback(() => setMenuOpen(false), [])

  useEffect(() => {
    if (!menuOpen) return
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const onKeyDown = (e) => {
      if (e.key === 'Escape') closeMenu()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [menuOpen, closeMenu])

  useEffect(() => closeMenu(), [pathname, closeMenu])

  const showMarketingNav = activePage !== 'dashboard'

  function navHref(key) {
    if (key === 'dashboard') return '/dashboard'
    return MARKETING_PATHS[key] || '/'
  }

  function isActive(key) {
    if (key === 'bookDemo') return pathname.startsWith('/book-demo')
    return activePage === key
  }

  function handleNav(key) {
    return (e) => {
      e.preventDefault()
      setPage(key)
      closeMenu()
    }
  }

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

      {showMarketingNav && (
        <div className="nav-tabs">
          {links.map(({ key, label }) => (
            <a
              key={key}
              href={navHref(key)}
              className={`nav-tab${isActive(key) ? ' active' : ''}`}
              onClick={handleNav(key)}
            >
              {label}
            </a>
          ))}
        </div>
      )}

      <div className="nav-right">
        {showMarketingNav && (
          <button
            type="button"
            className="nav-menu-toggle"
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={menuOpen}
            aria-controls="nav-mobile-menu"
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        )}
        {isAuthenticated ? (
          <button type="button" className="btn-nav" onClick={() => onLogout?.()}>Log out</button>
        ) : (
          <>
            <a href="/login" className="btn-ghost" onClick={(e) => { e.preventDefault(); setPage('login') }}>Log in</a>
            <a href="/subscribe/starter" className="btn-nav" onClick={(e) => { e.preventDefault(); setPage('subscription', { plan: 'starter' }) }}>Get started free</a>
          </>
        )}
      </div>

      <AnimatePresence>
        {showMarketingNav && menuOpen && (
          <motion.div
            id="nav-mobile-menu"
            className="nav-mobile-panel open"
            initial={reduceMotion ? false : { opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -8 }}
            transition={{ duration: reduceMotion ? 0 : 0.18, ease: 'easeOut' }}
          >
            {links.map(({ key, label }) => (
              <a
                key={key}
                href={navHref(key)}
                className={`nav-mobile-link${isActive(key) ? ' active' : ''}`}
                onClick={handleNav(key)}
              >
                {label}
              </a>
            ))}
            <div className="nav-mobile-actions">
              {isAuthenticated ? (
                <button type="button" className="btn-nav" onClick={() => { closeMenu(); onLogout?.() }}>
                  Log out
                </button>
              ) : (
                <>
                  <a href="/login" className="btn-ghost" onClick={(e) => { e.preventDefault(); closeMenu(); setPage('login') }}>
                    Log in
                  </a>
                  <a href="/subscribe/starter" className="btn-nav" onClick={(e) => { e.preventDefault(); closeMenu(); setPage('subscription', { plan: 'starter' }) }}>
                    Get started free
                  </a>
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  )
}
