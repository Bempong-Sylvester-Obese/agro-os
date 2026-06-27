// src/pages/LoginPage.jsx
import { useState } from 'react'
import { USERS } from '../data/users'

export default function LoginPage({ onAuth }) {
  const [mode, setMode]         = useState('login')   // 'login' | 'signup'
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [name, setName]         = useState('')
  const [confirm, setConfirm]   = useState('')
  const [error, setError]       = useState('')
  const [accounts, setAccounts] = useState(USERS)

  function handleLogin(e) {
    e.preventDefault()
    setError('')
    const user = accounts.find(
      u => u.email.toLowerCase() === email.trim().toLowerCase() && u.password === password
    )
    if (!user) {
      setError('Invalid email or password. Please try again.')
      return
    }
    onAuth(user)
  }

  function handleSignup(e) {
    e.preventDefault()
    setError('')
    if (!name.trim()) { setError('Please enter your full name.'); return }
    if (!email.trim()) { setError('Please enter your email.'); return }
    if (password.length < 6) { setError('Password must be at least 6 characters.'); return }
    if (password !== confirm) { setError('Passwords do not match.'); return }
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
      cooperative: 'Ashanti Farmers Co-op',
    }
    const updated = [...accounts, newUser]
    setAccounts(updated)
    onAuth(newUser)
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

            <button type="submit" className="btn-lg auth-submit">
              {mode === 'login' ? 'Sign in →' : 'Create account →'}
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
  )
}
