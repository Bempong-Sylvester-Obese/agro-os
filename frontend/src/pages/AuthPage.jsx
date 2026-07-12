import { useEffect, useId, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { login, signup, storeAuthToken, userFromAuthToken, userFromSignupResponse, warmAuthBackend } from '../api/auth'
import { USERS } from '../data/users'
import { Sprout, ArrowLeft, ArrowRight, Building2, Users, MapPin, Mail, Lock, Eye, EyeOff, CheckCircle2 } from 'lucide-react'

const ALLOW_DEMO_LOGIN = import.meta.env.DEV || import.meta.env.VITE_ALLOW_DEMO_LOGIN === 'true'

// ---------------------------------------------------------------------------
// Step indicators
// ---------------------------------------------------------------------------
function StepDots({ total, current }) {
  return (
    <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginBottom: 32 }}>
      {Array.from({ length: total }).map((_, i) => (
        <div
          key={i}
          style={{
            width: i === current ? 24 : 8,
            height: 8,
            borderRadius: 99,
            background: i === current ? 'var(--g)' : i < current ? 'var(--gl)' : 'var(--border)',
            transition: 'all 0.3s ease',
          }}
        />
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Styled input with icon
// ---------------------------------------------------------------------------
function Field({ id, label, icon: Icon, type = 'text', value, onChange, placeholder, required, rightEl }) {
  const generatedId = useId()
  const fieldId = id || `auth-field-${generatedId.replace(/:/g, '')}`

  return (
    <div style={{ marginBottom: 16 }}>
      <label htmlFor={fieldId} style={{ display: 'block', marginBottom: 6, fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>
        {label}
      </label>
      <div style={{ position: 'relative' }}>
        {Icon && (
          <Icon
            size={16}
            style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--muted)' }}
          />
        )}
        <input
          id={fieldId}
          type={type}
          className="auth-input"
          value={value}
          onChange={onChange}
          required={required}
          placeholder={placeholder}
          style={{
            width: '100%',
            padding: Icon ? '11px 12px 11px 38px' : '11px 12px',
            paddingRight: rightEl ? 44 : 12,
            border: '1.5px solid var(--border)',
            borderRadius: 8,
            fontSize: 14,
            fontFamily: "'DM Sans', sans-serif",
            background: '#fff',
            color: 'var(--text)',
            outline: 'none',
            transition: 'border-color 0.2s',
          }}
          onFocus={e => (e.target.style.borderColor = 'var(--g)')}
          onBlur={e => (e.target.style.borderColor = 'var(--border)')}
        />
        {rightEl && (
          <div style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)' }}>
            {rightEl}
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Size option pills
// ---------------------------------------------------------------------------
const SIZE_OPTIONS = [
  { label: '1–10', value: 5 },
  { label: '11–50', value: 25 },
  { label: '51–200', value: 100 },
  { label: '200+', value: 250 },
]

function SizePills({ value, onChange }) {
  return (
    <fieldset style={{ margin: 0, marginBottom: 16, padding: 0, border: 0 }}>
      <legend style={{ display: 'block', marginBottom: 8, fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>
        Cooperative size (members)
      </legend>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        {SIZE_OPTIONS.map(opt => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            aria-pressed={value === opt.value}
            style={{
              padding: '10px 0',
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,
              fontFamily: "'DM Sans', sans-serif",
              cursor: 'pointer',
              transition: 'all 0.18s',
              border: value === opt.value ? '2px solid var(--g)' : '1.5px solid var(--border)',
              background: value === opt.value ? 'rgba(26,71,49,0.07)' : '#fff',
              color: value === opt.value ? 'var(--g)' : 'var(--muted)',
            }}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </fieldset>
  )
}

// ---------------------------------------------------------------------------
// Main AuthPage
// ---------------------------------------------------------------------------
export default function AuthPage({ onAuth }) {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const initialLogin = searchParams.get('mode') !== 'signup'
  const [isLogin, setIsLogin] = useState(initialLogin)
  const [step, setStep] = useState(0) // 0 = coop info, 1 = account creds

  // Login fields
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)

  // Signup-specific fields
  const [cooperativeName, setCooperativeName] = useState('')
  const [location, setLocation] = useState('')
  const [memberCount, setMemberCount] = useState(null)
  const [signupEmail, setSignupEmail] = useState('')
  const [signupPassword, setSignupPassword] = useState('')
  const [showSignupPw, setShowSignupPw] = useState(false)

  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [backendWarming, setBackendWarming] = useState(false)

  useEffect(() => {
    let mounted = true
    setBackendWarming(true)
    warmAuthBackend().finally(() => {
      if (mounted) setBackendWarming(false)
    })
    return () => { mounted = false }
  }, [])

  useEffect(() => {
    setIsLogin(searchParams.get('mode') !== 'signup')
    setError(null)
    setStep(0)
    setSuccess(false)
  }, [searchParams])

  function completeAuth(tokenPayload, extras = {}) {
    const apiUser = tokenPayload.user || userFromAuthToken(tokenPayload.access_token)
    onAuth({
      ...(apiUser || {}),
      ...extras,
    })
  }

  // ── LOGIN ──────────────────────────────────────────────────────────────────
  const handleLogin = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const data = await login(email, password)
      storeAuthToken(data.access_token)
      completeAuth(data, {
        email: data.user?.email || email.trim(),
        cooperative_id: data.user?.cooperative_id ?? userFromAuthToken(data.access_token)?.cooperative_id ?? null,
        cooperative: data.user?.cooperative || 'Kuapa Kokoo Demo Cooperative',
      })
      return
    } catch (err) {
      if (!ALLOW_DEMO_LOGIN) {
        setError(err.message)
        return
      }
    } finally {
      setLoading(false)
    }

    const demoUser = USERS.find(
      u => u.email.toLowerCase() === email.trim().toLowerCase() && u.password === password
    )
    if (!demoUser) {
      setError('Invalid email or password. Try kwabena@ashantifarmers.gh / harvest2026 when the API is unavailable.')
      return
    }
    onAuth(demoUser)
  }

  // ── SIGNUP step 0 → 1 ─────────────────────────────────────────────────────
  const handleNextStep = (e) => {
    e.preventDefault()
    if (!cooperativeName.trim()) {
      setError('Please enter your cooperative or farm name.')
      return
    }
    setError(null)
    setStep(1)
  }

  // ── SIGNUP final submit ────────────────────────────────────────────────────
  const handleSignup = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const data = await signup({
        email: signupEmail,
        password: signupPassword,
        cooperativeName,
        location: location || undefined,
        memberCount: memberCount || undefined,
      })
      storeAuthToken(data.access_token)
      setSuccess(true)
      setTimeout(() => {
        completeAuth(data, userFromSignupResponse(data, signupEmail.trim()))
      }, 1200)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // ── Switch mode helper ─────────────────────────────────────────────────────
  const switchMode = () => {
    const nextLogin = !isLogin
    setIsLogin(nextLogin)
    setError(null)
    setStep(0)
    setSuccess(false)
    const params = new URLSearchParams()
    if (!nextLogin) params.set('mode', 'signup')
    const next = searchParams.get('next')
    if (next) params.set('next', next)
    const search = params.toString() ? `?${params.toString()}` : ''
    navigate(`/login${search}`, { replace: true })
  }

  // ── Background panel illustration ─────────────────────────────────────────
  const panelItems = [
    { icon: Building2, text: 'Create your cooperative profile' },
    { icon: Users, text: 'Manage members & dues' },
    { icon: Sprout, text: 'Track harvests & trust scores' },
  ]

  return (
    <div
      style={{
        display: 'flex',
        minHeight: '100vh',
        background: 'var(--cream)',
        alignItems: 'stretch',
      }}
    >
      {/* ── Left panel (decorative, hidden on small) ── */}
      <div
        style={{
          flex: '0 0 42%',
          background: 'linear-gradient(160deg, var(--g) 0%, var(--gm) 60%, #3A7D5C 100%)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '60px 48px',
          position: 'relative',
          overflow: 'hidden',
        }}
        className="auth-brand-panel"
      >
        {/* decorative blobs */}
        <div style={{
          position: 'absolute', top: -80, right: -80,
          width: 280, height: 280,
          borderRadius: '50%',
          background: 'rgba(255,255,255,0.06)',
        }} />
        <div style={{
          position: 'absolute', bottom: -60, left: -60,
          width: 220, height: 220,
          borderRadius: '50%',
          background: 'rgba(255,255,255,0.05)',
        }} />

        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 56 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 10,
            background: 'rgba(255,255,255,0.15)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Sprout size={22} color="#fff" />
          </div>
          <span style={{ color: '#fff', fontWeight: 700, fontSize: 20, letterSpacing: '-0.3px' }}>AgroOS</span>
        </div>

        <h2
          className="serif"
          style={{ color: '#fff', fontSize: 32, lineHeight: 1.25, marginBottom: 12, fontWeight: 600 }}
        >
          {isLogin ? 'Welcome back to your cooperative' : 'Digital infrastructure for African farmers'}
        </h2>
        <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: 15, lineHeight: 1.65, marginBottom: 48 }}>
          {isLogin
            ? 'Log in to manage members, track payments, and broadcast updates across your cooperative.'
            : 'Join hundreds of cooperatives already replacing paper ledgers with AgroOS.'}
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {panelItems.map(({ icon: Icon, text }) => (
            <div key={text} style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
              <div style={{
                width: 36, height: 36, borderRadius: 8,
                background: 'rgba(255,255,255,0.12)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0,
              }}>
                <Icon size={17} color="rgba(255,255,255,0.9)" />
              </div>
              <span style={{ color: 'rgba(255,255,255,0.85)', fontSize: 14, fontWeight: 500 }}>{text}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Right panel (form) ── */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '40px 24px',
        }}
      >
        <div style={{ width: '100%', maxWidth: 420 }}>

          {/* ── Success state ── */}
          {success && (
            <div style={{ textAlign: 'center' }}>
              <div style={{
                width: 72, height: 72, borderRadius: '50%',
                background: 'rgba(82,183,136,0.15)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                margin: '0 auto 20px',
              }}>
                <CheckCircle2 size={36} color="var(--gl)" />
              </div>
              <h2 className="serif" style={{ fontSize: 26, marginBottom: 8 }}>All set! 🎉</h2>
              <p style={{ color: 'var(--muted)', fontSize: 14 }}>Redirecting you to your dashboard…</p>
            </div>
          )}

          {/* ── LOGIN FORM ── */}
          {!success && isLogin && (
            <>
              <h2 className="serif" style={{ fontSize: 28, marginBottom: 6 }}>Sign in</h2>
              <p style={{ color: 'var(--muted)', fontSize: 14, marginBottom: 32 }}>
                Access your cooperative dashboard
              </p>

              {backendWarming && !error && (
                <div className="info-banner" style={{ marginBottom: 20, fontSize: 13 }}>
                  Connecting to AgroOS servers… first sign-in after idle may take up to a minute.
                </div>
              )}

              {error && (
                <div style={{
                  padding: '10px 14px', backgroundColor: '#FEF2F2', color: '#991B1B',
                  borderRadius: 8, marginBottom: 20, fontSize: 13, borderLeft: '3px solid #F87171',
                }}>
                  {error}
                </div>
              )}

              <form onSubmit={handleLogin}>
                <Field
                  label="Email address"
                  icon={Mail}
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@cooperative.com"
                  required
                />
                <Field
                  label="Password"
                  icon={Lock}
                  type={showPw ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  rightEl={
                    <button
                      type="button"
                      onClick={() => setShowPw(!showPw)}
                      aria-label={showPw ? 'Hide password' : 'Show password'}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', padding: 0 }}
                    >
                      {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  }
                />

                <button
                  type="submit"
                  className="btn-lg"
                  disabled={loading}
                  style={{ width: '100%', marginTop: 8, justifyContent: 'center', display: 'flex' }}
                >
                  {loading ? 'Signing in…' : 'Sign in →'}
                </button>
              </form>

              {ALLOW_DEMO_LOGIN && (
                <div style={{
                  marginTop: 20, padding: '12px 14px', borderRadius: 8,
                  background: 'var(--sage)', fontSize: 12, color: 'var(--muted)', lineHeight: 1.5,
                }}>
                  <strong style={{ display: 'block', color: 'var(--text)', marginBottom: 4 }}>Demo credentials</strong>
                  kwabena@ashantifarmers.gh / harvest2026
                </div>
              )}
            </>
          )}

          {/* ── SIGNUP STEP 0: Cooperative info ── */}
          {!success && !isLogin && step === 0 && (
            <>
              <StepDots total={2} current={0} />
              <h2 className="serif" style={{ fontSize: 26, marginBottom: 6 }}>About your cooperative</h2>
              <p style={{ color: 'var(--muted)', fontSize: 14, marginBottom: 28 }}>
                Tell us about your farm or cooperative to get started.
              </p>

              {backendWarming && !error && (
                <div className="info-banner" style={{ marginBottom: 20, fontSize: 13 }}>
                  Connecting to AgroOS servers… first sign-up after idle may take up to a minute.
                </div>
              )}

              {error && (
                <div style={{
                  padding: '10px 14px', backgroundColor: '#FEF2F2', color: '#991B1B',
                  borderRadius: 8, marginBottom: 20, fontSize: 13, borderLeft: '3px solid #F87171',
                }}>
                  {error}
                </div>
              )}

              <form onSubmit={handleNextStep}>
                <Field
                  label="Cooperative / farm name *"
                  icon={Building2}
                  value={cooperativeName}
                  onChange={e => setCooperativeName(e.target.value)}
                  placeholder="e.g. Tamale Farmers Union"
                  required
                />
                <Field
                  label="Location (optional)"
                  icon={MapPin}
                  value={location}
                  onChange={e => setLocation(e.target.value)}
                  placeholder="e.g. Northern Region, Ghana"
                />
                <SizePills value={memberCount} onChange={setMemberCount} />

                <button
                  type="submit"
                  className="btn-lg"
                  style={{ width: '100%', marginTop: 8, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 8 }}
                >
                  Continue <ArrowRight size={16} />
                </button>
              </form>
            </>
          )}

          {/* ── SIGNUP STEP 1: Account credentials ── */}
          {!success && !isLogin && step === 1 && (
            <>
              <StepDots total={2} current={1} />

              <button
                onClick={() => { setStep(0); setError(null) }}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', fontSize: 13, marginBottom: 20, display: 'flex', alignItems: 'center', gap: 6, padding: 0 }}
              >
                <ArrowLeft size={14} /> Back
              </button>

              <h2 className="serif" style={{ fontSize: 26, marginBottom: 4 }}>Create your account</h2>
              <p style={{ color: 'var(--muted)', fontSize: 14, marginBottom: 4 }}>
                Admin account for <strong style={{ color: 'var(--g)' }}>{cooperativeName}</strong>
              </p>
              <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 28 }}>
                You'll manage everything from here.
              </p>

              {error && (
                <div style={{
                  padding: '10px 14px', backgroundColor: '#FEF2F2', color: '#991B1B',
                  borderRadius: 8, marginBottom: 20, fontSize: 13, borderLeft: '3px solid #F87171',
                }}>
                  {error}
                </div>
              )}

              <form onSubmit={handleSignup}>
                <Field
                  label="Email address"
                  icon={Mail}
                  type="email"
                  value={signupEmail}
                  onChange={e => setSignupEmail(e.target.value)}
                  placeholder="you@cooperative.com"
                  required
                />
                <Field
                  label="Password"
                  icon={Lock}
                  type={showSignupPw ? 'text' : 'password'}
                  value={signupPassword}
                  onChange={e => setSignupPassword(e.target.value)}
                  placeholder="Create a strong password"
                  required
                  rightEl={
                    <button
                      type="button"
                      onClick={() => setShowSignupPw(!showSignupPw)}
                      aria-label={showSignupPw ? 'Hide password' : 'Show password'}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', padding: 0 }}
                    >
                      {showSignupPw ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  }
                />

                <div style={{
                  background: 'rgba(26,71,49,0.06)', borderRadius: 8, padding: '10px 14px',
                  fontSize: 12, color: 'var(--muted)', marginBottom: 16,
                }}>
                  🔒 Your account will have full admin access to <strong>{cooperativeName}</strong>
                  {memberCount ? ` (≈${memberCount} members)` : ''}
                  {location ? ` in ${location}` : ''}.
                </div>

                <button
                  type="submit"
                  className="btn-lg"
                  disabled={loading}
                  style={{ width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 8 }}
                >
                  {loading ? 'Creating account…' : 'Get started free →'}
                </button>
              </form>
            </>
          )}

          {/* ── Toggle login/signup ── */}
          {!success && (
            <div style={{ marginTop: 28, textAlign: 'center', fontSize: 14, color: 'var(--muted)' }}>
              {isLogin ? "Don't have an account? " : 'Already have an account? '}
              <button
                onClick={switchMode}
                style={{ background: 'none', border: 'none', color: 'var(--g)', fontWeight: 700, cursor: 'pointer', fontSize: 14 }}
              >
                {isLogin ? 'Sign up free' : 'Log in'}
              </button>
            </div>
          )}

          {!success && (
            <div style={{ marginTop: 12, textAlign: 'center' }}>
              <button
                onClick={() => navigate('/')}
                style={{ background: 'none', border: 'none', color: 'var(--muted)', fontSize: 12, cursor: 'pointer', textDecoration: 'underline' }}
              >
                ← Return to website
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Hide left panel on mobile */}
      <style>{`
        @media (max-width: 700px) { .auth-brand-panel { display: none; } }
      `}</style>
    </div>
  )
}
