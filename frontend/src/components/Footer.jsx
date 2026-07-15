// src/components/Footer.jsx
import React from 'react'
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
          <a href="/book-demo" className="footer-link" onClick={go('bookDemo')}>Book a demo</a>
        </div>

        <div>
          <div className="footer-col-title">Solutions</div>
          <a href="/solutions" className="footer-link" onClick={go('solutions')}>Cooperatives</a>
          <a href="/solutions#ussd-section" className="footer-link" onClick={go('solutions', { scrollTo: 'ussd-section' })}>Smallholders</a>
          <a href="/solutions" className="footer-link" onClick={go('solutions')}>Field operations</a>
          <a href="/solutions" className="footer-link" onClick={go('solutions')}>Lenders & programmes</a>
        </div>

        <div>
          <div className="footer-col-title">Moolre</div>
          <a href="/#moolre-integration" className="footer-link" onClick={go('home', { scrollTo: 'moolre-integration' })}>Integration overview</a>
          <a href="/#moolre-integration" className="footer-link" onClick={go('home', { scrollTo: 'moolre-integration' })}>Collections & disbursements</a>
          <a href="/solutions#ussd-section" className="footer-link" onClick={go('solutions', { scrollTo: 'ussd-section' })}>Merchant-code USSD</a>
        </div>

        <div>
          <div className="footer-col-title">Company</div>
          <a href="/subscribe/starter" className="footer-link" onClick={go('subscription', { plan: 'starter' })}>Create free workspace</a>
          <a href="/book-demo?plan=enterprise&amp;topic=Enterprise+implementation" className="footer-link" onClick={go('bookDemo', { plan: 'enterprise', topic: 'Enterprise implementation' })}>Contact enterprise sales</a>
        </div>

        <div>
          <div className="footer-col-title">Legal</div>
          <a href="/compliance" className="footer-link" onClick={go('compliance')}>Compliance policy</a>
        </div>
      </div>

      <div className="footer-btm">
        <span>© 2026 AgroOS. All rights reserved.</span>
        <span>Built for the Moolre ecosystem</span>
      </div>
    </footer>
  )
}
