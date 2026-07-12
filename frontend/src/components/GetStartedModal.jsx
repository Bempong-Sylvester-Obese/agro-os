// src/components/GetStartedModal.jsx
import { useState } from 'react'
import { signupAdmin, storeAuthToken } from '../api/auth'

const ALLOW_DEMO_LOGIN = import.meta.env.DEV || import.meta.env.VITE_ALLOW_DEMO_LOGIN === 'true'
const STEPS = ['Account', 'Cooperative', 'Done']

function buildUserFromForm(form) {
  const initials = form.name.trim().split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()
  return {
    name: form.name.trim(),
    initials,
    email: form.email.trim(),
    role: 'Field Officer',
    cooperative: form.cooperative.trim(),
  }
}

export default function GetStartedModal({ onClose, onSignIn, onAuth }) {
  const [step, setStep] = useState(0)
  const [form, setForm] = useState({
    name: '', email: '', password: '', confirmPassword: '',
    cooperative: '', region: 'Ashanti', size: '1-50',
  })
  const [err, setErr] = useState('')
  const [agreed, setAgreed] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [signedUpUser, setSignedUpUser] = useState(null)

  const REGIONS = ['Ashanti', 'Northern', 'Gr. Accra', 'Brong-Ahafo', 'Eastern', 'Volta', 'Western', 'Central', 'Upper East', 'Upper West']
  const SIZES = ['1-50', '51-200', '201-500', '500+']

  function handleField(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }))
    setErr('')
  }

  function next() {
    if (step === 0) {
      if (!form.name.trim()) { setErr('Full name is required.'); return }
      if (!form.email.trim()) { setErr('Email is required.'); return }
      if (form.password.length < 8) { setErr('Password must be at least 8 characters.'); return }
      if (form.password !== form.confirmPassword) { setErr('Passwords do not match.'); return }
    }
    setErr('')
    setStep((s) => s + 1)
  }

  async function createAccount() {
    if (!form.cooperative.trim()) { setErr('Cooperative name is required.'); return }
    if (!agreed) { setErr('Please agree to the terms to continue.'); return }

    setErr('')
    setSubmitting(true)

    try {
      const result = await signupAdmin({
        name: form.name.trim(),
        email: form.email.trim(),
        password: form.password,
        cooperative_name: form.cooperative.trim(),
      })
      storeAuthToken(result.access_token)
      setSignedUpUser({
        ...result.user,
        email: result.user?.email || form.email.trim(),
        cooperative: form.cooperative.trim(),
      })
      setStep(2)
      return
    } catch (err) {
      if (!ALLOW_DEMO_LOGIN) {
        setErr(err.message || 'Could not create account')
        return
      }
    } finally {
      setSubmitting(false)
    }

    setSignedUpUser(buildUserFromForm(form))
    setStep(2)
  }

  const planFeatures = [
    'Up to 50 members',
    'MoMo payment collection',
    'Basic dashboard & reports',
    'SMS broadcasts (100/month)',
    'USSD access for farmers',
    'Email support',
  ]

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal gs-modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 560 }}>
        <div className="modal-head">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <span style={{ background: 'var(--g)', color: '#fff', borderRadius: 6, padding: '2px 10px', fontSize: 11, fontWeight: 700, letterSpacing: '.04em' }}>FREE PLAN</span>
            </div>
            <div className="modal-title serif">{step === 2 ? "You're all set! 🎉" : 'Get started with AgroOS'}</div>
            <div className="modal-sub">
              {step === 0 && 'Create your free account. No credit card required.'}
              {step === 1 && 'Tell us about your cooperative so we can personalize your experience.'}
              {step === 2 && 'Your free account is ready. Start managing your cooperative today.'}
            </div>
          </div>
          <button type="button" className="modal-close" onClick={onClose}>✕</button>
        </div>

        {step < 2 && (
          <div style={{ display: 'flex', gap: 6, marginBottom: 24 }}>
            {STEPS.map((s, i) => (
              <div key={s} style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div style={{
                  height: 3,
                  borderRadius: 99,
                  background: i <= step ? 'var(--g)' : 'var(--border)',
                  transition: 'background 0.3s',
                }} />
                <div style={{ fontSize: 10, color: i <= step ? 'var(--g)' : 'var(--muted)', fontWeight: 600 }}>{s}</div>
              </div>
            ))}
          </div>
        )}

        {err && <div className="auth-error" style={{ margin: '0 0 16px' }}>{err}</div>}

        {step === 0 && (
          <div className="modal-form">
            <div className="modal-row">
              <div className="auth-field">
                <label className="auth-label">Full name *</label>
                <input className="auth-input" name="name" placeholder="e.g. Kwame Boateng" value={form.name} onChange={handleField} />
              </div>
              <div className="auth-field">
                <label className="auth-label">Work email *</label>
                <input className="auth-input" name="email" type="email" placeholder="you@yourco-op.gh" value={form.email} onChange={handleField} />
              </div>
            </div>
            <div className="modal-row">
              <div className="auth-field">
                <label className="auth-label">Password *</label>
                <input className="auth-input" name="password" type="password" placeholder="Min. 8 characters" value={form.password} onChange={handleField} />
              </div>
              <div className="auth-field">
                <label className="auth-label">Confirm password *</label>
                <input className="auth-input" name="confirmPassword" type="password" placeholder="Repeat password" value={form.confirmPassword} onChange={handleField} />
              </div>
            </div>

            <div style={{ background: 'var(--sage)', borderRadius: 10, padding: '14px 16px' }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--g)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 10 }}>What's included — Free plan</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 12px' }}>
                {planFeatures.map((f) => (
                  <div key={f} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text)' }}>
                    <span style={{ color: 'var(--gl)', fontSize: 13 }}>✓</span>{f}
                  </div>
                ))}
              </div>
            </div>

            <div className="modal-actions">
              <button type="button" className="btn-out-lg" style={{ fontSize: 13, padding: '10px 22px' }} onClick={onClose}>Cancel</button>
              <button type="button" className="btn-lg" style={{ fontSize: 13, padding: '10px 22px' }} onClick={next}>Continue →</button>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="modal-form">
            <div className="auth-field">
              <label className="auth-label">Cooperative name *</label>
              <input className="auth-input" name="cooperative" placeholder="e.g. Ashanti Farmers Co-op" value={form.cooperative} onChange={handleField} />
            </div>
            <div className="modal-row">
              <div className="auth-field">
                <label className="auth-label">Region</label>
                <select className="auth-input auth-select" name="region" value={form.region} onChange={handleField}>
                  {REGIONS.map((r) => <option key={r}>{r}</option>)}
                </select>
              </div>
              <div className="auth-field">
                <label className="auth-label">Cooperative size</label>
                <select className="auth-input auth-select" name="size" value={form.size} onChange={handleField}>
                  {SIZES.map((s) => <option key={s}>{s} members</option>)}
                </select>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', paddingTop: 4 }}>
              <input
                type="checkbox"
                id="terms"
                checked={agreed}
                onChange={(e) => { setAgreed(e.target.checked); setErr('') }}
                style={{ marginTop: 2, cursor: 'pointer', accentColor: 'var(--g)', width: 15, height: 15 }}
              />
              <label htmlFor="terms" style={{ fontSize: 12, color: 'var(--muted)', lineHeight: 1.5, cursor: 'pointer' }}>
                I agree to AgroOS's Terms of Service and Privacy Policy. I understand my data is processed within the Moolre ecosystem.
              </label>
            </div>

            <div className="modal-actions">
              <button type="button" className="btn-out-lg" style={{ fontSize: 13, padding: '10px 22px' }} onClick={() => { setStep(0); setErr('') }} disabled={submitting}>← Back</button>
              <button type="button" className="btn-lg" style={{ fontSize: 13, padding: '10px 22px' }} onClick={createAccount} disabled={submitting}>
                {submitting ? 'Creating account…' : 'Create account →'}
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div style={{ textAlign: 'center', padding: '8px 0 4px' }}>
            <div style={{ fontSize: 56, marginBottom: 16 }}>🌾</div>
            <div style={{ fontSize: 15, color: 'var(--text)', marginBottom: 6, fontWeight: 600 }}>
              Welcome to AgroOS, {form.name.split(' ')[0]}!
            </div>
            <div style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 24, lineHeight: 1.6 }}>
              Your cooperative <strong>{form.cooperative}</strong> is registered on the free plan.<br />
              Open your dashboard to get started.
            </div>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
              <button type="button" className="btn-out-lg" style={{ fontSize: 13, padding: '10px 22px' }} onClick={onClose}>Back to site</button>
              <button
                type="button"
                className="btn-lg"
                style={{ fontSize: 13, padding: '10px 22px' }}
                onClick={() => signedUpUser && onAuth(signedUpUser)}
                disabled={!signedUpUser}
              >
                Go to dashboard →
              </button>
            </div>
            <div style={{ marginTop: 16, fontSize: 11, color: 'var(--muted)' }}>
              Account created for <strong>{form.email}</strong>
            </div>
          </div>
        )}

        {step < 2 && (
          <div style={{ textAlign: 'center', marginTop: 16, fontSize: 12, color: 'var(--muted)' }}>
            Already have an account?{' '}
            <button type="button" onClick={onSignIn} style={{ background: 'none', border: 'none', color: 'var(--g)', fontWeight: 600, fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' }}>
              Sign in
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
