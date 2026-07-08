// src/components/dashboard/Overview.jsx
import { useState, useEffect } from 'react'
import { transactionsApi } from '../../lib/api'

const STATUS_CLS = { completed: 'bdg-green', pending: 'bdg-amber', failed: 'bdg-red' }
const STATUS_LABEL = { completed: 'Paid', pending: 'Pending', failed: 'Failed' }

function fmtDate(iso) {
  try { return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' }) }
  catch { return iso }
}

function AllPaymentsModal({ transactions, memberByFarmerId, onClose }) {
  const [filter, setFilter] = useState('All')
  const statusMap = { All: null, Paid: 'completed', Pending: 'pending', Failed: 'failed' }
  const filtered = filter === 'All' ? transactions : transactions.filter(t => t.status === statusMap[filter])

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 680 }}>
        <div className="modal-head">
          <div>
            <div className="modal-title serif">All payments</div>
            <div className="modal-sub">{transactions.length} transactions</div>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

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
          {['Member','Amount','Type','Date','Status'].map(h => (
            <span key={h} className="pt-lbl">{h}</span>
          ))}
        </div>
        <div style={{ maxHeight: 340, overflowY: 'auto' }}>
          {filtered.map(tx => {
            const member = memberByFarmerId[tx.farmer_id]
            return (
              <div key={tx.id} className="pt-row" style={{ gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr' }}>
                <div>
                  <div className="pt-name">{member?.name ?? `Farmer #${tx.farmer_id}`}</div>
                  <div className="pt-id">{member?.id ?? ''}</div>
                </div>
                <span className="pt-v">{tx.currency} {tx.amount.toLocaleString()}</span>
                <span className="pt-m" style={{ textTransform: 'capitalize' }}>{tx.transaction_type}</span>
                <span className="pt-m">{fmtDate(tx.created_at)}</span>
                <span className={`bdg ${STATUS_CLS[tx.status] ?? 'bdg-amber'}`}>{STATUS_LABEL[tx.status] ?? tx.status}</span>
              </div>
            )
          })}
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
            <div className="modal-sub">AgroCredit scores for all {members.length} members</div>
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
  const [transactions, setTransactions] = useState([])

  useEffect(() => {
    transactionsApi.list({ limit: 100 }).then(setTransactions).catch(() => setTransactions([]))
  }, [])

  const recentTransactions = transactions.slice(0, 5)
  const memberByFarmerId = Object.fromEntries((members || []).map(m => [m.farmerId, m]))

  const total    = members.length
  const duesPaid = members.filter(m => m.dues === 'Paid').length
  const duesCollectedTotal = transactions
    .filter(t => t.status === 'completed' && t.transaction_type === 'dues')
    .reduce((s, t) => s + t.amount, 0)
  const pendingTx = transactions.filter(t => t.status === 'pending')
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
          ['Total members',          String(total),                      `${duesPaid} dues paid`],
          ['Dues collected',         `GHS ${duesCollectedTotal.toLocaleString()}`, 'All-time, completed'],
          ['Pending transactions',   String(pendingTx.length),           `${pendingTx.length} awaiting confirmation`],
          ['Avg trust score',        avgScore,                           'Live AgroCredit average'],
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
            {['Member', 'Amount', 'Type', 'Date', 'Status'].map(h => (
              <span key={h} className="pt-lbl">{h}</span>
            ))}
          </div>
          {recentTransactions.length === 0 && (
            <div style={{ padding: '20px 22px', color: 'var(--muted)', fontSize: 13 }}>No transactions yet.</div>
          )}
          {recentTransactions.map(tx => {
            const member = memberByFarmerId[tx.farmer_id]
            return (
              <div key={tx.id} className="pt-row">
                <div>
                  <div className="pt-name">{member?.name ?? `Farmer #${tx.farmer_id}`}</div>
                  <div className="pt-id">{member?.id ?? ''}</div>
                </div>
                <span className="pt-v">{tx.currency} {tx.amount.toLocaleString()}</span>
                <span className="pt-m" style={{ textTransform: 'capitalize' }}>{tx.transaction_type}</span>
                <span className="pt-m">{fmtDate(tx.created_at)}</span>
                <span className={`bdg ${STATUS_CLS[tx.status] ?? 'bdg-amber'}`}>{STATUS_LABEL[tx.status] ?? tx.status}</span>
              </div>
            )
          })}
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
          {topScores.length === 0 && (
            <div style={{ padding: '20px 22px', color: 'var(--muted)', fontSize: 13 }}>No members yet.</div>
          )}
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

      {showPayments && <AllPaymentsModal transactions={transactions} memberByFarmerId={memberByFarmerId} onClose={() => setShowPayments(false)} />}
      {showScores   && <AllScoresModal members={members} onClose={() => setShowScores(false)} />}
    </>
  )
}
