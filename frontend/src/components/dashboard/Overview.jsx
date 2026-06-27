// src/components/dashboard/Overview.jsx
import { useState } from 'react'
import { PAYMENTS } from '../../data/payments'

function AllPaymentsModal({ onClose }) {
  const [filter, setFilter] = useState('All')
  const filtered = filter === 'All' ? PAYMENTS : PAYMENTS.filter(([,,,,,status]) => status === filter)

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 680 }}>
        <div className="modal-head">
          <div>
            <div className="modal-title serif">All payments</div>
            <div className="modal-sub">{PAYMENTS.length} transactions · June 2026</div>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        {/* Filter tabs */}
        <div style={{ display: 'flex', gap: 6, marginBottom: 18 }}>
          {['All','Paid','Pending','Failed'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                padding: '5px 14px', borderRadius: 99, fontSize: 12, fontWeight: 600,
                border: '1.5px solid ' + (filter === f ? 'var(--g)' : 'var(--border)'),
                background: filter === f ? 'var(--g)' : '#fff',
                color: filter === f ? '#fff' : 'var(--text)',
                cursor: 'pointer',
              }}
            >{f}</button>
          ))}
        </div>

        <div className="pt-head" style={{ gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr' }}>
          {['Member','Amount','Method','Date','Status'].map(h => (
            <span key={h} className="pt-lbl">{h}</span>
          ))}
        </div>
        <div style={{ maxHeight: 340, overflowY: 'auto' }}>
          {filtered.map(([name, id, amt, method, date, status, cls]) => (
            <div key={name+date} className="pt-row" style={{ gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr' }}>
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
          {filtered.length === 0 && (
            <div style={{ textAlign: 'center', padding: '32px', color: 'var(--muted)', fontSize: 13 }}>No {filter.toLowerCase()} payments found.</div>
          )}
        </div>
        <div style={{ marginTop: 16, paddingTop: 14, borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'flex-end' }}>
          <button className="btn-out-lg" style={{ fontSize: 12, padding: '8px 18px' }} onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  )
}

function AllScoresModal({ members, onClose }) {
  const sorted = [...members].sort((a,b) => parseInt(b.score,10) - parseInt(a.score,10))

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 560 }}>
        <div className="modal-head">
          <div>
            <div className="modal-title serif">All trust scores</div>
            <div className="modal-sub">AgroCredit scores for all {members.length} members · Updated monthly</div>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: 0, marginBottom: 8 }}>
          {['Member','Region','Score'].map(h => (
            <span key={h} className="pt-lbl" style={{ paddingLeft: h === 'Member' ? 0 : 8 }}>{h}</span>
          ))}
        </div>

        <div style={{ maxHeight: 380, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 2 }}>
          {sorted.map((m, i) => (
            <div key={m.id} style={{
              display: 'grid', gridTemplateColumns: '2fr 1fr 1fr',
              alignItems: 'center', padding: '10px 0',
              borderBottom: '1px solid var(--border)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ fontSize: 11, color: 'var(--muted)', minWidth: 20 }}>#{i+1}</div>
                <div>
                  <div className="pt-name">{m.name}</div>
                  <div className="pt-id">{m.id}</div>
                </div>
              </div>
              <span className="pt-m">{m.region}</span>
              <span className={`score-bdg ${m.tier}`}>{m.score}</span>
            </div>
          ))}
        </div>

        <div style={{ marginTop: 16, paddingTop: 14, borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'flex-end' }}>
          <button className="btn-out-lg" style={{ fontSize: 12, padding: '8px 18px' }} onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  )
}

export default function Overview({ members }) {
  const [showPayments, setShowPayments] = useState(false)
  const [showScores,   setShowScores]   = useState(false)

  const total   = members.length
  const paid    = members.filter(m => m.dues === 'Paid').length
  const avgScore = members.length
    ? (members.reduce((s, m) => s + parseInt(m.score, 10), 0) / members.length).toFixed(1)
    : '—'

  const topScores = [...members]
    .sort((a, b) => parseInt(b.score, 10) - parseInt(a.score, 10))
    .slice(0, 4)
    .map((m, i) => [`#${i + 1} ${m.name}`, m.region, m.score, m.tier])

  return (
    <>
      <div className="stat-row">
        {[
          ['Total members',          String(total),           `+${Math.max(0, total - 6)} this month`],
          ['Dues collected',         'GHS 29,760',            'June 2026'],
          ['Pending disbursements',  'GHS 4,200',             '3 pending'],
          ['Avg trust score',        avgScore,                '+3.1 vs last month'],
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
            <span
              className="admin-card-action"
              style={{ cursor: 'pointer' }}
              onClick={() => setShowPayments(true)}
            >View all →</span>
          </div>
          <div className="pt-head">
            {['Member', 'Amount', 'Method', 'Date', 'Status'].map(h => (
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

        {/* Top trust scores */}
        <div className="admin-card">
          <div className="admin-card-head">
            <span className="admin-card-title serif">Top trust scores</span>
            <span
              className="admin-card-action"
              style={{ cursor: 'pointer' }}
              onClick={() => setShowScores(true)}
            >View all →</span>
          </div>
          {topScores.map(([name, region, score, tier]) => (
            <div key={name} className="score-item">
              <div>
                <div className="score-item-name">{name}</div>
                <div className="score-item-region">{region}</div>
              </div>
              <span className={`score-bdg ${tier}`}>{score}</span>
            </div>
          ))}
        </div>
      </div>

      {showPayments && <AllPaymentsModal onClose={() => setShowPayments(false)} />}
      {showScores   && <AllScoresModal members={members} onClose={() => setShowScores(false)} />}
    </>
  )
}
