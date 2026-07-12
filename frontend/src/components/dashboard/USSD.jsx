// src/components/dashboard/USSD.jsx
import { useEffect, useState } from 'react'
import { fetchUssdLogs, formatUssdTime, simulatePaymentWebhook } from '../../api/ussd'
import { USSDLogsSkeleton } from './DashboardSkeleton'

export default function USSD() {
  const [loading, setLoading] = useState(true)
  const [logs, setLogs] = useState([])
  const [source, setSource] = useState('demo')
  const [simulateTxId, setSimulateTxId] = useState('')
  const [simulateMsg, setSimulateMsg] = useState('')
  const [simulateErr, setSimulateErr] = useState('')

  function loadLogs() {
    setLoading(true)
    fetchUssdLogs()
      .then((data) => {
        setLogs(data.logs)
        setSource(data.source)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadLogs()
  }, [])

  async function handleSimulate(e) {
    e.preventDefault()
    setSimulateErr('')
    setSimulateMsg('')
    const txId = parseInt(simulateTxId, 10)
    if (Number.isNaN(txId)) {
      setSimulateErr('Enter a valid pending transaction ID.')
      return
    }
    try {
      const result = await simulatePaymentWebhook({ transactionId: txId })
      setSimulateMsg(result.message || 'Payment simulated successfully.')
      loadLogs()
    } catch (err) {
      setSimulateErr(err.message || 'Simulation failed.')
    }
  }

  const sourceLabel = source === 'api' ? 'Live API' : 'Demo data'

  return (
    <>
      <div className="info-banner" style={{ marginBottom: 20 }}>
        USSD sessions appear here after farmers interact with the Moolre short code.
        Use the demo simulator below when Moolre sandbox access is unavailable.
      </div>

      <div className="admin-card" style={{ marginBottom: 20 }}>
        <div className="admin-card-head">
          <span className="admin-card-title serif">Simulate payment webhook</span>
          <span className="admin-card-action">Demo fallback</span>
        </div>
        <form onSubmit={handleSimulate} style={{ display: 'flex', gap: 12, alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div className="auth-field" style={{ flex: '1 1 200px' }}>
            <label className="auth-label">Pending transaction ID</label>
            <input
              className="auth-input"
              placeholder="e.g. 1"
              value={simulateTxId}
              onChange={(e) => setSimulateTxId(e.target.value)}
            />
          </div>
          <button type="submit" className="btn-nav" style={{ fontSize: 12, padding: '10px 18px' }}>
            Simulate payment →
          </button>
        </form>
        {simulateErr && <div className="auth-error" style={{ marginTop: 12 }}>{simulateErr}</div>}
        {simulateMsg && (
          <div className="info-banner" style={{ marginTop: 12, marginBottom: 0 }}>
            {simulateMsg}
          </div>
        )}
      </div>

      <div className="admin-card">
        <div className="admin-card-head">
          <span className="admin-card-title serif">Recent USSD activity</span>
          <span className="admin-card-action">{loading ? '' : sourceLabel}</span>
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
              <div className="pt-name">No USSD sessions recorded yet.</div>
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
