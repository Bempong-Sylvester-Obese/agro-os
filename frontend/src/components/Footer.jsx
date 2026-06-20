// src/components/Footer.jsx
export default function Footer({ setPage }) {
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
          <a href="#" className="footer-link" onClick={(e) => { e.preventDefault(); setPage('features') }}>Features</a>
          <a href="#" className="footer-link" onClick={(e) => { e.preventDefault(); setPage('pricing') }}>Pricing</a>
          <a href="#" className="footer-link" onClick={(e) => e.preventDefault()}>USSD integration</a>
          <a href="#" className="footer-link" onClick={(e) => e.preventDefault()}>API docs</a>
        </div>

        <div>
          <div className="footer-col-title">Solutions</div>
          <a href="#" className="footer-link" onClick={(e) => { e.preventDefault(); setPage('solutions') }}>Cooperatives</a>
          <a href="#" className="footer-link" onClick={(e) => { e.preventDefault(); setPage('solutions') }}>Smallholders</a>
          <a href="#" className="footer-link" onClick={(e) => { e.preventDefault(); setPage('solutions') }}>Field agents</a>
          <a href="#" className="footer-link" onClick={(e) => { e.preventDefault(); setPage('solutions') }}>Lenders</a>
        </div>

        <div>
          <div className="footer-col-title">Moolre</div>
          <a href="#" className="footer-link" onClick={(e) => e.preventDefault()}>Integration</a>
          <a href="#" className="footer-link" onClick={(e) => e.preventDefault()}>Payment portal</a>
          <a href="#" className="footer-link" onClick={(e) => e.preventDefault()}>USSD menu</a>
        </div>

        <div>
          <div className="footer-col-title">Company</div>
          <a href="#" className="footer-link" onClick={(e) => e.preventDefault()}>About</a>
          <a href="#" className="footer-link" onClick={(e) => e.preventDefault()}>Request access</a>
          <a href="#" className="footer-link" onClick={(e) => e.preventDefault()}>Help center</a>
        </div>
      </div>

      <div className="footer-btm">
        <span>© 2026 AgroOS. All rights reserved.</span>
        <span>Built for the Moolre ecosystem</span>
      </div>
    </footer>
  )
}
