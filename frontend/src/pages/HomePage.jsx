// src/pages/HomePage.jsx
import React from 'react'
import Footer from '../components/Footer'
import DashboardMock from '../components/DashboardMock'
import CTASection from '../components/CTASection'
import { Reveal } from '../components/Motion'
import { useAppNavigate } from '../hooks/useAppNavigate'
import { Sprout, Smartphone, Users, CreditCard, MessageSquare, Star, Building, MapPin, Tractor, Landmark, Banknote, ArrowRight, ReceiptText, Check, FileText, Clock, ClipboardCheck } from 'lucide-react'

const MOOLRE_PILLARS = [
  {
    icon: <CreditCard size={24} />,
    title: 'Collections',
    desc: 'Collect member dues via MoMo with payment links, receipts, and webhook confirmation.',
    target: 'dashboard',
    dashboardSection: 'payments',
  },
  {
    icon: <Banknote size={24} />,
    title: 'Disbursements',
    desc: 'Approve and disburse loans straight to member wallets with full audit trails.',
    target: 'dashboard',
    dashboardSection: 'loans',
  },
  {
    icon: <MessageSquare size={24} />,
    title: 'SMS broadcasts',
    desc: 'Send announcements to all members or filtered groups in one click.',
    target: 'dashboard',
    dashboardSection: 'sms',
  },
  {
    icon: <Smartphone size={24} />,
    title: 'USSD access',
    desc: 'Farmers check active loan balances, pay dues, and view announcements through Moolre USSD.',
    target: 'solutions',
    scrollTo: 'ussd-section',
  },
]

const OPERATING_PROOF = [
  [FileText, 'Less paperwork', 'Replace scattered paper ledgers and spreadsheets with one simple system.'],
  [ClipboardCheck, 'Fewer errors, better records', 'Keep member, loan, payment, and produce records accurate and up to date.'],
  [Clock, 'More time for farmers', 'Faster communication and less admin so staff can focus on supporting members.'],
]

const FEATURES = [
  ['01', <Users size={28} />, 'Accurate member records', 'Keep farmer profiles, dues status, and history in one place instead of scattered sheets.', 'features'],
  ['02', <Banknote size={28} />, 'Loans and repayments', 'Track loan requests, approvals, disbursements, and repayments without rebuilding formulas.', 'solutions'],
  ['03', <Sprout size={28} />, 'Produce and farmer payments', 'Record deliveries and payouts so produce and money stay connected.', 'solutions'],
  ['04', <MessageSquare size={28} />, 'SMS reminders and announcements', 'Reach members quickly with dues reminders, meeting notices, and updates.', 'features'],
  ['05', <Smartphone size={28} />, 'Access on any mobile phone', 'Farmers use USSD on basic phones when they do not have smartphones or internet.', 'ussd'],
  ['06', <Star size={28} />, 'Trust Score for lending', 'Use payment, production, and repayment history to support clearer lending decisions.', 'solutions'],
]

const WHO = [
  [<Building size={32} />, 'Cooperative leaders', 'Full dashboard access. Manage members, finances, and communications in one place. Replace the ledger.'],
  [<MapPin size={32} />, 'Field agents',         'Log production data and member activity on the go. Mobile-optimized for low-connectivity environments.'],
  [<Tractor size={32} />, 'Farmers',              'Pay dues, check active loan balances, and view announcements via USSD — no smartphone or data connection needed.'],
  [<Landmark size={32} />, 'Financiers & lenders', 'Access AgroCredit Trust Scores for individual farmers to assess creditworthiness with confidence.'],
]

export default function HomePage({ user }) {
  const setPage = useAppNavigate()

  function previewDashboard() {
    document.getElementById('product-preview')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  function handlePillarClick(pillar) {
    if (pillar.target === 'dashboard') {
      if (user) {
        setPage('dashboard', { dashboardSection: pillar.dashboardSection })
      } else {
        setPage('login', { next: `/dashboard/${pillar.dashboardSection}` })
      }
      return
    }
    setPage(pillar.target, { scrollTo: pillar.scrollTo })
  }

  function exploreFeature(target) {
    if (target === 'ussd') {
      setPage('solutions', { scrollTo: 'ussd-section' })
      return
    }
    setPage(target)
  }

  return (
    <>
      <main>
      {/* ── Hero ── */}
      <section className="hero">
        <div className="hero-grid">
          <Reveal>
            <div className="hero-eyebrow"><strong>Digital office for farmer cooperatives</strong></div>
            <h1 className="hero-h1 serif">
              Less paperwork.<br /><em>Better records.</em><br />Stronger farmer cooperatives.
            </h1>
            <p className="hero-sub">
              AgroOS gives farmer cooperatives one simple system to manage member records, loans,
              payments, produce deliveries and communication, replacing paperwork and spreadsheets.
              It works on smartphones and basic mobile phones through USSD, making it accessible to every farmer.
            </p>
            <div className="hero-ctas">
              {user ? (
                <>
                  <button className="btn-lg" onClick={() => setPage('dashboard')}>Go to dashboard</button>
                  <button className="btn-out-lg" onClick={() => setPage('bookDemo')}>Book a demo</button>
                </>
              ) : (
                <>
                  <button className="btn-lg" onClick={() => setPage('subscription', { plan: 'starter' })}>Create free workspace</button>
                  <button className="btn-out-lg" onClick={previewDashboard}>Preview the dashboard</button>
                </>
              )}
            </div>
            {!user && (
              <div className="home-hero-assurance">
                <span><Check size={13} /> Starter is free</span>
                <span><Check size={13} /> No card required</span>
                <span><Check size={13} /> GHS pricing</span>
              </div>
            )}
          </Reveal>
          <Reveal delay={0.08} id="product-preview">
            <DashboardMock />
          </Reveal>
        </div>
      </section>

      {/* ── Operational proof ── */}
      <section className="home-proof" aria-label="What cooperatives gain">
        <Reveal className="home-proof-inner">
          <div className="home-proof-heading">
            <span>What really stands out</span>
            <strong className="serif">Not the technology. The outcomes.</strong>
          </div>
          <div className="home-proof-grid">
            {OPERATING_PROOF.map(([Icon, title, text]) => (
              <div key={title} className="home-proof-card">
                <div className="home-proof-icon"><Icon size={20} /></div>
                <div>
                  <h2 className="serif">{title}</h2>
                  <p>{text}</p>
                </div>
              </div>
            ))}
          </div>
        </Reveal>
      </section>

      {/* ── Trust bar ── */}
      <div className="trust">
        {[
          ['MoMo & Card',  'Payments accepted'],
          ['50–500+',      'Members by plan'],
          ['3 channels',   'Web, SMS & USSD access'],
          ['Data-led',     'AgroCredit decisions'],
        ].map(([v, l]) => (
          <div key={l} className="trust-item">
            <div className="trust-v">{v}</div>
            <div className="trust-l">{l}</div>
          </div>
        ))}
      </div>

      {/* ── Features ── */}
      <section className="sec">
        <Reveal className="sec-inner">
          <div className="sec-lbl">With AgroOS, cooperatives can</div>
          <h2 className="sec-h2 serif">Spend less time on paperwork<br />and more time supporting farmers</h2>
          <p className="sec-sub">
            One simple system for the day-to-day work that usually lives in paper records and Excel.
          </p>
          <div className="feat-grid">
            {FEATURES.map(([num, icon, title, desc, target]) => (
              <button key={num} className="feat-card feat-card--action" type="button" onClick={() => exploreFeature(target)}>
                <div className="feat-num mono">{num}</div>
                <div className="feat-icon">{icon}</div>
                <div className="feat-title serif">{title}</div>
                <div className="feat-desc">{desc}</div>
                <span className="feat-link">Explore capability <ArrowRight size={14} /></span>
              </button>
            ))}
          </div>
        </Reveal>
      </section>

      {/* ── How it works ── */}
      <section className="sec bg-sage">
        <Reveal className="sec-inner">
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
        </Reveal>
      </section>

      {/* ── Who it's for ── */}
      <section className="sec">
        <Reveal className="sec-inner">
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
        </Reveal>
      </section>

      {/* ── Moolre band + integration ── */}
      <div className="moolre-band">
        <Reveal className="moolre-inner">
          <div className="moolre-tag">Moolre integration</div>
          <h2 className="moolre-h2 serif">Built on Moolre.<br />Native from day one.</h2>
          <p className="moolre-desc">
            AgroOS uses Moolre's payment infrastructure natively — USSD menus, MoMo collections,
            and disbursements flow directly through the Moolre ecosystem. No third-party payment setup required.
          </p>
        </Reveal>

        <Reveal className="moolre-cards-wrap" id="moolre-integration">
          <h3 className="moolre-cards-heading serif">Explore the integration</h3>
          <p className="moolre-cards-sub">Four native capabilities — choose one to learn more.</p>
          <div className="moolre-cards">
            {MOOLRE_PILLARS.map((pillar) => (
              <button
                key={pillar.title}
                type="button"
                className="moolre-card"
                onClick={() => handlePillarClick(pillar)}
              >
                <div className="moolre-card-icon">{pillar.icon}</div>
                <div className="moolre-card-title serif">{pillar.title}</div>
                <p className="moolre-card-desc">{pillar.desc}</p>
                <span className="moolre-card-link">
                  Learn more <ArrowRight size={14} />
                </span>
              </button>
            ))}
          </div>
        </Reveal>
      </div>

      {/* ── Pricing bridge ── */}
      <section className="home-pricing">
        <Reveal className="home-pricing-inner">
          <div className="section-header">
            <div className="section-kicker">A clear path as you grow</div>
            <h2 className="sec-title serif">Start free. Add operational depth when you need it.</h2>
            <p className="sec-sub">Every route begins with the right commercial context—not a generic account screen.</p>
          </div>
          <div className="home-plan-grid">
            {[
              ['Starter', 'Free', 'Up to 50 members', 'Create free workspace', () => setPage('subscription', { plan: 'starter' })],
              ['Growth', 'GHS 299 / month', 'Up to 500 members', 'Review Growth', () => setPage('subscription', { plan: 'growth' })],
              ['Enterprise', 'Custom', 'Multi-team or programme rollout', 'Talk to enterprise sales', () => setPage('bookDemo', { plan: 'enterprise', topic: 'Enterprise implementation' })],
            ].map(([name, price, detail, label, action], index) => (
              <article key={name} className={`home-plan-card${index === 1 ? ' home-plan-card--featured' : ''}`}>
                <ReceiptText size={20} />
                <h3 className="serif">{name}</h3>
                <strong>{price}</strong>
                <p>{detail}</p>
                <button type="button" className="home-plan-action" onClick={action}>
                  {label} <ArrowRight size={14} />
                </button>
              </article>
            ))}
          </div>
          <button type="button" className="home-pricing-link" onClick={() => setPage('pricing')}>
            Compare all plans and terms <ArrowRight size={14} />
          </button>
        </Reveal>
      </section>

      {/* ── CTA ── */}
      <CTASection
        heading="Spend less time on paperwork.<br />More time supporting your farmers."
        subtext="Create a Starter workspace without a card, or speak with our team about a structured enterprise rollout."
        primaryLabel={user ? 'Go to dashboard' : 'Start with Starter'}
        secondaryLabel="Discuss enterprise rollout"
        onPrimary={() => (user ? setPage('dashboard') : setPage('subscription', { plan: 'starter' }))}
        onSecondary={() => setPage('bookDemo', { plan: 'enterprise', topic: 'Enterprise implementation' })}
      />
      </main>

      <Footer />
    </>
  )
}
