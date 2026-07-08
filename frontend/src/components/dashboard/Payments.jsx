// src/components/dashboard/Payments.jsx
import { useCallback, useEffect, useState } from 'react'
import { collectDues, fetchPaymentsDashboard } from '../../api/transactions'

export default function Payments({ dbFarmers }) {
  const [loading, setLoading] = useState(true)
  const [dashboard, setDashboard] = useState(null)
  const [collectError, setCollectError] = useState('')
  const [collecting, setCollecting] = useState(null)
  const [collectAmount, setCollectAmount] = useState('50')

  const load = useCallback(() => {
    setLoading(true)
    return fetchPaymentsDashboard()
      .then((data) => setDashboard(data))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const stats = dashboard?.stats ?? []
  const rows = dashboard?.rows ?? []
  const sourceLabel = dashboard?.source === 'api' ? 'Live API' : 'Demo data'
  const farmers = dbFarmers?.farmers ?? dashboard?.farmers ?? []
  const canCollect = dashboard?.source === 'api' && farmers.length > 0

  async function handleCollect(farmerId) {
    setCollecting(farmerId)
    setCollectError('')
    try {
      await collectDues({
        farmer_id: farmerId,
        amount: parseFloat(collectAmount) || 50,
        channel: '13',
        description: 'Cooperative dues payment',
      })
      await load()
    } catch (err) {
      setCollectError(err.message || 'Could not initiate dues collection. Is MOOLRE_API_USER configured?')
    } finally {
      setCollecting(null)
    }
  }

  return (
    <>
      <div className="pay-stats">
        {loading
          ? ['Total collected', 'Via MoMo', 'Via USSD'].map((lbl) => (
              <div key={lbl} className="stat-card">
                <div className="stat-lbl">{lbl}</div>
                <div className="stat-val serif">…</div>
                <div className="stat-sub">Loading</div>
              </div>
            ))
          : stats.map(([lbl, val, sub]) => (
              <div key={lbl} className="stat-card">
                <div className="stat-lbl">{lbl}</div>
                <div className="stat-val serif">{val}</div>
                <div className="stat-sub">{sub}</div>
              </div>
            ))}
      </div>

      {canCollect && (
        <div className="admin-card" style={{ marginBottom: 20, padding: 20 }}>
          <div className="admin-card-title serif" style={{ marginBottom: 12 }}>Collect dues via Moolre USSD push</div>
          {collectError && <div className="auth-error" style={{ marginBottom: 12 }}>{collectError}</div>}
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <input
              className="auth-input"
              style={{ maxWidth: 120 }}
              type="number"
              min="1"
              value={collectAmount}
              onChange={(e) => setCollectAmount(e.target.value)}
            />
            <span style={{ fontSize: 12, color: 'var(--muted)' }}>GHS per member, then pick who to charge:</span>
            <select
              className="auth-input auth-select"
              style={{ maxWidth: 260 }}
              onChange={(e) => {
                const farmerId = parseInt(e.target.value, 10)
                if (!farmerId) return
                const farmer = farmers.find((f) => f.id === farmerId)
                if (window.confirm(`Send a GHS ${collectAmount} dues request to ${farmer?.name}?`)) {
                  handleCollect(farmerId)
                }
              }}
              value=""
              disabled={collecting !== null}
            >
              <option value="">{collecting ? 'Sending request…' : 'Select a member…'}</option>
              {farmers.map((farmer) => (
                <option key={farmer.id} value={farmer.id}>
                  {farmer.name} — {farmer.phone}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      <div className="admin-card">
        <div className="admin-card-head">
          <span className="admin-card-title serif">Payment history</span>
          <button
            type="button"
            className="admin-card-action"
            style={{ background: 'none', border: 'none', cursor: 'pointer' }}
            onClick={load}
            disabled={loading}
          >
            {loading ? 'Loading…' : `${sourceLabel} · Refresh →`}
          </button>
        </div>

        <div className="table-scroll">
          <div className="pay-head">
            {['Member', 'Amount', 'Method', 'Date', 'Status'].map((h) => (
              <span key={h} className="pt-lbl">{h}</span>
            ))}
          </div>

          {loading && (
            <div className="pay-row">
              <div className="pt-name">Loading payment history…</div>
            </div>
          )}

          {!loading && rows.length === 0 && (
            <div className="pay-row">
              <div className="pt-name">No transactions recorded yet.</div>
            </div>
          )}

          {!loading && rows.map((row) => (
            <div key={row.key} className="pay-row">
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
    </>
  )
}
