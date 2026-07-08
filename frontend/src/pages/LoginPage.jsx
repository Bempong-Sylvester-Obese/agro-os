// src/pages/LoginPage.jsx
import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { loginAdmin, signupAdmin, storeAuthToken } from '../api/auth'
import { USERS } from '../data/users'

export default function LoginPage({ onAuth }) {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const initialMode = searchParams.get('mode') === 'signup' ? 'signup' : 'login'
  const [mode, setMode]         = useState(initialMode)
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [name, setName]         = useState('')
  const [confirm, setConfirm]   = useState('')
  const [cooperativeName, setCooperativeName] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)
  const [accounts, setAccounts] = useState(USERS)

  useEffect(() => {
    setMode(initialMode)
    setError('')
  }, [initialMode])

  async function handleLogin(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const result = await loginAdmin(email, password)
      storeAuthToken(result.access_token)
      onAuth({
        ...result.user,
        email: result.user.email || email.trim(),
        cooperative: 'Kuapa Kokoo Demo Cooperative',
      })
      return
    } catch {
      // Fall back to local demo accounts when backend auth is unavailable.
    } finally {
      setLoading(false)
    }

    const user = accounts.find(
      u => u.email.toLowerCase() === email.trim().toLowerCase() && u.password === password
    )
    if (!user) {
      setError('Invalid email or password. Try admin@agroos.demo / demo1234 when the API is running.')
      return
    }
    onAuth(user)
  }

  async function handleSignup(e) {
    e.preventDefault()
    setError('')
    if (!name.trim()) { setError('Please enter your full name.'); return }
    if (!email.trim()) { setError('Please enter your email.'); return }
    if (!cooperativeName.trim()) { setError('Please enter your cooperative name.'); return }
    if (password.length < 6) { setError('Password must be at least 6 characters.'); return }
    if (password !== confirm) { setError('Passwords do not match.'); return }

    setLoading(true)
    try {
      const result = await signupAdmin({
        name: name.trim(),
        email: email.trim(),
        password,
        cooperative_name: cooperativeName.trim(),
      })
      storeAuthToken(result.access_token)
      onAuth({
        ...result.user,
        email: result.user?.email || email.trim(),
        cooperative: cooperativeName.trim(),
      })
      return
    } catch {
      // Fall back to local demo signup when backend signup is unavailable.
    } finally {
      setLoading(false)
    }

    if (accounts.find(u => u.email.toLowerCase() === email.trim().toLowerCase())) {
      setError('An account with this email already exists.')
      return
    }
    const initials = name.trim().split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    const newUser = {
      id: `USR-${String(accounts.length + 1).padStart(3, '0')}`,
      name: name.trim(),
      initials,
      email: email.trim(),
      password,
      role: 'Field Officer',
      cooperative: cooperativeName.trim() || 'Ashanti Farmers Co-op',
    }
    const updated = [...accounts, newUser]
    setAccounts(updated)
    onAuth(newUser)
  }

  return (
    <div className="auth-page">
      <header className="auth-nav">
        <button type="button" className="auth-back-btn" onClick={() => navigate('/')}>
          ← Back to site
        </button>
        <button type="button" className="auth-nav-logo serif" onClick={() => navigate('/')}>
          AgroOS
        </button>
      </header>

      <div className="auth-shell">
      <div className="auth-brand">
        <div className="auth-brand-inner">
          <div className="auth-logo serif">AgroOS</div>
          <div className="auth-tagline">Cooperative management platform for Ghana's farmers</div>

          <div className="auth-features">
            <div className="auth-feature-item">
              <span className="auth-feature-icon">📊</span>
              <div>
                <div className="auth-feature-title">Real-time dashboards</div>
                <div className="auth-feature-desc">Track members, payments & trust scores</div>
              </div>
            </div>
            <div className="auth-feature-item">
              <span className="auth-feature-icon">💳</span>
              <div>
                <div className="auth-feature-title">MoMo & USSD payments</div>
                <div className="auth-feature-desc">Collect dues and disburse loans seamlessly</div>
              </div>
            </div>
            <div className="auth-feature-item">
              <span className="auth-feature-icon">⭐</span>
              <div>
                <div className="auth-feature-title">AgroCredit scores</div>
                <div className="auth-feature-desc">AI-driven trust ratings per farmer</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="auth-panel">
        <div className="auth-card">
          <div className="auth-card-head">
            <div className="auth-card-title serif">
              {mode === 'login' ? 'Welcome back' : 'Create your account'}
            </div>
            <div className="auth-card-sub">
              {mode === 'login'
                ? 'Sign in to access your cooperative dashboard'
                : 'Join your cooperative on AgroOS'}
            </div>
          </div>

          {error && <div className="auth-error">{error}</div>}

          <form onSubmit={mode === 'login' ? handleLogin : handleSignup} className="auth-form">
            {mode === 'signup' && (
              <div className="auth-field">
                <label className="auth-label">Full name</label>
                <input
                  className="auth-input"
                  type="text"
                  placeholder="e.g. Abena Mensah"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  required
                />
              </div>
            )}

            <div className="auth-field">
              <label className="auth-label">Email address</label>
              <input
                className="auth-input"
                type="email"
                placeholder="you@cooperative.gh"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="auth-field">
              <label className="auth-label">Password</label>
              <input
                className="auth-input"
                type="password"
                placeholder={mode === 'signup' ? 'At least 6 characters' : '••••••••'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
              />
            </div>

            {mode === 'signup' && (
              <div className="auth-field">
                <label className="auth-label">Cooperative name</label>
                <input
                  className="auth-input"
                  type="text"
                  placeholder="e.g. Ashanti Farmers Co-op"
                  value={cooperativeName}
                  onChange={e => setCooperativeName(e.target.value)}
                  required
                />
              </div>
            )}

            {mode === 'signup' && (
              <div className="auth-field">
                <label className="auth-label">Confirm password</label>
                <input
                  className="auth-input"
                  type="password"
                  placeholder="Re-enter your password"
                  value={confirm}
                  onChange={e => setConfirm(e.target.value)}
                  required
                />
              </div>
            )}

            <button type="submit" className="btn-lg auth-submit" disabled={loading}>
              {loading
                ? (mode === 'login' ? 'Signing in…' : 'Creating account…')
                : (mode === 'login' ? 'Sign in →' : 'Create account →')}
            </button>
          </form>

          <div className="auth-switch">
            {mode === 'login' ? (
              <>Don't have an account?{' '}
                <button className="auth-switch-btn" onClick={() => { setMode('signup'); setError('') }}>
                  Sign up
                </button>
              </>
            ) : (
              <>Already have an account?{' '}
                <button className="auth-switch-btn" onClick={() => { setMode('login'); setError('') }}>
                  Sign in
                </button>
              </>
            )}
          </div>

          {mode === 'login' && (
            <div className="auth-hint">
              <span className="auth-hint-label">Demo credentials</span>
              <span>kwabena@ashantifarmers.gh / harvest2026</span>
            </div>
          )}
        </div>
      </div>
    </div>
    </div>
  )
}
