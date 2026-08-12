import React, { useEffect, useMemo, useState } from 'react'
import { ArrowLeft, ArrowRight, Building2, Check, ChevronRight, MapPin, ReceiptText, ShieldCheck, Users } from 'lucide-react'
import { Navigate, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Reveal } from '../components/Motion'
import { createPreCheckout, fetchPlans } from '../api/plans'

const MEMBER_OPTIONS = [
  { value: '25', label: '1–50 members' },
  { value: '125', label: '51–200 members' },
  { value: '350', label: '201–500 members' },
  { value: '750', label: '500+ members' },
]

export default function SubscriptionPage() {
  const { plan: planKey } = useParams()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [plans, setPlans] = useState([])
  const [step, setStep] = useState(0)
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    organisation: '',
    location: '',
    memberCount: '',
    role: 'Cooperative administrator',
  })

  useEffect(() => {
    fetchPlans().then(setPlans).catch(() => {})
  }, [])

  const plan = useMemo(() => plans.find((p) => p.key === planKey), [plans, planKey])
  const bandKey = searchParams.get('band')
  const band = useMemo(() => {
    if (!plan?.bands) return null
    return plan.bands.find((b) => b.key === bandKey) || plan.bands[0]
  }, [plan, bandKey])

  if (plans.length > 0 && !plan) return <Navigate to="/pricing" replace />

  function updateField(event) {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
    setError('')
  }

  function reviewOrder(event) {
    event.preventDefault()
    if (!form.organisation.trim() || !form.memberCount) {
      setError('Add your organisation and expected member count to continue.')
      return
    }
    setStep(1)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  async function continueToAccount() {
    const orgType = planKey === 'solo' ? 'solo_farm' : 'cooperative'
    if (planKey === 'starter') {
      const intent = { plan: planKey, ...form, org_type: orgType }
      window.sessionStorage.setItem('agroos-subscription-intent', JSON.stringify(intent))
      navigate(`/login?mode=signup&plan=${planKey}&onboarding=subscription`)
      return
    }

    setError('')
    try {
      const checkout = await createPreCheckout({
        plan_key: planKey,
        band: band?.key || null,
        organisation: form.organisation,
        location: form.location,
        member_count: Number(form.memberCount) || null,
        role: form.role,
        organization_type: orgType,
      })
      const intent = { plan: planKey, band: band?.key || null, ...form, org_type: orgType, checkout_ref: checkout.reference }
      window.sessionStorage.setItem('agroos-subscription-intent', JSON.stringify(intent))
      window.location.href = checkout.authorization_url
    } catch (err) {
      setError(err.message)
    }
  }

  if (!plan) return null

  const priceLabel = band ? `GHS ${band.price}` : plan.price

  return (
    <main className="subscribe-page">
      <section className="subscribe-aside">
        <button type="button" className="subscribe-back" onClick={() => navigate('/pricing')}>
          <ArrowLeft size={15} /> Back to pricing
        </button>
        <div className="subscribe-kicker">Selected plan</div>
        <h1 className="serif">{plan.name}</h1>
        <div className="subscribe-price">{priceLabel}</div>
        <div className="subscribe-cadence">{band ? band.label : plan.cadence}</div>
        <p className="subscribe-description">{plan.description}</p>
        <div className="subscribe-terms">
          {plan.features.map((term) => <div key={term}><Check size={15} /> {term}</div>)}
        </div>
        <div className="subscribe-safety">
          <ShieldCheck size={18} />
          <div>
            <strong>Commercially transparent</strong>
            <p>You will review the selected plan and pay before creating an administrator account.</p>
          </div>
        </div>
      </section>

      <section className="subscribe-content">
        <Reveal className="subscribe-panel">
          <div className="subscribe-progress" aria-label={`Step ${step + 1} of 2`}>
            <span className="active">1</span><i className={step === 1 ? 'complete' : ''} /><span className={step === 1 ? 'active' : ''}>2</span>
          </div>

          {step === 0 ? (
            <>
              <div className="subscribe-heading">
                <div className="subscribe-kicker">Organisation profile</div>
                <h2 className="serif">Set up your subscription workspace.</h2>
                <p>This information prepares the correct workspace and account path for your team.</p>
              </div>

              {error && <div className="auth-error subscribe-error" role="alert">{error}</div>}

              <form onSubmit={reviewOrder} className="subscribe-form">
                <label className="demo-field">
                  <span><Building2 size={14} /> Organisation name *</span>
                  <input className="auth-input" name="organisation" value={form.organisation} onChange={updateField} placeholder="Ashanti Farmers Cooperative" required />
                </label>
                <label className="demo-field">
                  <span><MapPin size={14} /> Primary location</span>
                  <input className="auth-input" name="location" value={form.location} onChange={updateField} placeholder="Kumasi, Ashanti Region" />
                </label>
                <label className="demo-field">
                  <span><Users size={14} /> Expected member count *</span>
                  <select className="auth-input auth-select" name="memberCount" value={form.memberCount} onChange={updateField} required>
                    <option value="">Select organisation size</option>
                    {MEMBER_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                  </select>
                </label>
                <label className="demo-field">
                  <span>Your role</span>
                  <select className="auth-input auth-select" name="role" value={form.role} onChange={updateField}>
                    {['Cooperative administrator', 'Executive or board member', 'Finance or operations lead', 'Programme manager', 'Technology partner'].map((role) => <option key={role}>{role}</option>)}
                  </select>
                </label>
                <button type="submit" className="btn-lg subscribe-primary">
                  Review plan and terms <ArrowRight size={16} />
                </button>
              </form>
            </>
          ) : (
            <>
              <button type="button" className="subscribe-inline-back" onClick={() => setStep(0)}>
                <ArrowLeft size={14} /> Edit organisation details
              </button>
              <div className="subscribe-heading">
                <div className="subscribe-kicker">Order summary</div>
                <h2 className="serif">Confirm your onboarding path.</h2>
                <p>You will be charged once, securely, before account creation.</p>
              </div>

              <div className="subscribe-summary">
                <div className="subscribe-summary-plan">
                  <div>
                    <span>Plan</span>
                    <strong>{plan.name}</strong>
                  </div>
                  <div className="subscribe-summary-price">
                    <strong>{priceLabel}</strong>
                    <span>/ month</span>
                  </div>
                </div>
                <div className="subscribe-summary-row"><span>Organisation</span><strong>{form.organisation}</strong></div>
                <div className="subscribe-summary-row"><span>Member profile</span><strong>{MEMBER_OPTIONS.find((option) => option.value === form.memberCount)?.label}</strong></div>
                <div className="subscribe-summary-row"><span>Billing today</span><strong>{priceLabel}</strong></div>
              </div>

              <div className="subscribe-next">
                <ReceiptText size={18} />
                <div>
                  <strong>{planKey === 'starter' ? 'Next: secure account setup' : 'Next: secure payment'}</strong>
                  <p>{planKey === 'starter' ? 'Create the administrator credentials for your workspace.' : 'Pay securely via Moolre, then create your administrator account.'}</p>
                </div>
                <ChevronRight size={18} />
              </div>

              {error && <div className="auth-error subscribe-error" role="alert">{error}</div>}

              <button type="button" className="btn-lg subscribe-primary" onClick={continueToAccount}>
                {planKey === 'starter' ? 'Start free workspace' : `Pay ${priceLabel}`} <ArrowRight size={16} />
              </button>
            </>
          )}
        </Reveal>
      </section>
    </main>
  )
}
