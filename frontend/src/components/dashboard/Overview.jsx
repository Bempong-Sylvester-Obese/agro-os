// src/components/dashboard/Overview.jsx
import { CREDIT_SUMMARY, FARMER_ASSESSMENTS, PAYMENTS } from '../../data/payments'
import { DB_FARMERS_FALLBACK } from '../../api/farmers'
import { averageTrustScore, formatTrustScore, scoreTier } from '../../utils/scores'

export default function Overview({ agroAi, dbFarmers }) {
  const farmers = dbFarmers?.farmers || DB_FARMERS_FALLBACK
  const agroAiFarmers = agroAi?.farmers || FARMER_ASSESSMENTS
  const summary = agroAi?.summary || CREDIT_SUMMARY
  const avgTrustScore = averageTrustScore(farmers)
  const topTrustScores = [...farmers]
    .sort((a, b) => Number(b.trust_score) - Number(a.trust_score))
    .slice(0, 4)
  const topAgroAiScores = agroAiFarmers
    .filter((farmer) => farmer.eligible)
    .sort((a, b) => b.score - a.score)
    .slice(0, 4)
  const reviewQueue = agroAiFarmers.filter((farmer) => !farmer.eligible).slice(0, 3)
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
          ['Total members', String(farmers.length), dbFarmers?.source === 'api' ? 'Live DB' : 'Demo fallback'],
          ['Dues collected', 'GHS 29,760', 'June 2026'],
          ['Avg Trust Score', avgTrustScore, dbFarmers?.source === 'api' ? 'Rules-based · live' : 'Rules-based · demo'],
          ['Avg Agro-AI score', summary.average_score, summary.model_version],
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
        <div className="admin-card">
          <div className="admin-card-head">
            <span className="admin-card-title serif">Recent payments</span>
            <span className="admin-card-action">View all →</span>
          </div>
          <div className="pt-head">
            {['Member', 'Amount', 'Method', 'Date', 'Status'].map((h) => (
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

        <div className="admin-card">
          <div className="admin-card-head">
            <span className="admin-card-title serif">Top Trust Scores</span>
            <span className="admin-card-action">
              {dbFarmers?.source === 'api' ? 'Rules-based · live' : 'Rules-based · demo'}
            </span>
          </div>
          {topTrustScores.map((farmer) => (
            <div key={farmer.id} className="score-item">
              <div>
                <div className="score-item-name">{farmer.name}</div>
                <div className="score-item-region">{farmer.location || '—'}</div>
              </div>
              <span className={`score-bdg ${scoreTier(farmer.trust_score)}`}>
                {formatTrustScore(farmer.trust_score)}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="admin-grid" style={{ marginTop: 20 }}>
        <div className="admin-card">
          <div className="admin-card-head">
            <span className="admin-card-title serif">Top Agro-AI approvals</span>
            <span className="admin-card-action">{agroAi?.source === 'api' ? 'ML model · live' : 'ML model · demo'}</span>
          </div>
          {topAgroAiScores.map((farmer) => (
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

        <div className="admin-card">
          <div className="admin-card-head">
            <span className="admin-card-title serif">Agro-AI review queue</span>
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
      </div>
    </>
  )
}
