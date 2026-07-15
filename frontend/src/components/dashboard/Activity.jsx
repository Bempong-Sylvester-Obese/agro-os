import React, { useEffect, useState } from 'react'
import { RefreshCw, ShieldCheck } from 'lucide-react'
import { fetchAdminAudit } from '../../api/governance'

function readableAction(action) {
  return action.replaceAll('.', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export default function Activity() {
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function load() {
    setLoading(true)
    setError('')
    try {
      setEntries(await fetchAdminAudit())
    } catch (err) {
      setError(err.message || 'Could not load administrator activity.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <section className="admin-card activity-card" aria-labelledby="activity-heading">
      <div className="admin-card-head">
        <div>
          <h2 id="activity-heading" className="admin-card-title serif">Administrator activity</h2>
          <p className="activity-subtitle">Append-only records for sensitive cooperative operations.</p>
        </div>
        <button type="button" className="admin-card-button" onClick={load} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spin' : ''} /> Refresh
        </button>
      </div>
      {error && <div className="dashboard-inline-error" role="alert">{error}</div>}
      {loading && entries.length === 0 ? (
        <div className="dashboard-empty">Loading administrator activity…</div>
      ) : entries.length === 0 ? (
        <div className="dashboard-empty">No audited administrator actions have been recorded yet.</div>
      ) : (
        <ol className="activity-list">
          {entries.map((entry) => (
            <li key={entry.id} className="activity-item">
              <span className="activity-icon"><ShieldCheck size={16} /></span>
              <div>
                <strong>{readableAction(entry.action)}</strong>
                <p>
                  {entry.actor_label || entry.actor_id}
                  {entry.resource_type ? ` · ${entry.resource_type} #${entry.resource_id}` : ''}
                </p>
                {entry.details && <small>{entry.details}</small>}
              </div>
              <time dateTime={entry.created_at}>
                {new Date(entry.created_at).toLocaleString('en-GH', {
                  dateStyle: 'medium',
                  timeStyle: 'short',
                })}
              </time>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
