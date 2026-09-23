import React, { useEffect, useState } from 'react'
import { Loader2, Plus, RefreshCw } from 'lucide-react'
import {
  fetchCooperativeUsers,
  updateCooperativeUser,
  inviteCooperativeUser,
} from '../../api/governance'
import { getOrganizationType } from '../../utils/auth'
import { COOP_ROLES, ROLE_DESCRIPTIONS, ROLES, SOLO_ROLES, roleLabel, rolesForTrack } from '../../utils/roles'

/**
 * Role picker (#244). Lists every role the API accepts, grouped by track, with
 * the current organisation's track first so the common choice is one click.
 */
function RoleOptions({ organizationType }) {
  const primary = rolesForTrack(organizationType)
  const primaryLabel = organizationType === 'solo_farm' ? 'Solo farm roles' : 'Cooperative roles'
  const secondary = organizationType === 'solo_farm' ? COOP_ROLES : SOLO_ROLES
  const secondaryLabel = organizationType === 'solo_farm' ? 'Cooperative roles' : 'Solo farm roles'
  const renderOptions = (roles) => roles.map((role) => (
    <option key={role} value={role} title={ROLE_DESCRIPTIONS[role]}>{roleLabel(role)}</option>
  ))
  return (
    <>
      <optgroup label={primaryLabel}>{renderOptions(primary)}</optgroup>
      <optgroup label={secondaryLabel}>{renderOptions(secondary.filter((role) => role !== ROLES.ADMIN))}</optgroup>
    </>
  )
}

function defaultInviteRole(organizationType) {
  return organizationType === 'solo_farm' ? ROLES.FARM_MANAGER : ROLES.FINANCE_OFFICER
}

export default function GovernanceSettings({ cooperativeId }) {
  const organizationType = getOrganizationType()
  const emptyInvite = { email: '', role: defaultInviteRole(organizationType) }
  const [users, setUsers] = useState([])
  const [invite, setInvite] = useState(emptyInvite)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(null)
  const [error, setError] = useState('')
  const [restricted, setRestricted] = useState(false)

  async function load() {
    setLoading(true)
    setError('')
    try {
      const data = await fetchCooperativeUsers(cooperativeId)
      setUsers(data)
      setRestricted(false)
    } catch (err) {
      if ([401, 403].includes(err.status)) {
        setRestricted(true)
      } else {
        setRestricted(false)
        setError(err.message || 'Could not load cooperative users.')
      }
    }
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
      const invited = await inviteCooperativeUser(invite.email, invite.role)
      const invitedEmail = invite.email
      setInvite(emptyInvite)
      await load()
      const delivery = invited?.delivery
      if (delivery?.delivered) {
        setError(`Invite emailed to ${invitedEmail}.`)
      } else if (delivery?.invite_link) {
        setError(`Invite created. Email delivery is not configured — share this link with ${invitedEmail}: ${delivery.invite_link}`)
      } else {
        setError(delivery?.message || 'Invite sent.')
      }
    } catch (err) {
      setError(err.message || 'Could not invite this user.')
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

  return (
    <>
      <section className="admin-card governance-settings-card" aria-labelledby="team-settings-title">
        <div className="admin-card-head">
          <div>
            <h2 id="team-settings-title" className="admin-card-title serif">Team and access</h2>
            <p className="activity-subtitle">
              {organizationType === 'solo_farm'
                ? 'Manage farm owners, managers and supervisors.'
                : 'Manage administrators, finance, field, operations and sales officers.'}
            </p>
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
                      <RoleOptions organizationType={organizationType} />
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
              <h3><Plus size={15} /> Invite team member</h3>
              <input
                type="email"
                value={invite.email}
                onChange={(event) => setInvite({ ...invite, email: event.target.value })}
                placeholder="name@cooperative.org"
                aria-label="New user email"
                required
              />
              <select
                value={invite.role}
                onChange={(event) => setInvite({ ...invite, role: event.target.value })}
                aria-label="New user role"
              >
                <RoleOptions organizationType={organizationType} />
              </select>
              <small className="settings-role-hint">{ROLE_DESCRIPTIONS[invite.role]}</small>
              <button type="submit" className="btn-lg" disabled={saving === 'invite'}>
                {saving === 'invite' ? 'Sending…' : 'Send invite'}
              </button>
            </form>
          </div>
        )}
      </section>
    </>
  )
}
