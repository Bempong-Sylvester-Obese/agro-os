// src/components/dashboard/SMS.jsx
import { useState, useEffect } from 'react'
import { fetchSMSLogs, sendBroadcast } from '../../api/communications'
import { SMSLogsSkeleton } from './DashboardSkeleton'

export default function SMS({ cooperativeId, memberCount = 0 }) {
  const [msg, setMsg]                 = useState('')
  const [logs, setLogs]               = useState([])
  const [loadingLogs, setLoadingLogs] = useState(true)
  const [sending, setSending]         = useState(false)
  const [sendSuccess, setSendSuccess] = useState(false)
  const [sendError, setSendError]     = useState(null)

  useEffect(() => {
    let mounted = true
    fetchSMSLogs(cooperativeId).then(data => {
      if (mounted) { setLogs(data); setLoadingLogs(false) }
    })
    return () => { mounted = false }
  }, [cooperativeId])

  const handleSend = async () => {
    if (!msg.trim()) return
    if (!cooperativeId) {
      setSendError('Cannot send: cooperative not found. Please log in again.')
      return
    }
    setSending(true)
    setSendSuccess(false)
    setSendError(null)
    try {
      await sendBroadcast(cooperativeId, msg)
      setMsg('')
      setSendSuccess(true)
      const newLogs = await fetchSMSLogs(cooperativeId)
      setLogs(newLogs)
      setTimeout(() => setSendSuccess(false), 3000)
    } catch (err) {
      setSendError(err.message || 'Failed to send broadcast. Check your Moolre SMS configuration.')
    } finally {
      setSending(false)
    }
  }

  const mappedLogs = logs.map(log => ({
    message: log.body,
    date: new Date(log.sent_at).toLocaleDateString('en-US', { month: 'short', day: '2-digit' }),
    recipients: `${log.recipients_count} recipient${log.recipients_count !== 1 ? 's' : ''}`,
    rate: log.status === 'success' || log.status === 'sent' ? '✓ Sent' : 'Failed',
    cls: log.status === 'success' || log.status === 'sent' ? 'bdg-green' : 'bdg-red',
    key: log.id,
  }))

  return (
    <div className="sms-grid">
      {/* ── Compose ── */}
      <div className="admin-card">
        <div className="admin-card-head">
          <span className="admin-card-title serif">Compose broadcast</span>
        </div>
        <div style={{ padding: 20 }}>
          <div className="sms-lbl">Recipients</div>
          <div style={{
            padding: '10px 12px', border: '1.5px solid var(--border)', borderRadius: 8,
            fontSize: 14, marginBottom: 16, background: 'var(--sage)',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <span>All active members</span>
            {memberCount > 0 && (
              <span style={{ fontSize: 12, color: 'var(--muted)' }}>{memberCount} members</span>
            )}
          </div>

          <label htmlFor="sms-message" className="sms-lbl">Message</label>
          <textarea
            id="sms-message"
            className="sms-textarea"
            placeholder="Type your message here…"
            value={msg}
            onChange={e => setMsg(e.target.value.slice(0, 160))}
            maxLength={160}
          />
          <div style={{
            fontSize: 11, color: msg.length > 140 ? '#DC4444' : 'var(--muted)',
            textAlign: 'right', margin: '5px 0 14px',
          }}>
            {msg.length} / 160 characters
          </div>

          {sendError && (
            <div style={{
              padding: '10px 14px', background: '#FEF2F2', color: '#991B1B',
              borderRadius: 8, marginBottom: 12, fontSize: 13, borderLeft: '3px solid #F87171',
            }}>
              {sendError}
            </div>
          )}

          <button
            className="btn-lg"
            style={{ width: '100%', padding: 11, fontSize: 14 }}
            onClick={handleSend}
            disabled={sending || msg.trim().length === 0}
          >
            {sending ? 'Sending…' : sendSuccess ? '✓ Sent!' : 'Send broadcast →'}
          </button>

          {!cooperativeId && (
            <div style={{ marginTop: 10, fontSize: 12, color: '#991B1B', textAlign: 'center' }}>
              ⚠ Cooperative ID not found — please log in again.
            </div>
          )}
        </div>
      </div>

      {/* ── Broadcast history ── */}
      <div className="admin-card">
        <div className="admin-card-head">
          <span className="admin-card-title serif">Broadcast history</span>
        </div>

        {loadingLogs ? (
          <SMSLogsSkeleton />
        ) : mappedLogs.length === 0 ? (
          <div style={{ padding: '28px 20px', color: 'var(--muted)', fontSize: 14 }}>
            No broadcasts sent yet. Send your first message to members above.
          </div>
        ) : (
          mappedLogs.map(({ message, date, recipients, rate, cls, key }) => (
            <div key={key} className="sms-row">
              <div className="sms-msg">{message}</div>
              <div className="sms-meta">
                <span>{date}</span>
                <span>{recipients}</span>
                <span className={`bdg ${cls}`} style={{ fontSize: 11 }}>{rate}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
