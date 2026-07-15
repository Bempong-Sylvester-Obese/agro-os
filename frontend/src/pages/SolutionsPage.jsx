// src/pages/SolutionsPage.jsx
import React from 'react'
import { ArrowRight, BarChart3, CheckCircle2, CreditCard, Megaphone, ShieldCheck, Smartphone, Users } from 'lucide-react'
import Footer from '../components/Footer'
import CTASection from '../components/CTASection'
import { Reveal } from '../components/Motion'
import { useAppNavigate } from '../hooks/useAppNavigate'

const OUTCOMES = [
  [Users, 'Cooperative administrators', 'Keep member, payment, production, and communication records connected instead of split across ledgers and spreadsheets.'],
  [Smartphone, 'Farmers and field teams', 'Reach essential services through web, SMS, and a Moolre USSD session when mobile data is unavailable.'],
  [BarChart3, 'Finance and programme teams', 'Review auditable activity and data-led credit signals before making operational or lending decisions.'],
]

export default function SolutionsPage({ user }) {
  const setPage = useAppNavigate()

  function openWorkspace(section) {
    if (user) {
      setPage('dashboard', section ? { dashboardSection: section } : undefined)
      return
    }
    setPage('subscription', { plan: 'starter' })
  }

  return (
    <>
      <main className="solutions-page">
        <section className="sol-hero">
          <Reveal className="sol-hero-inner">
            <div className="sol-tag">Connected agricultural operations</div>
            <h1 className="sol-hero-h1 serif">One operating system.<br />Clear outcomes for every role.</h1>
            <p className="sol-hero-sub">
              AgroOS connects cooperative administration, farmer access, payments, communications,
              and data-led credit workflows without assuming every member owns a smartphone.
            </p>
            <div className="sol-hero-actions">
              <button className="btn-lg" type="button" onClick={() => setPage('subscription', { plan: 'starter' })}>
                Create free workspace
              </button>
              <button className="btn-out-lg" type="button" onClick={() => setPage('bookDemo', { enterprise: true, topic: 'Solutions consultation' })}>
                Discuss enterprise rollout
              </button>
            </div>
          </Reveal>
        </section>

        <section className="sol-sec">
          <Reveal className="sol-inner">
            <div>
              <div className="sol-tag">Cooperative operations</div>
              <h2 className="sol-h2 serif">Replace fragmented administration with one accountable workspace.</h2>
              <p className="sol-desc">
                Keep member profiles, dues, production records, disbursements, and announcements in one operating view.
                Teams can see what happened, who initiated it, and what needs attention next.
              </p>
              <button className="btn-sol" type="button" onClick={() => openWorkspace()}>
                {user ? 'Open cooperative workspace' : 'Start with the free workspace'} <ArrowRight size={15} />
              </button>
            </div>
            <div className="sol-visual sol-operations-card">
              <div className="sol-visual-title">One operational record</div>
              {[
                [Users, 'Member administration', 'Profiles, roles and dues status'],
                [CreditCard, 'Financial operations', 'Collections, disbursements and receipts'],
                [Megaphone, 'Member communication', 'Announcements across dashboard, SMS and USSD'],
                [ShieldCheck, 'Decision support', 'Production history and credit signals'],
              ].map(([Icon, name, detail]) => (
                <div key={name} className="sol-capability-row">
                  <span><Icon size={17} /></span>
                  <div><strong>{name}</strong><small>{detail}</small></div>
                  <CheckCircle2 size={16} />
                </div>
              ))}
            </div>
          </Reveal>
        </section>

        <section className="sol-sec sol-ussd-section" id="ussd-section">
          <Reveal className="sol-inner rev">
            <div>
              <div className="sol-tag">Farmer access through Moolre</div>
              <h2 className="sol-h2 serif">Essential services without a smartphone or mobile data.</h2>
              <p className="sol-desc">
                Registered farmers can check active loan balances, pay cooperative dues through MoMo,
                and view announcements from a Moolre merchant-code session. Announcements may also be sent by SMS.
              </p>
              <div className="ussd-flow-notes">
                <div><strong>Loan balance</strong><span>Returns the farmer's active disbursed-loan total, or confirms that no active loan exists.</span></div>
                <div><strong>Dues payment</strong><span>Requests a GHS amount, then starts the MoMo collection and asks for an OTP when verification is required.</span></div>
              </div>
            </div>
            <div className="ussd-device-wrap">
              <div className="ussd-session-label"><span /> Moolre merchant-code session</div>
              <div className="ussd-phone" aria-label="AgroOS USSD main menu preview">
                <div className="ussd-speaker" />
                <div className="ussd-screen">
                  <div className="ussd-t">Welcome to AgroOS</div>
                  <div className="ussd-line">1. Check Loan Balance</div>
                  <div className="ussd-line">2. Pay Dues</div>
                  <div className="ussd-line">3. Announcements</div>
                  <div className="ussd-dim">Reply 1–3</div>
                </div>
                <div className="ussd-keypad" aria-hidden="true">
                  {['1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', '#'].map((key) => <i key={key}>{key}</i>)}
                </div>
              </div>
            </div>
          </Reveal>
        </section>

        <section className="solution-outcomes">
          <Reveal className="solution-outcomes-inner">
            <div className="section-header">
              <div className="section-kicker">Role-based outcomes</div>
              <h2 className="sec-title serif">Shared infrastructure, appropriate access.</h2>
            </div>
            <div className="solution-outcome-grid">
              {OUTCOMES.map(([Icon, title, text]) => (
                <article key={title} className="solution-outcome-card">
                  <Icon size={22} />
                  <h3 className="serif">{title}</h3>
                  <p>{text}</p>
                </article>
              ))}
            </div>
          </Reveal>
        </section>

        <section className="sol-sec">
          <Reveal className="sol-inner">
            <div>
              <div className="sol-tag">Lenders & programme teams</div>
              <h2 className="sol-h2 serif">Use operating history to support better credit decisions.</h2>
              <p className="sol-desc">
                AgroCredit Trust Scores combine available payment, production, repayment, attendance, and tenure data.
                They support review workflows; they do not replace responsible underwriting.
              </p>
              <button className="btn-sol" type="button" onClick={() => openWorkspace('scores')}>
                {user ? 'Review AgroCredit workspace' : 'Explore plans'} <ArrowRight size={15} />
              </button>
            </div>
            <div className="sol-visual sol-credit-card">
              <div className="sol-visual-title">Decision-support profile</div>
              <div className="sol-credit-score"><strong>Data-led</strong><span>multi-factor assessment</span></div>
              {['Payment and repayment history', 'Production records', 'Attendance and cooperative tenure'].map((item) => (
                <div key={item} className="sol-credit-factor"><CheckCircle2 size={16} /> {item}</div>
              ))}
              <p>Scores provide context for human review and lending policy.</p>
            </div>
          </Reveal>
        </section>

        <CTASection
          heading="Choose the right operating path"
          subtext="Start with a no-card Starter workspace or plan an enterprise rollout with our team."
          primaryLabel="See pricing"
          secondaryLabel="Talk to enterprise sales"
          onPrimary={() => setPage('pricing')}
          onSecondary={() => setPage('bookDemo', { enterprise: true, topic: 'Enterprise solutions' })}
        />
      </main>

      <Footer />
    </>
  )
}
