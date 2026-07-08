// src/components/dashboard/Scores.jsx
import { useState } from 'react'
import { DB_FARMERS_FALLBACK, recalculateTrustScore } from '../../api/farmers'
import { FARMER_ASSESSMENTS } from '../../data/payments'
import { findCrmFarmerForAgroAi, formatTrustScore, scoreTier } from '../../utils/scores'

const pct = (value) => `${Math.round(value * 100)}%`

const FEATURE_LABELS = {
  dues_payment_rate: 'Dues consistency',
  on_time_payment_rate: 'On-time payments',
  yield_performance: 'Yield performance',
  attendance_rate: 'Attendance',
  savings_rate: 'Savings rate',
}

export default function Scores({ agroAi, dbFarmers, onRecalculated }) {
  const agroAiFarmers = agroAi?.farmers || FARMER_ASSESSMENTS
  const trustFarmers = dbFarmers?.farmers || DB_FARMERS_FALLBACK
  const [selectedId, setSelectedId] = useState(agroAiFarmers[0]?.farmer_id)
  const [recalculating, setRecalculating] = useState(null)
  const [recalcError, setRecalcError] = useState('')
  const selectedFarmer = agroAiFarmers.find((farmer) => farmer.farmer_id === selectedId) || agroAiFarmers[0]
  const selectedTrustFarmer = findCrmFarmerForAgroAi(trustFarmers, selectedFarmer)

  async function handleRecalculate(farmerId) {
    setRecalculating(farmerId)
    setRecalcError('')
    try {
      await recalculateTrustScore(farmerId)
      if (onRecalculated) await onRecalculated()
    } catch (err) {
      setRecalcError(err.message || 'Could not recalculate this trust score.')
    } finally {
      setRecalculating(null)
    }
  }

  return (
    <>
      {recalcError && <div className="auth-error" style={{ marginBottom: 16 }}>{recalcError}</div>}

      <div className="info-banner">
        <strong>Trust Score</strong> is rules-based and stored in the database — it recalculates when Moolre payment
        webhooks confirm dues. <strong>Agro-AI credit</strong> is a separate Random Forest model for loan decisions.
      </div>

      <div className="score-layout">
        <div className="admin-card">
          <div className="admin-card-head">
            <span className="admin-card-title serif">Agro-AI credit queue</span>
            <span className="admin-card-action">{agroAi?.source === 'api' ? 'ML model · live' : 'Demo fallback'}</span>
          </div>
          <div className="table-scroll">
            <div className="sc-head">
              {['Member', 'Payment', 'Yield', 'Decision', 'Agro-AI'].map((h) => (
                <span key={h} className="pt-lbl">{h}</span>
              ))}
            </div>
            {agroAiFarmers.map((farmer) => (
              <button
                key={farmer.farmer_id}
                className={`sc-row sc-row-btn${farmer.farmer_id === selectedFarmer?.farmer_id ? ' on' : ''}`}
                onClick={() => setSelectedId(farmer.farmer_id)}
              >
                <div>
                  <div className="pt-name">{farmer.name}</div>
                  <div className="pt-id">{farmer.region} · {farmer.crop}</div>
                </div>
                <span className="pt-m mono" style={{ fontSize: 11 }}>{pct(farmer.features.dues_payment_rate)}</span>
                <span className="pt-m mono" style={{ fontSize: 11 }}>{pct(farmer.features.yield_performance)}</span>
                <span className={`bdg ${farmer.eligible ? 'bdg-green' : 'bdg-amber'}`}>
                  {farmer.eligible ? 'Eligible' : 'Review'}
                </span>
                <span className={`score-bdg ${scoreTier(farmer.score)}`}>{farmer.score}</span>
              </button>
            ))}
          </div>
        </div>

        {selectedFarmer && (
          <div className="admin-card score-detail-card">
            <div className="score-detail-hero">
              <div>
                <div className="pt-id">{selectedFarmer.farmer_id} · {selectedFarmer.region}</div>
                <div className="score-detail-name serif">{selectedFarmer.name}</div>
                <div className="score-detail-sub">
                  {selectedFarmer.crop} farmer requesting GHS {selectedFarmer.requested_credit_amount}
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'flex-end' }}>
                <span className={`score-bdg score-bdg-lg ${scoreTier(selectedTrustFarmer?.trust_score)}`} title="Trust Score">
                  {formatTrustScore(selectedTrustFarmer?.trust_score)}
                </span>
                <span style={{ fontSize: 11, color: 'var(--muted)' }}>Trust Score</span>
                <span className={`score-bdg ${scoreTier(selectedFarmer.score)}`} title="Agro-AI credit score">
                  {selectedFarmer.score}
                </span>
                <span style={{ fontSize: 11, color: 'var(--muted)' }}>Agro-AI credit</span>
              </div>
            </div>

            <div className="decision-card">
              <div className="decision-label">{selectedFarmer.risk_band}</div>
              <div className="decision-title serif">{selectedFarmer.recommendation}</div>
              <div className="decision-copy">
                Agro-AI confidence: {selectedFarmer.confidence}%. Suggested credit limit: GHS {selectedFarmer.approved_credit_limit}.
              </div>
            </div>

            <div className="feature-grid">
              {Object.entries(FEATURE_LABELS).map(([key, label]) => (
                <div key={key} className="feature-pill">
                  <span>{label}</span>
                  <strong>{pct(selectedFarmer.features[key])}</strong>
                </div>
              ))}
            </div>

            <div className="reason-list">
              <div className="pt-lbl">Top model reasons</div>
              {selectedFarmer.top_reasons.map((reason) => (
                <div key={reason} className="reason-item">{reason}</div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="admin-card" style={{ marginTop: 20 }}>
        <div className="admin-card-head">
          <span className="admin-card-title serif">Trust Score leaderboard</span>
          <span className="admin-card-action">
            {dbFarmers?.source === 'api' ? 'Rules-based · live · refreshes every 15s' : 'Rules-based · demo'}
          </span>
        </div>
        <div className="table-scroll">
          <div className="sc-head sc-head-4">
            {['Member', 'Region', 'Status', 'Trust Score', ''].map((h) => (
              <span key={h || 'action'} className="pt-lbl">{h}</span>
            ))}
          </div>
          {[...trustFarmers]
            .sort((a, b) => Number(b.trust_score) - Number(a.trust_score))
            .map((farmer) => (
              <div key={farmer.id} className="sc-row sc-row-4">
                <div>
                  <div className="pt-name">{farmer.name}</div>
                  <div className="pt-id">#{farmer.id}</div>
                </div>
                <span className="pt-m">{farmer.location || '—'}</span>
                <span className="pt-m">{farmer.membership_status}</span>
                <span className={`score-bdg ${scoreTier(farmer.trust_score)}`}>
                  {formatTrustScore(farmer.trust_score)}
                </span>
                {dbFarmers?.source === 'api' ? (
                  <button
                    type="button"
                    className="admin-card-action"
                    style={{ fontSize: 11, background: 'none', border: 'none', cursor: 'pointer' }}
                    onClick={() => handleRecalculate(farmer.id)}
                    disabled={recalculating === farmer.id}
                    title="Recalculate trust score"
                  >
                    {recalculating === farmer.id ? '…' : '↻'}
                  </button>
                ) : (
                  <span />
                )}
              </div>
            ))}
        </div>
      </div>
    </>
  )
}
