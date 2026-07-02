// src/components/Footer.jsx
import { useAppNavigate } from '../hooks/useAppNavigate'

export default function Footer() {
  const setPage = useAppNavigate()

  function go(page, options) {
    return (e) => {
      e.preventDefault()
      setPage(page, options)
    }
  }

  return (
    <footer className="footer">
      <div className="footer-grid">
        <div>
          <div className="footer-brand">AgroOS</div>
          <div className="footer-tag">
            Built for African agriculture.<br />
            Modern cooperative management.
          </div>
        </div>

        <div>
          <div className="footer-col-title">Product</div>
          <a href="/features" className="footer-link" onClick={go('features')}>Features</a>
          <a href="/pricing" className="footer-link" onClick={go('pricing')}>Pricing</a>
          <a href="/solutions#ussd-section" className="footer-link" onClick={go('solutions', { scrollTo: 'ussd-section' })}>USSD integration</a>
          <a href="/features" className="footer-link" onClick={go('features')}>API docs</a>
        </div>

        <div>
          <div className="footer-col-title">Solutions</div>
          <a href="/solutions" className="footer-link" onClick={go('solutions')}>Cooperatives</a>
          <a href="/solutions#ussd-section" className="footer-link" onClick={go('solutions', { scrollTo: 'ussd-section' })}>Smallholders</a>
          <a href="/dashboard/production" className="footer-link" onClick={go('dashboard', { dashboardSection: 'production' })}>Field agents</a>
          <a href="/dashboard/scores" className="footer-link" onClick={go('dashboard', { dashboardSection: 'scores' })}>Lenders</a>
        </div>

        <div>
          <div className="footer-col-title">Moolre</div>
          <a href="/#moolre-integration" className="footer-link" onClick={go('home', { scrollTo: 'moolre-integration' })}>Integration</a>
          <a href="/dashboard/payments" className="footer-link" onClick={go('dashboard', { dashboardSection: 'payments' })}>Payment portal</a>
          <a href="/dashboard/ussd" className="footer-link" onClick={go('dashboard', { dashboardSection: 'ussd' })}>USSD menu</a>
        </div>

        <div>
          <div className="footer-col-title">Company</div>
          <a href="/" className="footer-link" onClick={go('home')}>About</a>
          <a href="/login?mode=signup" className="footer-link" onClick={go('login', { loginMode: 'signup' })}>Request access</a>
          <a href="/features" className="footer-link" onClick={go('features')}>Help center</a>
        </div>
      </div>

      <div className="footer-btm">
        <span>© 2026 AgroOS. All rights reserved.</span>
        <span>Built for the Moolre ecosystem</span>
      </div>
    </footer>
  )
}
