// src/components/dashboard/Scores.jsx
import { useState } from 'react'
import { farmersApi } from '../../lib/api'

export default function Scores({ members, onRecalculated }) {
  const [recalculating, setRecalculating] = useState(null)
  const [error, setError] = useState('')

  async function handleRecalculate(farmerId) {
    setRecalculating(farmerId)
    setError('')
    try {
      await farmersApi.recalculateTrustScore(farmerId)
      if (onRecalculated) await onRecalculated()
    } catch (err) {
      setError(err.message || 'Could not recalculate this trust score.')
    } finally {
      setRecalculating(null)
    }
  }

  const sorted = [...(members || [])].sort((a, b) => parseInt(b.score, 10) - parseInt(a.score, 10))

  return (
    <>
      <div className="info-banner">
        <strong>About AgroCredit scores</strong> — AI-generated creditworthiness scores (0–100) built from each
        member's payment history, production output, cooperative tenure, and dues consistency. Scores are calculated
        live by the backend's Trust Score service, weighted 40% payment compliance, 25% production history,
        20% loan repayment, 15% attendance.
      </div>

      {error && <div className="auth-error" style={{ marginBottom: 16 }}>{error}</div>}

      <div className="admin-card">
        <div className="admin-card-head">
          <span className="admin-card-title serif">Member trust scores</span>
        </div>
        <div className="sc-head">
          {['Member','Region','Phone','Score',''].map(h => (
            <span key={h} className="pt-lbl">{h}</span>
          ))}
        </div>
        {sorted.length === 0 && (
          <div style={{ padding: '20px 22px', color: 'var(--muted)', fontSize: 13 }}>No members yet.</div>
        )}
        {sorted.map(m => (
          <div key={m.id} className="sc-row">
            <div>
              <div className="pt-name">{m.name}</div>
              <div className="pt-id">{m.id}</div>
            </div>
            <span className="pt-m">{m.region}</span>
            <span className="pt-m mono" style={{ fontSize: 11 }}>{m.phone}</span>
            <span className={`score-bdg ${m.tier}`}>{m.score}</span>
            <button
              className="admin-card-action"
              style={{ fontSize: 11, background: 'none', border: 'none', cursor: 'pointer' }}
              onClick={() => handleRecalculate(m.farmerId)}
              disabled={recalculating === m.farmerId}
            >
              {recalculating === m.farmerId ? '…' : '↻'}
            </button>
          </div>
        ))}
      </div>
    </>
  )
}
