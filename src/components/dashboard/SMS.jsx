// src/components/dashboard/SMS.jsx
import { useState, useEffect, useCallback } from 'react'
import { communicationsApi } from '../../lib/api'

function fmtDate(iso) {
  try { return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' }) }
  catch { return iso }
}

export default function SMS({ cooperativeId, sentBy }) {
  const [msg, setMsg] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [logs, setLogs] = useState([])
  const [loadingLogs, setLoadingLogs] = useState(true)

  const loadLogs = useCallback(async () => {
    setLoadingLogs(true)
    try {
      const data = await communicationsApi.logs({ cooperative_id: cooperativeId, limit: 50 })
      setLogs(data)
    } catch {
      setLogs([])
    } finally {
      setLoadingLogs(false)
    }
  }, [cooperativeId])

  useEffect(() => { loadLogs() }, [loadLogs])

  async function handleSend() {
    setError('')
    setSuccess('')
    if (!msg.trim()) { setError('Please write a message before sending.'); return }
    if (msg.length > 160) { setError('Message must be 160 characters or fewer.'); return }

    setSending(true)
    try {
      const res = await communicationsApi.broadcast({
        cooperative_id: cooperativeId,
        message: msg.trim(),
        sent_by: sentBy,
      })
      setSuccess(`Sent to ${res.recipients_count} recipient(s).`)
      setMsg('')
      await loadLogs()
    } catch (err) {
      setError(err.message || 'Could not send this broadcast. Check your Moolre SMS credentials.')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="sms-grid">
      {/* Compose */}
      <div className="admin-card">
        <div className="admin-card-head">
          <span className="admin-card-title serif">Compose broadcast</span>
        </div>
        <div style={{ padding: 20 }}>
          <div className="sms-lbl">Recipients</div>
          <select className="sms-select" disabled>
            <option>All active members of your cooperative</option>
          </select>

          {error && <div className="auth-error" style={{ margin: '10px 0 0' }}>{error}</div>}
          {success && (
            <div style={{
              background: 'rgba(82,183,136,.12)', color: 'var(--g)', fontSize: 12,
              padding: '8px 12px', borderRadius: 8, margin: '10px 0 0',
            }}>{success}</div>
          )}

          <div className="sms-lbl">Message</div>
          <textarea
            className="sms-textarea"
            placeholder="Type your message here..."
            value={msg}
            onChange={(e) => setMsg(e.target.value)}
            maxLength={160}
          />
          <div style={{ fontSize: 11, color: 'var(--muted)', textAlign: 'right', margin: '5px 0 14px' }}>
            {msg.length} / 160 characters
          </div>

          <button className="btn-lg" style={{ width: '100%', padding: 11, fontSize: 14 }} onClick={handleSend} disabled={sending}>
            {sending ? 'Sending…' : 'Send broadcast →'}
          </button>
        </div>
      </div>

      {/* History */}
      <div className="admin-card">
        <div className="admin-card-head">
          <span className="admin-card-title serif">Broadcast history</span>
          <span className="admin-card-action" style={{ cursor: 'pointer' }} onClick={loadLogs}>Refresh →</span>
        </div>
        {loadingLogs && <div style={{ padding: 20, color: 'var(--muted)', fontSize: 13 }}>Loading…</div>}
        {!loadingLogs && logs.length === 0 && (
          <div style={{ padding: 20, color: 'var(--muted)', fontSize: 13 }}>No broadcasts sent yet.</div>
        )}
        {!loadingLogs && logs.map(log => (
          <div key={log.id} className="sms-row">
            <div className="sms-msg">{log.body}</div>
            <div className="sms-meta">
              <span>{fmtDate(log.sent_at)}</span>
              <span>{log.recipients_count} recipients</span>
              <span className="sms-rate" style={{ textTransform: 'capitalize' }}>{log.status}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
