import React, { useEffect, useState } from 'react'
import { Loader2, Plus, RefreshCw, ShieldCheck } from 'lucide-react'
import {
  fetchCooperativeUsers,
  fetchIntegrationHealth,
  registerCooperativeUser,
  updateCooperativeUser,
} from '../../api/governance'

const emptyInvite = { email: '', password: '', role: 'finance_officer' }

export default function GovernanceSettings() {
  const [users, setUsers] = useState([])
  const [health, setHealth] = useState(null)
  const [invite, setInvite] = useState(emptyInvite)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(null)
  const [error, setError] = useState('')
  const [restricted, setRestricted] = useState(false)

  async function load() {
    setLoading(true)
    setError('')
    const [usersResult, healthResult] = await Promise.allSettled([
      fetchCooperativeUsers(),
      fetchIntegrationHealth(),
    ])
    if (usersResult.status === 'fulfilled') {
      setUsers(usersResult.value)
      setRestricted(false)
    } else if ([401, 403].includes(usersResult.reason?.status)) {
      setRestricted(true)
    } else {
      setError(usersResult.reason?.message || 'Could not load cooperative users.')
    }
    if (healthResult.status === 'fulfilled') setHealth(healthResult.value)
    setLoading(false)
  }

  useEffect(() => {
    load()
  }, [])

  async function handleInvite(event) {
    event.preventDefault()
    setSaving('invite')
    setError('')
    try {
      await registerCooperativeUser(invite)
      setInvite(emptyInvite)
      await load()
    } catch (err) {
      setError(err.message || 'Could not add this user.')
    } finally {
      setSaving(null)
    }
  }

  async function changeUser(userId, payload) {
    setSaving(userId)
    setError('')
    try {
      await updateCooperativeUser(userId, payload)
      await load()
    } catch (err) {
      setError(err.message || 'Could not update this user.')
    } finally {
      setSaving(null)
    }
  }

  const moolreChecks = health?.moolre ? Object.entries(health.moolre) : []

  return (
    <>
      <section className="admin-card governance-settings-card" aria-labelledby="team-settings-title">
        <div className="admin-card-head">
          <div>
            <h2 id="team-settings-title" className="admin-card-title serif">Team and access</h2>
            <p className="activity-subtitle">Manage cooperative administrators and finance officers.</p>
          </div>
          <button type="button" className="admin-card-button" onClick={load} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin' : ''} /> Refresh
          </button>
        </div>
        {error && <div className="dashboard-inline-error" role="alert">{error}</div>}
        {restricted ? (
          <div className="dashboard-empty">Only cooperative administrators can manage team access.</div>
        ) : loading && users.length === 0 ? (
          <div className="dashboard-empty">Loading team access…</div>
        ) : (
          <div className="governance-settings-body">
            <div className="settings-user-list">
              {users.map((user) => (
                <div className="settings-user-row" key={user.id}>
                  <div>
                    <strong>{user.email}</strong>
                    <small>{user.is_active ? 'Active account' : 'Deactivated account'}</small>
                  </div>
                  <label>
                    <span className="sr-only">Role for {user.email}</span>
                    <select
                      value={user.role}
                      disabled={saving === user.id || !user.is_active}
                      onChange={(event) => changeUser(user.id, { role: event.target.value })}
                    >
                      <option value="admin">Administrator</option>
                      <option value="finance_officer">Finance officer</option>
                    </select>
                  </label>
                  <button
                    type="button"
                    className="admin-card-button"
                    disabled={saving === user.id}
                    onClick={() => changeUser(user.id, { is_active: !user.is_active })}
                    aria-label={`${user.is_active ? 'Deactivate' : 'Reactivate'} ${user.email}`}
                  >
                    {saving === user.id ? <Loader2 size={13} className="spin" /> : null}
                    {user.is_active ? 'Deactivate' : 'Reactivate'}
                  </button>
                </div>
              ))}
            </div>
            <form className="settings-invite-form" onSubmit={handleInvite}>
              <h3><Plus size={15} /> Add team member</h3>
              <input
                type="email"
                value={invite.email}
                onChange={(event) => setInvite({ ...invite, email: event.target.value })}
                placeholder="name@cooperative.org"
                aria-label="New user email"
                required
              />
              <input
                type="password"
                minLength={8}
                value={invite.password}
                onChange={(event) => setInvite({ ...invite, password: event.target.value })}
                placeholder="Temporary password"
                aria-label="Temporary password"
                required
              />
              <select
                value={invite.role}
                onChange={(event) => setInvite({ ...invite, role: event.target.value })}
                aria-label="New user role"
              >
                <option value="finance_officer">Finance officer</option>
                <option value="admin">Administrator</option>
              </select>
              <button type="submit" className="btn-lg" disabled={saving === 'invite'}>
                {saving === 'invite' ? 'Adding…' : 'Add user'}
              </button>
            </form>
          </div>
        )}
      </section>

      <section className="admin-card governance-settings-card" aria-labelledby="integration-health-title">
        <div className="admin-card-head">
          <div>
            <h2 id="integration-health-title" className="admin-card-title serif">Moolre integration health</h2>
            <p className="activity-subtitle">Configuration readiness and wallet policy. No credentials are displayed.</p>
          </div>
          {health && <span className="bdg bdg-green">{health.environment}</span>}
        </div>
        {health ? (
          <div className="integration-health-grid">
            {moolreChecks.map(([name, configured]) => (
              <div key={name} className="integration-health-item">
                <ShieldCheck size={17} />
                <span>{name.replaceAll('_', ' ')}</span>
                <strong className={configured ? 'is-ready' : 'is-missing'}>
                  {configured ? 'Configured' : 'Action required'}
                </strong>
              </div>
            ))}
            <div className="integration-wallet-policy">
              Loan payouts use the protected platform wallet. Repayment collections settle to the cooperative wallet.
            </div>
          </div>
        ) : (
          <div className="dashboard-empty">
            {restricted ? 'Integration configuration is visible to administrators.' : 'Integration health is unavailable.'}
          </div>
        )}
      </section>
    </>
  )
}
