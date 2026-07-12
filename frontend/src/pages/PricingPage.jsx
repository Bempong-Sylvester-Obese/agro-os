// src/pages/PricingPage.jsx
import CTASection from '../components/CTASection'
import Footer from '../components/Footer'
import { useAppNavigate } from '../hooks/useAppNavigate'

const PLANS = [
  {
    name: 'Starter',
    price: 'Free',
    sub: 'Forever free',
    primary: false,
    features: [
      'Up to 50 members',
      'MoMo payments',
      'Basic dashboard',
      'SMS broadcasts (100/mo)',
      'Email support',
    ],
    cta: 'Get started free',
  },
  {
    name: 'Growth',
    price: 'GHS 299',
    sub: 'per month',
    primary: true,
    features: [
      'Up to 500 members',
      'Unlimited payments',
      'AgroCredit scores',
      'SMS broadcasts (1,000/mo)',
      'USSD integration',
      'Priority support',
    ],
    cta: 'Start free trial',
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    sub: 'Talk to us',
    primary: false,
    features: [
      'Unlimited members',
      'Custom USSD menu',
      'API access',
      'Dedicated account manager',
      'White-label options',
      'SLA guarantee',
    ],
    cta: 'Contact sales',
  },
]

export default function PricingPage() {
  const setPage = useAppNavigate()

  function handlePlanCta(cta) {
    if (cta === 'Contact sales') {
      setPage('bookDemo')
      return
    }
    setPage('login', { loginMode: 'signup' })
  }

  return (
    <>
      <div className="sol-hero">
        <h1 className="sol-hero-h1 serif">Simple, transparent pricing</h1>
        <p className="sol-hero-sub">
          Start free. Pay only when your cooperative grows. No hidden fees, no surprises.
        </p>
      </div>

      <section className="sec">
        <div className="sec-inner">
          <div className="pricing-grid">
            {PLANS.map(({ name, price, sub, primary, features, cta }) => (
              <div
                key={name}
                className={`pricing-card${primary ? ' pricing-card--featured' : ''}`}
              >
                <div className="pricing-card__label">{name}</div>
                <div className="pricing-card__price">{price}</div>
                <div className="pricing-card__sub">{sub}</div>

                <div className="pricing-card__features">
                  {features.map((f) => (
                    <div key={f} className="pricing-card__feature">
                      <span className="pricing-card__check">✓</span>
                      {f}
                    </div>
                  ))}
                </div>

                <button
                  type="button"
                  className="pricing-card__btn"
                  onClick={() => handlePlanCta(cta)}
                >
                  {cta}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      <CTASection
        heading="Ready to modernize<br />your cooperative?"
        subtext="Join cooperatives across Ghana who've replaced paper with AgroOS. Start free, upgrade when you're ready."
        primaryLabel="Get started free"
        secondaryLabel="Book a demo"
        onPrimary={() => setPage('login', { loginMode: 'signup' })}
        onSecondary={() => setPage('bookDemo')}
      />

      <Footer />
    </>
  )
}
