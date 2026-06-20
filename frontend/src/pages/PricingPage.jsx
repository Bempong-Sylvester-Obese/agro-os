// src/pages/PricingPage.jsx
import Footer from '../components/Footer'

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

export default function PricingPage({ setPage }) {
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
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 24, maxWidth: 960, margin: '0 auto' }}>
            {PLANS.map(({ name, price, sub, primary, features, cta }) => (
              <div
                key={name}
                style={{
                  background: primary ? 'var(--g)' : '#fff',
                  border: `1px solid ${primary ? 'var(--g)' : 'var(--border)'}`,
                  borderRadius: 16,
                  padding: '32px 28px',
                  display: 'flex',
                  flexDirection: 'column',
                  boxShadow: primary ? '0 24px 60px rgba(26,71,49,.2)' : 'none',
                  transform: primary ? 'translateY(-8px)' : 'none',
                }}
              >
                <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '.08em', textTransform: 'uppercase', color: primary ? 'var(--gold-l)' : 'var(--g)', marginBottom: 10 }}>
                  {name}
                </div>
                <div style={{ fontFamily: "'Fraunces',serif", fontSize: 40, fontWeight: 900, color: primary ? '#fff' : 'var(--g)', marginBottom: 4 }}>
                  {price}
                </div>
                <div style={{ fontSize: 13, color: primary ? 'rgba(255,255,255,.6)' : 'var(--muted)', marginBottom: 28 }}>
                  {sub}
                </div>

                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 28 }}>
                  {features.map((f) => (
                    <div key={f} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', fontSize: 13, color: primary ? 'rgba(255,255,255,.85)' : 'var(--text)' }}>
                      <span style={{ color: primary ? 'var(--gold-l)' : 'var(--gl)', marginTop: 2 }}>✓</span>
                      {f}
                    </div>
                  ))}
                </div>

                <button
                  style={{
                    background: primary ? 'var(--gold)' : 'none',
                    color: primary ? 'var(--g)' : 'var(--g)',
                    border: primary ? 'none' : '1.5px solid var(--g)',
                    padding: '12px 20px',
                    borderRadius: 10,
                    fontFamily: "'DM Sans',sans-serif",
                    fontSize: 14,
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  {cta}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      <Footer setPage={setPage} />
    </>
  )
}
