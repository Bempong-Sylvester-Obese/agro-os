// src/components/dashboard/Overview.jsx
import { CREDIT_SUMMARY, FARMER_ASSESSMENTS, PAYMENTS } from '../../data/payments'

const scoreTier = (score) => {
  if (score >= 82) return 'sh'
  if (score >= 60) return 'sm'
  return 'sl'
}

export default function Overview({ agroAi }) {
  const farmers = agroAi?.farmers || FARMER_ASSESSMENTS
  const summary = agroAi?.summary || CREDIT_SUMMARY
  const topScores = [...farmers].sort((a, b) => b.score - a.score).slice(0, 4)
  const reviewQueue = farmers.filter((farmer) => !farmer.eligible).slice(0, 3)

  return (
    <>
      <div className="stat-row">
        {[
          ['Total members',          '248',        '+12 this month'],
          ['Dues collected',         'GHS 29,760', 'June 2026'],
          ['Credit eligible',        summary.eligible_count, `${summary.total_farmers} farmers assessed`],
          ['Avg Agro-AI score',      summary.average_score,  summary.model_version],
        ].map(([lbl, val, sub]) => (
          <div key={lbl} className="stat-card">
            <div className="stat-lbl">{lbl}</div>
            <div className="stat-val serif">{val}</div>
            <div className="stat-sub">{sub}</div>
          </div>
        ))}
      </div>

      <div className="admin-grid">
        {/* Recent payments */}
        <div className="admin-card">
          <div className="admin-card-head">
            <span className="admin-card-title serif">Recent payments</span>
            <span className="admin-card-action">View all →</span>
          </div>
          <div className="pt-head">
            {['Member','Amount','Method','Date','Status'].map(h => (
              <span key={h} className="pt-lbl">{h}</span>
            ))}
          </div>
          {PAYMENTS.map(([name, id, amt, method, date, status, cls]) => (
            <div key={name} className="pt-row">
              <div>
                <div className="pt-name">{name}</div>
                <div className="pt-id">{id}</div>
              </div>
              <span className="pt-v">{amt}</span>
              <span className="pt-m">{method}</span>
              <span className="pt-m">{date.split(',')[0]}</span>
              <span className={`bdg ${cls}`}>{status}</span>
            </div>
          ))}
        </div>

        {/* Top agro-ai scores */}
        <div className="admin-card">
          <div className="admin-card-head">
            <span className="admin-card-title serif">Top Agro-AI approvals</span>
            <span className="admin-card-action">{agroAi?.source === 'api' ? 'Live API' : 'Demo data'}</span>
          </div>
          {topScores.map((farmer) => (
            <div key={farmer.farmer_id} className="score-item">
              <div>
                <div className="score-item-name">{farmer.name}</div>
                <div className="score-item-region">
                  {farmer.region} · {farmer.recommendation}
                </div>
              </div>
              <span className={`score-bdg ${scoreTier(farmer.score)}`}>{farmer.score}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="admin-card" style={{ marginTop: 20 }}>
        <div className="admin-card-head">
          <span className="admin-card-title serif">Credit review queue</span>
          <span className="admin-card-action">{summary.manual_review_count + summary.high_risk_count} need attention</span>
        </div>
        <div className="review-grid">
          {reviewQueue.map((farmer) => (
            <div key={farmer.farmer_id} className="review-card">
              <div className="review-top">
                <div>
                  <div className="pt-name">{farmer.name}</div>
                  <div className="pt-id">{farmer.farmer_id} · {farmer.crop}</div>
                </div>
                <span className={`score-bdg ${scoreTier(farmer.score)}`}>{farmer.score}</span>
              </div>
              <div className="review-rec">{farmer.recommendation}</div>
              <div className="review-reason">{farmer.top_reasons[0]}</div>
            </div>
          ))}
        </div>
      </div>
    </>
  )
}
