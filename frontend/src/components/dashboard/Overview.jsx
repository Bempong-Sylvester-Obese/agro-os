// src/components/dashboard/Overview.jsx
import { OverviewSkeleton } from './DashboardSkeleton'

const scoreTier = (score) => {
  if (score >= 82) return 'sh'
  if (score >= 60) return 'sm'
  return 'sl'
}

function fmtGHS(amount) {
  return `GHS ${Number(amount).toLocaleString('en-GH', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

export default function Overview({ farmers = [], transactions = [], loading }) {
  if (loading) return <OverviewSkeleton />

  // ── Real computed stats ──────────────────────────────────────────────────
  const totalMembers  = farmers.length
  const activeMembers = farmers.filter(f => f.membership_status === 'active').length

  const oneMonthAgo   = new Date(); oneMonthAgo.setMonth(oneMonthAgo.getMonth() - 1)
  const newThisMonth  = farmers.filter(f => new Date(f.created_at) > oneMonthAgo).length

  const completedDues = transactions.filter(
    t => t.transaction_type === 'dues' && t.status === 'completed'
  )
  const duesCollected = completedDues.reduce((s, t) => s + t.amount, 0)

  const creditEligible = farmers.filter(f => f.trust_score >= 68).length
  const avgScore = totalMembers > 0
    ? Math.round(farmers.reduce((s, f) => s + (f.trust_score || 0), 0) / totalMembers * 10) / 10
    : null

  // ── Top scorers and review queue ─────────────────────────────────────────
  const sorted     = [...farmers].sort((a, b) => b.trust_score - a.trust_score)
  const topScores  = sorted.filter(f => f.trust_score >= 68).slice(0, 4)
  const reviewQueue = [...farmers]
    .filter(f => f.trust_score < 68)
    .sort((a, b) => a.trust_score - b.trust_score)
    .slice(0, 3)

  // ── Recent transactions (most recent 5) ──────────────────────────────────
  const recentTxns = [...transactions]
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .slice(0, 5)
    .map(tx => {
      const farmer = farmers.find(f => f.id === tx.farmer_id)
      const name   = farmer ? farmer.name : `Farmer #${tx.farmer_id}`
      const date   = new Date(tx.created_at).toLocaleDateString('en-US', { month: 'short', day: '2-digit' })

      let method = 'Manual'
      if (['13', '6', '7'].includes(tx.channel)) method = 'USSD'
      else if (tx.channel) method = tx.channel

      let cls = 'bdg-amber'; let label = 'Pending'
      if (tx.status === 'completed') { cls = 'bdg-green'; label = 'Paid' }
      if (tx.status === 'failed')    { cls = 'bdg-red';   label = 'Failed' }

      return { name, id: `#${tx.id}`, amt: fmtGHS(tx.amount), method, date, label, cls, key: tx.id }
    })

  return (
    <>
      {/* ── Stat cards ── */}
      <div className="stat-row">
        {[
          ['Total members',  totalMembers === 0 ? '0' : totalMembers,
            newThisMonth > 0 ? `+${newThisMonth} this month` : `${activeMembers} active`],
          ['Dues collected',  duesCollected > 0 ? fmtGHS(duesCollected) : '—',
            `${completedDues.length} payment${completedDues.length !== 1 ? 's' : ''} completed`],
          ['Credit eligible', creditEligible, `of ${totalMembers} member${totalMembers !== 1 ? 's' : ''} assessed`],
          ['Avg trust score', avgScore ?? '—', 'AgroCredit engine'],
        ].map(([lbl, val, sub]) => (
          <div key={lbl} className="stat-card">
            <div className="stat-lbl">{lbl}</div>
            <div className="stat-val serif">{val}</div>
            <div className="stat-sub">{sub}</div>
          </div>
        ))}
      </div>

      <div className="admin-grid">
        {/* ── Recent payments ── */}
        <div className="admin-card">
          <div className="admin-card-head">
            <span className="admin-card-title serif">Recent payments</span>
            <span className="admin-card-action">Live data</span>
          </div>
          {recentTxns.length === 0 ? (
            <div style={{ padding: '28px 20px', color: 'var(--muted)', fontSize: 14 }}>
              No transactions yet. Start collecting dues to see payment history here.
            </div>
          ) : (
            <>
              <div className="pt-head">
                {['Member', 'Amount', 'Method', 'Date', 'Status'].map(h => (
                  <span key={h} className="pt-lbl">{h}</span>
                ))}
              </div>
              {recentTxns.map(({ name, id, amt, method, date, label, cls, key }) => (
                <div key={key} className="pt-row">
                  <div>
                    <div className="pt-name">{name}</div>
                    <div className="pt-id">{id}</div>
                  </div>
                  <span className="pt-v">{amt}</span>
                  <span className="pt-m">{method}</span>
                  <span className="pt-m">{date}</span>
                  <span className={`bdg ${cls}`}>{label}</span>
                </div>
              ))}
            </>
          )}
        </div>

        {/* ── Top trust scores ── */}
        <div className="admin-card">
          <div className="admin-card-head">
            <span className="admin-card-title serif">Top credit scores</span>
            <span className="admin-card-action">Real data</span>
          </div>
          {topScores.length === 0 ? (
            <div style={{ padding: '28px 20px', color: 'var(--muted)', fontSize: 14 }}>
              {totalMembers === 0
                ? 'Add members to start building trust scores.'
                : 'No members have reached the credit threshold yet. Record payments and production data.'}
            </div>
          ) : (
            topScores.map(farmer => (
              <div key={farmer.id} className="score-item">
                <div>
                  <div className="score-item-name">{farmer.name}</div>
                  <div className="score-item-region">
                    {farmer.location || '—'} · {farmer.crop_type || 'Unspecified crop'}
                  </div>
                </div>
                <span className={`score-bdg ${scoreTier(farmer.trust_score)}`}>
                  {Math.round(farmer.trust_score)}
                </span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* ── Credit review queue ── */}
      <div className="admin-card" style={{ marginTop: 20 }}>
        <div className="admin-card-head">
          <span className="admin-card-title serif">Credit review queue</span>
          <span className="admin-card-action">
            {reviewQueue.length > 0 ? `${reviewQueue.length} need attention` : 'All clear'}
          </span>
        </div>
        {reviewQueue.length === 0 ? (
          <div style={{ padding: '28px 20px', color: 'var(--muted)', fontSize: 14 }}>
            {totalMembers === 0
              ? 'No members yet.'
              : 'No members flagged for review — all assessed members meet the credit threshold.'}
          </div>
        ) : (
          <div className="review-grid">
            {reviewQueue.map(farmer => (
              <div key={farmer.id} className="review-card">
                <div className="review-top">
                  <div>
                    <div className="pt-name">{farmer.name}</div>
                    <div className="pt-id">#{farmer.id} · {farmer.crop_type || '—'}</div>
                  </div>
                  <span className={`score-bdg ${scoreTier(farmer.trust_score)}`}>
                    {farmer.trust_score > 0 ? Math.round(farmer.trust_score) : '—'}
                  </span>
                </div>
                <div className="review-rec">
                  {farmer.trust_score < 40
                    ? 'Defer credit and require dues recovery'
                    : 'Review manually before approval'}
                </div>
                <div className="review-reason">
                  {farmer.membership_status === 'suspended'
                    ? 'Account suspended'
                    : farmer.trust_score === 0
                    ? 'No payment or production data recorded yet'
                    : 'Trust score below credit threshold'}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  )
}
