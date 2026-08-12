import { ArrowRight, Check, Headphones, LockKeyhole, ReceiptText, ShieldCheck } from 'lucide-react'
import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Footer from '../components/Footer'
import { Reveal } from '../components/Motion'
import { fetchPlans } from '../api/plans'

export default function PricingPage() {
  const navigate = useNavigate()
  const [plans, setPlans] = useState([])
  const [bands, setBands] = useState({})

  useEffect(() => {
    fetchPlans().then(setPlans).catch(() => {})
  }, [])

  const tracks = useMemo(() => {
    const coop = plans.filter((p) => p.track === 'cooperative')
    const farmer = plans.filter((p) => p.track === 'farmer')
    return { cooperative: coop, farmer }
  }, [plans])

  function choosePlan(plan) {
    if (plan.key === 'enterprise') {
      navigate('/book-demo?plan=enterprise&topic=Enterprise+implementation')
      return
    }
    const band = bands[plan.key]
    navigate(`/subscribe/${plan.key}${band ? `?band=${band}` : ''}`)
  }

  function renderCard(plan) {
    const selectedKey = bands[plan.key]
    const band = plan.bands
      ? (plan.bands.find((b) => b.key === selectedKey) || plan.bands[0])
      : null
    const price = band ? `GHS ${band.price}` : plan.price
    return (
      <article key={plan.key} className={`pricing-card pricing-card--business${plan.featured ? ' pricing-card--featured' : ''}`}>
        {plan.badge && <div className="pricing-card__badge">{plan.badge}</div>}
        <div className="pricing-card__eyebrow">{plan.eyebrow}</div>
        <h2 className="pricing-card__name serif">{plan.name}</h2>
        <div className="pricing-card__price">{price}</div>
        <div className="pricing-card__sub">{band ? band.label : plan.cadence}</div>
        <p className="pricing-card__description">{plan.description}</p>
        <div className="pricing-card__divider" />
        {plan.bands && (
          <label className="pricing-band-select">
            <span>Choose your size</span>
            <select
              value={band.key}
              onChange={(e) => setBands((cur) => ({ ...cur, [plan.key]: e.target.value }))}
            >
              {plan.bands.map((b) => (
                <option key={b.key} value={b.key}>{b.label}</option>
              ))}
            </select>
          </label>
        )}
        <div className="pricing-card__includes">Plan includes</div>
        <div className="pricing-card__features">
          {plan.features.map((feature) => (
            <div key={feature} className="pricing-card__feature">
              <Check className="pricing-card__check" size={15} />
              {feature}
            </div>
          ))}
        </div>
        <button type="button" className="pricing-card__btn" onClick={() => choosePlan(plan)}>
          {plan.cta} <ArrowRight size={15} />
        </button>
      </article>
    )
  }

  return (
    <>
      <main className="pricing-page">
        <section className="pricing-hero">
          <Reveal>
            <div className="pricing-kicker">Plans for every stage of operation</div>
            <h1 className="serif">Commercial terms that scale with your cooperative.</h1>
            <p>Start with core operations, move into connected financial workflows, and add enterprise governance when your programme requires it.</p>
            <div className="pricing-hero-notes">
              <span><Check size={14} /> Ghana cedi pricing</span>
              <span><Check size={14} /> No setup fee on self-serve plans</span>
              <span><Check size={14} /> Cancel monthly plans any time</span>
            </div>
          </Reveal>
        </section>

        <section className="pricing-plans-section">
          <div className="pricing-container">
            <Reveal className="pricing-track-heading">
              <div className="pricing-kicker">Cooperative track</div>
              <h2 className="serif">For Cooperatives</h2>
            </Reveal>
            <div className="pricing-grid pricing-grid--business">
              {tracks.cooperative.map(renderCard)}
            </div>

            <Reveal className="pricing-track-heading pricing-track-heading--second">
              <div className="pricing-kicker">Farmer track</div>
              <h2 className="serif">For Independent Farmers</h2>
            </Reveal>
            <div className="pricing-grid pricing-grid--business">
              {tracks.farmer.map(renderCard)}
            </div>

            <Reveal className="pricing-procurement">
              {[
                [ReceiptText, 'Clear commercial terms', 'A plan summary is shown before account creation. No surprise charges.'],
                [LockKeyhole, 'Pay before you sign up', 'Paid plans complete checkout before account creation, so there are no unpaid workspaces.'],
                [Headphones, 'Implementation support', 'Enterprise engagements include migration, rollout planning, and operational support.'],
              ].map(([Icon, title, copy]) => (
                <div key={title}>
                  <Icon size={19} />
                  <strong>{title}</strong>
                  <p>{copy}</p>
                </div>
              ))}
            </Reveal>
          </div>
        </section>

        <section className="pricing-compare-section">
          <Reveal className="pricing-container">
            <div className="pricing-section-heading">
              <div className="pricing-kicker">Plan comparison</div>
              <h2 className="serif">Compare the operating model, not just the feature list.</h2>
            </div>
          </Reveal>
        </section>

        <section className="pricing-enterprise-band">
          <Reveal className="pricing-enterprise-inner">
            <div>
              <div className="pricing-kicker">Enterprise procurement</div>
              <h2 className="serif">Planning a multi-cooperative rollout?</h2>
              <p>Discuss migration, security review, API access, service levels, and programme governance with our team.</p>
            </div>
            <button type="button" className="btn-gold" onClick={() => choosePlan({ key: 'enterprise' })}>
              Start an enterprise conversation <ArrowRight size={16} />
            </button>
            <div className="pricing-enterprise-assurance"><ShieldCheck size={16} /> No generic signup. Your requirements are reviewed first.</div>
          </Reveal>
        </section>
      </main>
      <Footer />
    </>
  )
}
