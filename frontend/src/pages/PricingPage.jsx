// src/pages/PricingPage.jsx
import { useState } from 'react'
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
    payable: false,
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
    payable: true,
    amount: 299,
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
    payable: false,
  },
]

function MoolrePayModal({ plan, onClose, onSuccess }) {
  const [step, setStep] = useState('method') // method | momo | card | processing | done
  const [momoNum, setMomoNum] = useState('')
  const [momoNetwork, setMomoNetwork] = useState('MTN')
  const [card, setCard] = useState({ number: '', expiry: '', cvv: '', name: '' })
  const [err, setErr] = useState('')

  function fmtCard(val) {
    return val.replace(/\D/g,'').slice(0,16).replace(/(.{4})/g,'$1 ').trim()
  }
  function fmtExpiry(val) {
    const d = val.replace(/\D/g,'').slice(0,4)
    return d.length > 2 ? d.slice(0,2)+'/'+d.slice(2) : d
  }

  function handleMomoPay() {
    if (!momoNum.match(/^0[2345679]\d{8}$/)) {
      setErr('Enter a valid 10-digit Ghana mobile number.')
      return
    }
    setErr('')
    setStep('processing')
    setTimeout(() => setStep('done'), 2800)
  }

  function handleCardPay() {
    const num = card.number.replace(/\s/g,'')
    if (num.length < 16) { setErr('Enter a valid 16-digit card number.'); return }
    if (!card.expiry.match(/^\d{2}\/\d{2}$/)) { setErr('Enter a valid expiry (MM/YY).'); return }
    if (card.cvv.length < 3) { setErr('Enter a valid CVV.'); return }
    if (!card.name.trim()) { setErr('Enter the cardholder name.'); return }
    setErr('')
    setStep('processing')
    setTimeout(() => setStep('done'), 3000)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 460 }}>
        {/* Header */}
        <div className="modal-head">
          <div>
            {/* Moolre logo mark */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <div style={{
                background: 'linear-gradient(135deg, #1a4731 0%, #52b788 100%)',
                borderRadius: 8, width: 32, height: 32,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 16,
              }}>💳</div>
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--g)', letterSpacing: '.04em', textTransform: 'uppercase' }}>Moolre Secure Checkout</div>
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Powered by Moolre Payment Gateway</div>
              </div>
            </div>
            <div className="modal-title serif">{plan.name} Plan</div>
            <div className="modal-sub">
              {step === 'done' ? 'Payment successful!' : `GHS ${plan.amount}/month · Billed monthly · Cancel anytime`}
            </div>
          </div>
          {step !== 'processing' && step !== 'done' && (
            <button className="modal-close" onClick={onClose}>✕</button>
          )}
        </div>

        {/* Order summary */}
        {step !== 'processing' && step !== 'done' && (
          <div style={{
            background: 'var(--sage)', borderRadius: 10, padding: '12px 16px',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            marginBottom: 20,
          }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>AgroOS {plan.name}</div>
              <div style={{ fontSize: 11, color: 'var(--muted)' }}>Monthly subscription</div>
            </div>
            <div style={{ fontFamily: "'Fraunces',serif", fontSize: 20, fontWeight: 900, color: 'var(--g)' }}>
              GHS {plan.amount}
            </div>
          </div>
        )}

        {err && <div className="auth-error" style={{ margin: '0 0 14px' }}>{err}</div>}

        {/* Method selection */}
        {step === 'method' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--muted)', marginBottom: 2 }}>SELECT PAYMENT METHOD</div>
            <button
              onClick={() => setStep('momo')}
              style={{
                display: 'flex', alignItems: 'center', gap: 14, padding: '14px 16px',
                border: '1.5px solid var(--border)', borderRadius: 10, background: '#fff',
                cursor: 'pointer', transition: 'all 0.15s', textAlign: 'left',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--g)'; e.currentTarget.style.background = 'var(--sage)' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.background = '#fff' }}
            >
              <div style={{ fontSize: 24 }}>📱</div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>Mobile Money (MoMo)</div>
                <div style={{ fontSize: 11, color: 'var(--muted)' }}>MTN, Vodafone Cash, AirtelTigo Money</div>
              </div>
              <span style={{ marginLeft: 'auto', color: 'var(--muted)', fontSize: 16 }}>›</span>
            </button>

            <button
              onClick={() => setStep('card')}
              style={{
                display: 'flex', alignItems: 'center', gap: 14, padding: '14px 16px',
                border: '1.5px solid var(--border)', borderRadius: 10, background: '#fff',
                cursor: 'pointer', transition: 'all 0.15s', textAlign: 'left',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--g)'; e.currentTarget.style.background = 'var(--sage)' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.background = '#fff' }}
            >
              <div style={{ fontSize: 24 }}>💳</div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>Debit / Credit Card</div>
                <div style={{ fontSize: 11, color: 'var(--muted)' }}>Visa, Mastercard, Verve</div>
              </div>
              <span style={{ marginLeft: 'auto', color: 'var(--muted)', fontSize: 16 }}>›</span>
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4, justifyContent: 'center' }}>
              <span style={{ fontSize: 12 }}>🔒</span>
              <span style={{ fontSize: 11, color: 'var(--muted)' }}>Secured by Moolre · 256-bit TLS encryption</span>
            </div>
          </div>
        )}

        {/* MoMo form */}
        {step === 'momo' && (
          <div className="modal-form">
            <div className="auth-field">
              <label className="auth-label">Mobile network</label>
              <div style={{ display: 'flex', gap: 8 }}>
                {['MTN', 'Vodafone', 'AirtelTigo'].map(n => (
                  <button
                    key={n}
                    onClick={() => setMomoNetwork(n)}
                    style={{
                      flex: 1, padding: '8px 4px', borderRadius: 8, fontSize: 12, fontWeight: 600,
                      border: momoNetwork === n ? '2px solid var(--g)' : '1.5px solid var(--border)',
                      background: momoNetwork === n ? 'var(--sage)' : '#fff',
                      color: momoNetwork === n ? 'var(--g)' : 'var(--text)',
                      cursor: 'pointer',
                    }}
                  >{n}</button>
                ))}
              </div>
            </div>
            <div className="auth-field">
              <label className="auth-label">Mobile Money number *</label>
              <input
                className="auth-input"
                placeholder="e.g. 0241234567"
                value={momoNum}
                onChange={e => { setMomoNum(e.target.value.replace(/\D/g,'').slice(0,10)); setErr('') }}
                maxLength={10}
              />
            </div>
            <div style={{ fontSize: 11, color: 'var(--muted)', padding: '4px 0', lineHeight: 1.5 }}>
              You will receive a USSD prompt on your phone to authorize the payment of <strong>GHS {plan.amount}</strong>.
            </div>
            <div className="modal-actions">
              <button className="btn-out-lg" style={{ fontSize: 13, padding: '10px 20px' }} onClick={() => { setStep('method'); setErr('') }}>← Back</button>
              <button className="btn-lg" style={{ fontSize: 13, padding: '10px 20px' }} onClick={handleMomoPay}>Pay GHS {plan.amount} →</button>
            </div>
          </div>
        )}

        {/* Card form */}
        {step === 'card' && (
          <div className="modal-form">
            <div className="auth-field">
              <label className="auth-label">Card number *</label>
              <input
                className="auth-input mono"
                placeholder="0000 0000 0000 0000"
                value={card.number}
                onChange={e => { setCard(c => ({ ...c, number: fmtCard(e.target.value) })); setErr('') }}
              />
            </div>
            <div className="auth-field">
              <label className="auth-label">Cardholder name *</label>
              <input
                className="auth-input"
                placeholder="Name on card"
                value={card.name}
                onChange={e => { setCard(c => ({ ...c, name: e.target.value })); setErr('') }}
              />
            </div>
            <div className="modal-row">
              <div className="auth-field">
                <label className="auth-label">Expiry *</label>
                <input
                  className="auth-input mono"
                  placeholder="MM/YY"
                  value={card.expiry}
                  onChange={e => { setCard(c => ({ ...c, expiry: fmtExpiry(e.target.value) })); setErr('') }}
                />
              </div>
              <div className="auth-field">
                <label className="auth-label">CVV *</label>
                <input
                  className="auth-input mono"
                  placeholder="•••"
                  type="password"
                  maxLength={4}
                  value={card.cvv}
                  onChange={e => { setCard(c => ({ ...c, cvv: e.target.value.replace(/\D/g,'').slice(0,4) })); setErr('') }}
                />
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {['visa','mc','verve'].map(b => (
                <div key={b} style={{
                  padding: '3px 8px', border: '1px solid var(--border)', borderRadius: 5,
                  fontSize: 10, fontWeight: 700, color: 'var(--muted)', letterSpacing: '.04em',
                }}>{b.toUpperCase()}</div>
              ))}
              <span style={{ fontSize: 11, color: 'var(--muted)', marginLeft: 4 }}>🔒 Encrypted</span>
            </div>
            <div className="modal-actions">
              <button className="btn-out-lg" style={{ fontSize: 13, padding: '10px 20px' }} onClick={() => { setStep('method'); setErr('') }}>← Back</button>
              <button className="btn-lg" style={{ fontSize: 13, padding: '10px 20px' }} onClick={handleCardPay}>Pay GHS {plan.amount} →</button>
            </div>
          </div>
        )}

        {/* Processing */}
        {step === 'processing' && (
          <div style={{ textAlign: 'center', padding: '24px 0' }}>
            <div style={{ fontSize: 40, marginBottom: 14, animation: 'spin 1.2s linear infinite', display: 'inline-block' }}>⏳</div>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>Processing payment…</div>
            <div style={{ fontSize: 12, color: 'var(--muted)' }}>Please do not close this window.</div>
            <div style={{ marginTop: 16, height: 4, background: 'var(--border)', borderRadius: 99, overflow: 'hidden' }}>
              <div style={{
                height: '100%', background: 'var(--g)', borderRadius: 99,
                animation: 'progress 2.8s ease forwards',
              }} />
            </div>
          </div>
        )}

        {/* Done */}
        {step === 'done' && (
          <div style={{ textAlign: 'center', padding: '8px 0 4px' }}>
            <div style={{ fontSize: 52, marginBottom: 12 }}>✅</div>
            <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 6, color: 'var(--g)' }}>Payment successful!</div>
            <div style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 24, lineHeight: 1.6 }}>
              Your <strong>AgroOS {plan.name}</strong> plan is now active.<br />
              A receipt has been sent to your registered email.
            </div>
            <div style={{
              background: 'var(--sage)', borderRadius: 10, padding: '12px 16px',
              fontSize: 12, color: 'var(--text)', marginBottom: 20, textAlign: 'left',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ color: 'var(--muted)' }}>Plan</span>
                <span style={{ fontWeight: 600 }}>AgroOS {plan.name}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ color: 'var(--muted)' }}>Amount paid</span>
                <span style={{ fontWeight: 600 }}>GHS {plan.amount}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--muted)' }}>Next billing date</span>
                <span style={{ fontWeight: 600 }}>Jul 27, 2026</span>
              </div>
            </div>
            <button className="btn-lg" style={{ width: '100%' }} onClick={onSuccess}>Go to dashboard →</button>
          </div>
        )}
      </div>
    </div>
  )
}

export default function PricingPage({ setPage, onGetStarted }) {
  const [payModal, setPayModal] = useState(null) // plan object or null

  function handlePlanCta(plan) {
    if (plan.name === 'Starter') {
      onGetStarted()
    } else if (plan.name === 'Growth') {
      setPayModal(plan)
    } else {
      setPage('book-demo')
    }
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
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 24, maxWidth: 960, margin: '0 auto' }}>
            {PLANS.map((plan) => {
              const { name, price, sub, primary, features, cta } = plan
              return (
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
                    onClick={() => handlePlanCta(plan)}
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
              )
            })}
          </div>
        </div>
      </section>

      <Footer setPage={setPage} onGetStarted={onGetStarted} />

      {payModal && (
        <MoolrePayModal
          plan={payModal}
          onClose={() => setPayModal(null)}
          onSuccess={() => { setPayModal(null); setPage('dashboard') }}
        />
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes progress { from { width: 0; } to { width: 100%; } }
      `}</style>
    </>
  )
}
