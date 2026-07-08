// src/pages/HomePage.jsx
import { useState } from 'react'
import Footer from '../components/Footer'
import DashboardMock from '../components/DashboardMock'
import CTASection from '../components/CTASection'
import GetStartedModal from '../components/GetStartedModal'
import { useAppNavigate } from '../hooks/useAppNavigate'

const PHOTO_STRIP = [
  ['#1A4731', '🌾', 'The team',      'Building AgroOS, in Ghana, for Africa.'],
  ['#2D6A4F', '🤝', 'Cooperatives',  'Hundreds of cooperatives. One platform.'],
  ['#3A7D5C', '📱', 'USSD access',   'No smartphone needed. Manage via USSD.'],
  ['#1A4731', '🌍', 'Built for Africa', 'AgriTech built for the continent.'],
]

const FEATURES = [
  ['01', '👥', 'Member management',       'Profiles, roles, dues status, and full history for every farmer in your cooperative.'],
  ['02', '🌾', 'Production tracking',     'Log harvests, yields, and crop cycles per member. Build a data trail over seasons.'],
  ['03', '💳', 'Payments & disbursements','Collect dues and pay out via MoMo or card with full audit trails and receipts.'],
  ['04', '📱', 'SMS broadcasts',          'Send instant announcements to all members or filtered groups in one click.'],
  ['05', '⭐', 'AgroCredit Trust Score',  'AI-generated creditworthiness score built from payment history, production, and tenure.'],
  ['06', '📲', 'USSD access',             'Farmers without smartphones interact through a native Moolre USSD menu — no data needed.'],
]

const WHO = [
  ['🏛️', 'Cooperative leaders', 'Full dashboard access. Manage members, finances, and communications in one place. Replace the ledger.'],
  ['🌿', 'Field agents',         'Log production data and member activity on the go. Mobile-optimized for low-connectivity environments.'],
  ['📷', 'Farmers',              'Pay dues, check balances, and receive updates via USSD — no smartphone or data connection needed.'],
  ['🏦', 'Financiers & lenders', 'Access AgroCredit Trust Scores for individual farmers to assess creditworthiness with confidence.'],
]

export default function HomePage({ onAuth }) {
  const setPage = useAppNavigate()
  const [showGetStarted, setShowGetStarted] = useState(false)

  return (
    <>
      {/* ── Hero ── */}
      <section className="hero">
        <div className="hero-grid">
          <div>
            <div className="hero-eyebrow">Built for the Moolre ecosystem</div>
            <h1 className="hero-h1 serif">
              Farm management<br /><em>that works</em><br />for Africa
            </h1>
            <p className="hero-sub">
              From member records in Tamale to MoMo payments in Accra — AgroOS gives cooperative
              leaders one platform to manage everything. No spreadsheets. No paper ledgers.
            </p>
            <div className="hero-ctas">
              <button type="button" className="btn-lg" onClick={() => setShowGetStarted(true)}>Get started free</button>
              <button className="btn-out-lg" onClick={() => setPage('dashboard')}>See the dashboard</button>
            </div>
          </div>
          <div>
            <DashboardMock />
          </div>
        </div>
      </section>

      {/* ── Photo strip ── */}
      <div className="photo-strip">
        {PHOTO_STRIP.map(([bg, icon, tag, text]) => (
          <div key={tag} className="photo-card" style={{ background: bg }}>
            <div className="photo-bg">
              <span className="photo-bg-icon" aria-hidden="true">{icon}</span>
            </div>
            <div className="photo-cap">
              <div className="photo-cap-tag">{tag}</div>
              <div className="photo-cap-text">{text}</div>
            </div>
          </div>
        ))}
      </div>

      {/* ── Trust bar ── */}
      <div className="trust">
        {[
          ['MoMo & Card',  'Payments accepted'],
          ['Unlimited',    'Members & records'],
          ['USSD-ready',   'No smartphone needed'],
          ['AI-powered',   'AgroCredit Trust Scores'],
        ].map(([v, l]) => (
          <div key={l} className="trust-item">
            <div className="trust-v">{v}</div>
            <div className="trust-l">{l}</div>
          </div>
        ))}
      </div>

      {/* ── Features ── */}
      <section className="sec">
        <div className="sec-inner">
          <div className="sec-lbl">The platform</div>
          <h2 className="sec-h2 serif">Everything you need to<br />manage your cooperative</h2>
          <p className="sec-sub">
            One platform replacing the WhatsApp groups, spreadsheets, and paper ledgers holding cooperatives back.
          </p>
          <div className="feat-grid">
            {FEATURES.map(([num, icon, title, desc]) => (
              <div key={num} className="feat-card">
                <div className="feat-num mono">{num}</div>
                <div className="feat-icon">{icon}</div>
                <div className="feat-title serif">{title}</div>
                <div className="feat-desc">{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section className="sec bg-sage">
        <div className="sec-inner">
          <div className="sec-lbl" style={{ textAlign: 'center' }}>How it works</div>
          <h2 className="sec-h2 serif" style={{ textAlign: 'center', marginBottom: 56 }}>Up and running in minutes</h2>
          <div className="hiw-steps">
            {[
              ['01', 'Set up',  'Register your cooperative, add members, configure MoMo payment settings, and invite your team.'],
              ['02', 'Go live', 'Members start paying dues via MoMo or USSD. Farmers without smartphones activate instantly.'],
              ['03', 'Manage', 'Track production, monitor payments, review Trust Scores, and broadcast updates from one dashboard.'],
            ].map(([num, title, desc]) => (
              <div key={num} className="hiw-step">
                <div className="hiw-num serif">{num}</div>
                <div className="hiw-title serif">{title}</div>
                <p className="hiw-desc">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Who it's for ── */}
      <section className="sec">
        <div className="sec-inner">
          <div className="sec-lbl">Who it's for</div>
          <h2 className="sec-h2 serif">Built for everyone<br />in your cooperative</h2>
          <div className="who-grid">
            {WHO.map(([icon, title, desc]) => (
              <div key={title} className="who-card">
                <div className="who-icon">{icon}</div>
                <div className="who-title serif">{title}</div>
                <div className="who-desc">{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Moolre band ── */}
      <div className="moolre-band" id="moolre-integration">
        <div className="moolre-inner">
          <div>
            <div className="moolre-tag">Moolre integration</div>
            <h2 className="moolre-h2 serif">Built on Moolre.<br />Native from day one.</h2>
            <p className="moolre-desc">
              AgroOS uses Moolre's payment infrastructure natively — USSD menus, MoMo collections,
              and disbursements flow directly through the Moolre ecosystem. No third-party payment setup required.
            </p>
          </div>
          <button className="btn-gold" onClick={() => setPage('solutions', { scrollTo: 'ussd-section' })}>Explore integration →</button>
        </div>
      </div>

      {/* ── CTA ── */}
      <CTASection
        heading="Ready to modernize<br />your cooperative?"
        subtext="Join cooperatives across Ghana who've replaced paper with AgroOS. Start free, upgrade when you're ready."
        primaryLabel="Get started free"
        secondaryLabel="Book a demo"
        onPrimary={() => setShowGetStarted(true)}
        onSecondary={() => setPage('bookDemo')}
      />

      {showGetStarted && (
        <GetStartedModal
          onClose={() => setShowGetStarted(false)}
          onSignIn={() => {
            setShowGetStarted(false)
            setPage('login', { loginMode: 'login' })
          }}
          onAuth={(user) => {
            setShowGetStarted(false)
            onAuth(user)
          }}
        />
      )}

      <Footer />
    </>
  )
}
