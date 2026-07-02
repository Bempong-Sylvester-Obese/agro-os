// src/components/dashboard/Payments.jsx
import { useEffect, useState } from 'react'
import { fetchPaymentsDashboard } from '../../api/transactions'

export default function Payments() {
  const [loading, setLoading] = useState(true)
  const [dashboard, setDashboard] = useState(null)

  useEffect(() => {
    let mounted = true

    fetchPaymentsDashboard()
      .then((data) => {
        if (mounted) setDashboard(data)
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })

    return () => {
      mounted = false
    }
  }, [])

  const stats = dashboard?.stats ?? []
  const rows = dashboard?.rows ?? []
  const sourceLabel = dashboard?.source === 'api' ? 'Live API' : 'Demo data'

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

      <div className="admin-card">
        <div className="admin-card-head">
          <span className="admin-card-title serif">Payment history</span>
          <span className="admin-card-action">{loading ? 'Loading…' : sourceLabel}</span>
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
