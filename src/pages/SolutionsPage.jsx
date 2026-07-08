// src/pages/SolutionsPage.jsx
import Footer from '../components/Footer'
import CTASection from '../components/CTASection'

export default function SolutionsPage({ setPage, onGetStarted }) {
  return (
    <>
      {/* ── Hero ── */}
      <div className="sol-hero">
        <h1 className="sol-hero-h1 serif">One platform,<br />every role in the cooperative</h1>
        <p className="sol-hero-sub">
          AgroOS is designed for the full cooperative stack — from the farmer in the field to the administrator in the office.
        </p>
      </div>

      {/* ── Cooperative leaders ── */}
      <div className="sol-sec">
        <div className="sol-inner">
          <div>
            <div className="sol-tag">Cooperatives</div>
            <h2 className="sol-h2 serif">Replace the ledger. Run everything from one dashboard.</h2>
            <p className="sol-desc">
              Manage hundreds of members, track dues, run disbursements, and broadcast messages — all from a single
              admin dashboard. Replace the Excel sheets and WhatsApp groups.
            </p>
            <button className="btn-sol" onClick={() => setPage('dashboard')}>Explore cooperative tools →</button>
          </div>
          <div>
            <div className="sol-visual">
              <div className="sol-visual-title">Cooperative overview</div>
              {[
                ['Ashanti Farmers Co-op',  '248 members', 'GHS 29,760'],
                ['Northern Grain Alliance', '183 members', 'GHS 21,960'],
                ['Volta Rice Collective',   '96 members',  'GHS 11,520'],
              ].map(([name, meta, val]) => (
                <div key={name} className="sol-row">
                  <div>
                    <div className="sol-row-name">{name}</div>
                    <div className="sol-row-meta">{meta}</div>
                  </div>
                  <span className="bdg bdg-green">{val}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Farmers / USSD ── */}
      <div className="sol-sec">
        <div className="sol-inner rev">
          <div>
            <div className="sol-tag">Farmers</div>
            <h2 className="sol-h2 serif">No smartphone? No problem.</h2>
            <p className="sol-desc">
              Farmers interact with AgroOS through a native Moolre USSD menu — check balances, pay dues, and receive
              alerts directly from their basic phones. Designed for Ghana's rural reality.
            </p>
            <button className="btn-sol" onClick={() => setPage('features')}>See how USSD works →</button>
          </div>
          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <div className="ussd-phone">
              <div className="ussd-screen">
                <div className="ussd-t">AgroOS *920#</div>
                <div className="ussd-line">Welcome, Kwame</div>
                <div className="ussd-line">Balance: GHS 0.00</div>
                <div className="ussd-line">&nbsp;</div>
                <div className="ussd-line">1. Pay dues</div>
                <div className="ussd-line">2. Check balance</div>
                <div className="ussd-line">3. Production log</div>
                <div className="ussd-line">4. Contact manager</div>
                <div className="ussd-line">&nbsp;</div>
                <div className="ussd-dim">Reply 1–4</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Lenders ── */}
      <div className="sol-sec">
        <div className="sol-inner">
          <div>
            <div className="sol-tag">Lenders & financiers</div>
            <h2 className="sol-h2 serif">Lend with confidence using AI-powered scores.</h2>
            <p className="sol-desc">
              Access AgroCredit Trust Scores for individual farmers — built from payment history, production output,
              and cooperative tenure. Make lending decisions backed by real behavioral data.
            </p>
            {/* Explore AgroCredit → goes to Features page */}
            <button className="btn-sol" onClick={() => setPage('features')}>Explore AgroCredit →</button>
          </div>
          <div>
            <div className="sol-visual">
              <div className="sol-visual-title">AgroCredit score — Kofi Darko</div>
              <div style={{ textAlign: 'center', marginBottom: 18 }}>
                <div style={{ fontFamily: "'Fraunces',serif", fontSize: 52, fontWeight: 900, color: 'var(--g)' }}>92</div>
                <div style={{ fontSize: 11, color: 'var(--muted)' }}>out of 100 · Excellent</div>
              </div>
              {[
                ['Payment history',   95],
                ['Production output', 88],
                ['Cooperative tenure',90],
                ['Dues consistency',  92],
              ].map(([lbl, val]) => (
                <div key={lbl} className="score-row">
                  <span className="score-lbl">{lbl}</span>
                  <div className="score-bg"><div className="score-fill" style={{ width: `${val}%` }} /></div>
                  <span className="score-val">{val}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <CTASection
        heading="Find the right plan<br />for your cooperative"
        subtext="Simple, transparent pricing. Start free and scale as your cooperative grows."
        primaryLabel="See pricing"
        secondaryLabel="Talk to us"
        onPrimary={() => setPage('pricing')}
        onSecondary={() => setPage('book-demo')}
      />

      <Footer setPage={setPage} onGetStarted={onGetStarted} />
    </>
  )
}
