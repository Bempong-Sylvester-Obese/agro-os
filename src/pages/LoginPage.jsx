// src/pages/LoginPage.jsx
import { useState } from 'react'
import { authApi, setToken } from '../lib/api'

export default function LoginPage({ onAuth }) {
  const [mode, setMode]         = useState('login')   // 'login' | 'signup'
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [name, setName]         = useState('')
  const [confirm, setConfirm]   = useState('')
  const [cooperativeName, setCooperativeName] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

  async function handleLogin(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await authApi.login({ email: email.trim(), password })
      setToken(res.access_token)
      onAuth(res.user)
    } catch (err) {
      setError(err.message || 'Invalid email or password. Please try again.')
    } finally {
      setLoading(false)
    }
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
      const res = await authApi.signup({
        name: name.trim(),
        email: email.trim(),
        password,
        cooperative_name: cooperativeName.trim(),
      })
      setToken(res.access_token)
      onAuth(res.user)
    } catch (err) {
      setError(err.message || 'Could not create your account. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
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
                : 'Join or create your cooperative on AgroOS'}
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
              <>
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
                  <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>
                    If this cooperative already exists you'll join it as a Field Officer.
                    Otherwise a new cooperative is created and you become its Administrator.
                  </div>
                </div>
              </>
            )}

            <button type="submit" className="btn-lg auth-submit" disabled={loading}>
              {loading ? 'Please wait…' : (mode === 'login' ? 'Sign in →' : 'Create account →')}
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
        </div>
      </div>
    </div>
  )
}
