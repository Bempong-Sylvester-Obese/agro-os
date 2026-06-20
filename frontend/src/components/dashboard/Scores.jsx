// src/components/dashboard/Scores.jsx
import { useState } from 'react'
import { FARMER_ASSESSMENTS } from '../../data/payments'

const scoreTier = (score) => {
  if (score >= 82) return 'sh'
  if (score >= 60) return 'sm'
  return 'sl'
}

const pct = (value) => `${Math.round(value * 100)}%`

const FEATURE_LABELS = {
  dues_payment_rate: 'Dues consistency',
  on_time_payment_rate: 'On-time payments',
  yield_performance: 'Yield performance',
  attendance_rate: 'Attendance',
  savings_rate: 'Savings rate',
}

export default function Scores({ agroAi }) {
  const farmers = agroAi?.farmers || FARMER_ASSESSMENTS
  const [selectedId, setSelectedId] = useState(farmers[0]?.farmer_id)
  const selectedFarmer = farmers.find((farmer) => farmer.farmer_id === selectedId) || farmers[0]

  return (
    <>
      <div className="info-banner">
        <strong>About Agro-AI</strong> — a Random Forest credit model trained on synthetic cooperative data for this
        hackathon. It estimates farmer creditworthiness from dues consistency, on-time payments, yield performance,
        attendance, tenure, loan history, outstanding balance, and savings behavior.
      </div>

      <div className="score-layout">
        <div className="admin-card">
          <div className="admin-card-head">
            <span className="admin-card-title serif">Credit decision queue</span>
            <span className="admin-card-action">{agroAi?.source === 'api' ? 'Live API' : 'Demo fallback'}</span>
          </div>
          <div className="sc-head">
            {['Member','Payment','Yield','Decision','Score'].map(h => (
              <span key={h} className="pt-lbl">{h}</span>
            ))}
          </div>
          {farmers.map((farmer) => (
            <button
              key={farmer.farmer_id}
              className={`sc-row sc-row-btn${farmer.farmer_id === selectedFarmer.farmer_id ? ' on' : ''}`}
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

        {selectedFarmer && (
          <div className="admin-card score-detail-card">
            <div className="score-detail-hero">
              <div>
                <div className="pt-id">{selectedFarmer.farmer_id} · {selectedFarmer.region}</div>
                <div className="score-detail-name serif">{selectedFarmer.name}</div>
                <div className="score-detail-sub">{selectedFarmer.crop} farmer requesting GHS {selectedFarmer.requested_credit_amount}</div>
              </div>
              <span className={`score-bdg score-bdg-lg ${scoreTier(selectedFarmer.score)}`}>{selectedFarmer.score}</span>
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
    </>
  )
}
