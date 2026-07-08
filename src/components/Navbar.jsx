// src/components/Navbar.jsx
export default function Navbar({ activePage, setPage, onGetStarted }) {
  const links = [
    { key: 'home',      label: 'Home' },
    { key: 'solutions', label: 'Solutions' },
    { key: 'features',  label: 'Features' },
    { key: 'pricing',   label: 'Pricing' },
    { key: 'dashboard', label: 'Dashboard' },
  ]

  return (
    <nav className="nav">
      <a
        className="nav-logo"
        href="#"
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

      <div className="nav-tabs">
        {links.map(({ key, label }) => (
          <a
            key={key}
            href="#"
            className={`nav-tab${activePage === key ? ' active' : ''}`}
            onClick={(e) => { e.preventDefault(); setPage(key) }}
          >
            {label}
          </a>
        ))}
      </div>

      <div className="nav-right">
        <a href="#" className="btn-ghost" onClick={(e) => { e.preventDefault(); setPage('login') }}>Log in</a>
        <a href="#" className="btn-nav" onClick={(e) => { e.preventDefault(); onGetStarted() }}>Get started free</a>
      </div>
    </nav>
  )
}
