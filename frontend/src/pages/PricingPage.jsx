import { ArrowRight, Check, Headphones, LockKeyhole, ReceiptText, ShieldCheck } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import Footer from '../components/Footer'
import { Reveal } from '../components/Motion'

const PLANS = [
  {
    key: 'starter',
    name: 'Starter',
    eyebrow: 'For emerging cooperatives',
    price: 'Free',
    cadence: 'No card required',
    description: 'Establish a reliable digital member register and start collecting dues.',
    features: ['Up to 50 members', 'MoMo payment collection', 'Member and dues dashboard', '100 SMS messages per month', 'Email support'],
    cta: 'Create free workspace',
  },
  {
    key: 'growth',
    name: 'Growth',
    eyebrow: 'For operating cooperatives',
    price: 'GHS 299',
    cadence: 'per organisation / month',
    description: 'Run payments, credit workflows, communication, and field operations at scale.',
    features: ['Up to 500 members', 'Unlimited payment records', 'AgroCredit Trust Scores', '1,000 SMS messages per month', 'USSD access', 'Priority support'],
    cta: 'Start Growth onboarding',
    featured: true,
    badge: 'Most selected',
  },
  {
    key: 'enterprise',
    name: 'Enterprise',
    eyebrow: 'For networks and institutions',
    price: 'Custom',
    cadence: 'Annual agreement',
    description: 'A governed rollout for unions, lenders, NGOs, and multi-cooperative programmes.',
    features: ['Unlimited members', 'Multi-cooperative administration', 'Custom USSD and API access', 'Migration and implementation support', 'Dedicated account manager', 'Contracted SLA'],
    cta: 'Talk to enterprise sales',
  },
]

const COMPARISON = [
  ['Member capacity', '50', '500', 'Custom'],
  ['MoMo collections', 'Included', 'Included', 'Included'],
  ['AgroCredit scoring', '—', 'Included', 'Included'],
  ['USSD access', '—', 'Included', 'Custom'],
  ['API and integrations', '—', '—', 'Included'],
  ['Support', 'Email', 'Priority', 'Dedicated team'],
]

export default function PricingPage() {
  const navigate = useNavigate()

  function choosePlan(plan) {
    if (plan.key === 'enterprise') {
      navigate('/book-demo?plan=enterprise&topic=Enterprise+implementation')
      window.scrollTo({ top: 0, behavior: 'instant' })
      return
    }
    navigate(`/subscribe/${plan.key}`)
    window.scrollTo({ top: 0, behavior: 'instant' })
  }

  return (
    <>
      <main className="pricing-page">
        <section className="pricing-hero">
          <Reveal>
            <div className="pricing-kicker">Plans for every stage of operation</div>
            <h1 className="serif">Commercial terms that scale with your cooperative.</h1>
            <p>
              Start with core operations, move into connected financial workflows, and add
              enterprise governance when your programme requires it.
            </p>
            <div className="pricing-hero-notes">
              <span><Check size={14} /> Ghana cedi pricing</span>
              <span><Check size={14} /> No setup fee on self-serve plans</span>
              <span><Check size={14} /> Cancel monthly plans any time</span>
            </div>
          </Reveal>
        </section>

        <section className="pricing-plans-section">
          <div className="pricing-container">
            <div className="pricing-grid pricing-grid--business">
              {PLANS.map((plan) => (
                <article key={plan.key} className={`pricing-card pricing-card--business${plan.featured ? ' pricing-card--featured' : ''}`}>
                  {plan.badge && <div className="pricing-card__badge">{plan.badge}</div>}
                  <div className="pricing-card__eyebrow">{plan.eyebrow}</div>
                  <h2 className="pricing-card__name serif">{plan.name}</h2>
                  <div className="pricing-card__price">{plan.price}</div>
                  <div className="pricing-card__sub">{plan.cadence}</div>
                  <p className="pricing-card__description">{plan.description}</p>
                  <div className="pricing-card__divider" />
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
              ))}
            </div>

            <Reveal className="pricing-procurement">
              {[
                [ReceiptText, 'Clear commercial terms', 'A plan summary is shown before account creation. No surprise charges.'],
                [LockKeyhole, 'No payment details yet', 'Growth begins with onboarding; billing is activated only after the trial terms are confirmed.'],
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
            <div className="pricing-table-wrap">
              <table className="pricing-table">
                <thead>
                  <tr>
                    <th>Capability</th>
                    <th>Starter</th>
                    <th>Growth</th>
                    <th>Enterprise</th>
                  </tr>
                </thead>
                <tbody>
                  {COMPARISON.map(([capability, starter, growth, enterprise]) => (
                    <tr key={capability}>
                      <th>{capability}</th>
                      <td>{starter}</td>
                      <td>{growth}</td>
                      <td>{enterprise}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
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
            <button type="button" className="btn-gold" onClick={() => choosePlan(PLANS[2])}>
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
