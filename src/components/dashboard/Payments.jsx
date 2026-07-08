// src/components/dashboard/Payments.jsx
import { useState, useEffect, useCallback } from 'react'
import { transactionsApi } from '../../lib/api'

const STATUS_CLS = { completed: 'bdg-green', pending: 'bdg-amber', failed: 'bdg-red' }
const STATUS_LABEL = { completed: 'Paid', pending: 'Pending', failed: 'Failed' }

function fmtAmount(tx) {
  return `${tx.currency} ${tx.amount.toLocaleString()}`
}

function fmtDate(iso) {
  try {
    return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
  } catch { return iso }
}

export default function Payments({ members }) {
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [collecting, setCollecting] = useState(null)
  const [collectAmount, setCollectAmount] = useState('50')

  const memberByFarmerId = Object.fromEntries((members || []).map(m => [m.farmerId, m]))

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await transactionsApi.list({ limit: 100 })
      setTransactions(data)
    } catch (err) {
      setError(err.message || 'Could not load transactions from the AgroOS API.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const totalCollected = transactions
    .filter(t => t.status === 'completed' && t.transaction_type === 'dues')
    .reduce((s, t) => s + t.amount, 0)
  const viaMomo = transactions
    .filter(t => t.status === 'completed' && t.channel === '13')
    .reduce((s, t) => s + t.amount, 0)
  const viaUssd = transactions
    .filter(t => t.status === 'completed' && (t.channel === '6' || t.channel === '7'))
    .reduce((s, t) => s + t.amount, 0)

  async function handleCollect(farmerId) {
    setCollecting(farmerId)
    try {
      await transactionsApi.collectDues({
        farmer_id: farmerId,
        amount: parseFloat(collectAmount) || 50,
        channel: '13',
        description: 'Cooperative dues payment',
      })
      await load()
    } catch (err) {
      setError(err.message || 'Could not initiate dues collection. Is MOOLRE_API_USER configured?')
    } finally {
      setCollecting(null)
    }
  }

  return (
    <>
      <div className="pay-stats">
        {[
          ['Total dues collected', `GHS ${totalCollected.toLocaleString()}`, 'From completed dues transactions'],
          ['Via MoMo',        `GHS ${viaMomo.toLocaleString()}`,  'Channel 13'],
          ['Via USSD',        `GHS ${viaUssd.toLocaleString()}`,  'Channels 6 / 7'],
        ].map(([lbl, val, sub]) => (
          <div key={lbl} className="stat-card">
            <div className="stat-lbl">{lbl}</div>
            <div className="stat-val serif">{val}</div>
            <div className="stat-sub">{sub}</div>
          </div>
        ))}
      </div>

      {/* Manual dues collection trigger */}
      <div className="admin-card" style={{ marginBottom: 20, padding: 20 }}>
        <div className="admin-card-title serif" style={{ marginBottom: 12 }}>Collect dues via Moolre USSD push</div>
        {error && <div className="auth-error" style={{ marginBottom: 12 }}>{error}</div>}
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <input
            className="auth-input"
            style={{ maxWidth: 120 }}
            type="number"
            min="1"
            value={collectAmount}
            onChange={e => setCollectAmount(e.target.value)}
          />
          <span style={{ fontSize: 12, color: 'var(--muted)' }}>GHS per member, then pick who to charge:</span>
          <select
            className="auth-input auth-select"
            style={{ maxWidth: 260 }}
            onChange={e => e.target.value && handleCollect(parseInt(e.target.value, 10))}
            value=""
            disabled={collecting !== null}
          >
            <option value="">{collecting ? 'Sending request…' : 'Select a member…'}</option>
            {(members || []).map(m => (
              <option key={m.farmerId} value={m.farmerId}>{m.name} — {m.phone}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="admin-card">
        <div className="admin-card-head">
          <span className="admin-card-title serif">Payment history</span>
          <span className="admin-card-action" style={{ cursor: 'pointer' }} onClick={load}>Refresh →</span>
        </div>
        <div className="pay-head">
          {['Member','Amount','Type','Date','Status'].map(h => (
            <span key={h} className="pt-lbl">{h}</span>
          ))}
        </div>
        {loading && <div style={{ padding: 24, textAlign: 'center', color: 'var(--muted)' }}>Loading transactions…</div>}
        {!loading && transactions.length === 0 && (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>
            No transactions yet. Use the form above to collect dues from a member.
          </div>
        )}
        {!loading && transactions.map(tx => {
          const member = memberByFarmerId[tx.farmer_id]
          return (
            <div key={tx.id} className="pay-row">
              <div>
                <div className="pt-name">{member?.name ?? `Farmer #${tx.farmer_id}`}</div>
                <div className="pt-id">{member?.id ?? ''}</div>
              </div>
              <span className="pt-v">{fmtAmount(tx)}</span>
              <span className="pt-m" style={{ textTransform: 'capitalize' }}>{tx.transaction_type}</span>
              <span className="pt-m">{fmtDate(tx.created_at)}</span>
              <span className={`bdg ${STATUS_CLS[tx.status] ?? 'bdg-amber'}`}>{STATUS_LABEL[tx.status] ?? tx.status}</span>
            </div>
          )
        })}
      </div>
    </>
  )
}
