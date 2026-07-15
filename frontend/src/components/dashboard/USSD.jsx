// src/components/dashboard/USSD.jsx
import { useEffect, useState } from 'react'
import { fetchUssdLogs, formatUssdTime } from '../../api/ussd'
import { USSDLogsSkeleton } from './DashboardSkeleton'

export default function USSD() {
  const [loading, setLoading] = useState(true)
  const [logs, setLogs] = useState([])
  const [error, setError] = useState(null)

  function loadLogs() {
    setLoading(true)
    setError(null)
    fetchUssdLogs()
      .then((data) => setLogs(data.logs))
      .catch((err) => {
        setLogs([])
        setError(err.message || 'Could not load USSD activity.')
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadLogs()
  }, [])

  return (
    <>
      <div className="info-banner" style={{ marginBottom: 20 }}>
        Live USSD sessions from Moolre appear here when farmers dial your cooperative merchant code.
        Payments confirmed via Moolre webhooks update the Payments tab automatically.
      </div>

      {error && (
        <div
          className="info-banner info-banner-row"
          style={{
            marginBottom: 20,
            background: '#FEF2F2',
            borderColor: '#FECACA',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 16,
          }}
        >
          <span>{error}</span>
          <button
            type="button"
            className="btn-lg"
            style={{ padding: '8px 16px', fontSize: 13, flexShrink: 0 }}
            onClick={loadLogs}
          >
            Retry
          </button>
        </div>
      )}

      <div className="admin-card">
        <div className="admin-card-head">
          <span className="admin-card-title serif">Recent USSD activity</span>
          <button
            type="button"
            className="admin-card-action"
            style={{ background: 'none', border: 'none', cursor: 'pointer', font: 'inherit' }}
            onClick={loadLogs}
            disabled={loading}
          >
            {loading ? 'Loading…' : 'Refresh'}
          </button>
        </div>

        <div className="table-scroll">
          <div className="mt-head mt-head-4">
            {['Phone', 'Menu path', 'Response', 'Time'].map((h) => (
              <span key={h} className="pt-lbl">{h}</span>
            ))}
          </div>

          {loading ? (
            <USSDLogsSkeleton />
          ) : logs.length === 0 ? (
            <div className="mt-row mt-row-4">
              <div className="pt-name" style={{ gridColumn: '1 / -1' }}>
                No USSD sessions recorded yet. When a farmer dials your Moolre code, activity will show here.
              </div>
            </div>
          ) : (
            logs.map((log) => (
              <div key={log.id} className="mt-row mt-row-4">
                <span className="pt-m" style={{ fontSize: 11 }}>{log.phone}</span>
                <span className="pt-m">{log.input_path || 'menu'}</span>
                <span className="pt-m" style={{ fontSize: 11, whiteSpace: 'pre-line' }}>
                  {(log.response_text || '').slice(0, 80)}{(log.response_text || '').length > 80 ? '…' : ''}
                </span>
                <span className="pt-m">{formatUssdTime(log.created_at)}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </>
  )
}
