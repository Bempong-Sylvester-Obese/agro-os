// src/components/dashboard/Overview.jsx
import { useEffect, useState } from 'react'
import { CREDIT_SUMMARY, FARMER_ASSESSMENTS } from '../../data/payments'
import { DB_FARMERS_FALLBACK } from '../../api/farmers'
import { fetchPaymentsDashboard } from '../../api/transactions'
import { averageTrustScore, formatTrustScore, scoreTier } from '../../utils/scores'

export default function Overview({ agroAi, dbFarmers }) {
  const [payments, setPayments] = useState(null)
  const [paymentsLoading, setPaymentsLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    fetchPaymentsDashboard()
      .then((data) => {
        if (mounted) setPayments(data)
      })
      .finally(() => {
        if (mounted) setPaymentsLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [])

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

  const duesCollected = paymentsLoading
    ? '…'
    : payments?.stats?.[0]?.[1] || 'GHS 0'
  const duesSub = paymentsLoading
    ? 'Loading'
    : payments?.stats?.[0]?.[2] || 'No completed dues'
  const recentPayments = paymentsLoading ? [] : (payments?.rows || []).slice(0, 5)

  return (
    <>
      <div className="stat-row">
        {[
          ['Total members', String(farmers.length), dbFarmers?.source === 'api' ? 'Live DB' : 'Demo fallback'],
          ['Dues collected', duesCollected, duesSub],
          ['Avg Trust Score', avgTrustScore, dbFarmers?.source === 'api' ? 'Rules-based · live' : 'Rules-based · demo'],
          ['Avg Agro-AI score', summary.average_score, summary.model_version],
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
            <span className="admin-card-action">
              {paymentsLoading ? 'Loading…' : payments?.source === 'api' ? 'Live API' : 'Demo data'}
            </span>
          </div>
          <div className="table-scroll">
            <div className="pt-head">
              {['Member', 'Amount', 'Method', 'Date', 'Status'].map((h) => (
                <span key={h} className="pt-lbl">{h}</span>
              ))}
            </div>
            {paymentsLoading && (
              <div className="pt-row">
                <div className="pt-name">Loading recent payments…</div>
              </div>
            )}
            {!paymentsLoading && recentPayments.length === 0 && (
              <div className="pt-row">
                <div className="pt-name">No transactions recorded yet.</div>
              </div>
            )}
            {!paymentsLoading && recentPayments.map((row) => (
              <div key={row.key} className="pt-row">
                <div>
                  <div className="pt-name">{row.name}</div>
                  <div className="pt-id">{row.memberId}</div>
                </div>
                <span className="pt-v">{row.amount}</span>
                <span className="pt-m">{row.method}</span>
                <span className="pt-m">{row.date}</span>
                <span className={`bdg ${row.statusClass}`}>{row.status}</span>
              </div>
            ))}
          </div>
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
