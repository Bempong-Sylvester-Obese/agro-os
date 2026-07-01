// src/components/dashboard/Production.jsx
import { useEffect, useState } from 'react'
import { fetchProductionDashboard } from '../../api/production'

export default function Production() {
  const [loading, setLoading] = useState(true)
  const [dashboard, setDashboard] = useState(null)

  useEffect(() => {
    let mounted = true
    fetchProductionDashboard()
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
  const records = dashboard?.records ?? []
  const sourceLabel = dashboard?.source === 'api' ? 'Live API' : 'Demo data'

  return (
    <>
      <div className="stat-row">
        {loading
          ? ['Active crop cycles', 'Expected yield', 'Actual harvest'].map((lbl) => (
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
          <span className="admin-card-title serif">Production records</span>
          <span className="admin-card-action">{loading ? 'Loading…' : sourceLabel}</span>
        </div>

        {dashboard?.source === 'demo' && !loading && (
          <div className="auth-error" style={{ margin: '0 0 16px' }}>
            API unreachable — showing demo production data.
          </div>
        )}

        <div className="mt-head">
          {['Farmer', 'Crop', 'Season', 'Expected', 'Actual', 'Grade'].map((h) => (
            <span key={h} className="pt-lbl">{h}</span>
          ))}
        </div>

        {loading && (
          <div className="mt-row">
            <div className="pt-name">Loading production records…</div>
          </div>
        )}

        {!loading && records.length === 0 && (
          <div className="mt-row">
            <div className="pt-name">No production records yet.</div>
          </div>
        )}

        {!loading && records.map((record) => (
          <div key={record.id} className="mt-row">
            <div>
              <div className="pt-name">{record.farmer_name}</div>
              <div className="pt-id">#{record.farmer_id}</div>
            </div>
            <span className="pt-m">{record.crop_type}</span>
            <span className="pt-m">{record.season || '—'}</span>
            <span className="pt-v">{record.expected_kg ? `${record.expected_kg} kg` : '—'}</span>
            <span className="pt-v">{record.quantity_kg ? `${record.quantity_kg} kg` : 'Pending'}</span>
            <span className={`bdg ${record.quality_grade === 'A' ? 'bdg-green' : 'bdg-amber'}`}>
              {record.quality_grade || '—'}
            </span>
          </div>
        ))}
      </div>
    </>
  )
}
