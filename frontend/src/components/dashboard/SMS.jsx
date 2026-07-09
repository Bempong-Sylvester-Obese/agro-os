// src/components/dashboard/SMS.jsx
import { useCallback, useEffect, useState } from 'react'
import {
  fetchCommunicationLogs,
  fetchFarmers,
  resolveCooperativeId,
  sendDuesReminder,
  sendSmsBroadcast,
} from '../../api/communications'
import { FARMER_ASSESSMENTS } from '../../data/payments'

const DEMO_HISTORY = [
  ['June dues reminder: Please pay by June 10th via MoMo or USSD.', 'Jun 01', FARMER_ASSESSMENTS.length, 'sent'],
  ['Harvest season meeting: Saturday 8th at Cooperative HQ, 10AM.', 'May 28', FARMER_ASSESSMENTS.length, 'sent'],
  ['New production tracking feature is now live. Log your yields today.', 'May 15', FARMER_ASSESSMENTS.length, 'sent'],
]

const STATUS_LABEL = {
  sent: 'Delivered',
  partial_fail: 'Partial',
  failed: 'Failed',
}

function formatDate(iso) {
  const d = new Date(iso)
  return d.toLocaleDateString('en-GB', { month: 'short', day: 'numeric' })
}

function formatLog(log) {
  return [log.body, formatDate(log.sent_at), log.recipients_count, log.status]
}

export default function SMS() {
  const [msg, setMsg] = useState('')
  const [history, setHistory] = useState(DEMO_HISTORY)
  const [recipientCount, setRecipientCount] = useState(FARMER_ASSESSMENTS.length)
  const [cooperativeId, setCooperativeId] = useState(null)
  const [source, setSource] = useState('demo')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const loadData = useCallback(async () => {
    setLoading(true)
    setError('')

    try {
      const coopId = await resolveCooperativeId()
      const [farmers, logs] = await Promise.all([
        fetchFarmers(coopId),
        fetchCommunicationLogs(coopId),
      ])

      setCooperativeId(coopId)
      setRecipientCount(farmers.length)
      setHistory(logs.length ? logs.map(formatLog) : [])
      setSource('api')
    } catch {
      setCooperativeId(null)
      setRecipientCount(FARMER_ASSESSMENTS.length)
      setHistory(DEMO_HISTORY)
      setSource('demo')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  async function handleSendBroadcast() {
    if (!msg.trim()) {
      setError('Enter a message before sending.')
      return
    }
    if (msg.length > 160) {
      setError('Message must be 160 characters or fewer.')
      return
    }

    setSending(true)
    setError('')
    setSuccess('')

    try {
      const coopId = cooperativeId ?? (await resolveCooperativeId())
      const result = await sendSmsBroadcast({
        cooperativeId: coopId,
        message: msg.trim(),
        sentBy: 'dashboard',
      })

      setMsg('')
      setSuccess(`Broadcast sent to ${result.recipients_count} recipient(s).`)
      await loadData()
    } catch (err) {
      setError(err.message || 'Failed to send broadcast.')
    } finally {
      setSending(false)
    }
  }

  async function handleSendDuesReminder() {
    setSending(true)
    setError('')
    setSuccess('')

    const dueDate = new Date()
    dueDate.setDate(dueDate.getDate() + 10)
    const dueDateLabel = dueDate.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    })

    try {
      const coopId = cooperativeId ?? (await resolveCooperativeId())
      const result = await sendDuesReminder({
        cooperativeId: coopId,
        amount: 120,
        dueDate: dueDateLabel,
        sentBy: 'dashboard',
      })

      setSuccess(`Dues reminder sent to ${result.recipients_count} recipient(s).`)
      await loadData()
    } catch (err) {
      setError(err.message || 'Failed to send dues reminder.')
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
          {source === 'demo' && (
            <span style={{ fontSize: 11, color: 'var(--muted)' }}>Demo data</span>
          )}
        </div>
        <div style={{ padding: 20 }}>
          <div className="sms-lbl">Recipients</div>
          <select className="sms-select" disabled={loading}>
            <option>All members ({recipientCount})</option>
          </select>

          <div className="sms-lbl">Message</div>
          <textarea
            className="sms-textarea"
            placeholder="Type your message here..."
            value={msg}
            onChange={(e) => setMsg(e.target.value)}
            disabled={sending}
          />
          <div style={{ fontSize: 11, color: 'var(--muted)', textAlign: 'right', margin: '5px 0 14px' }}>
            {msg.length} / 160 characters
          </div>

          {error && (
            <div className="auth-error" style={{ marginBottom: 12, fontSize: 12 }}>{error}</div>
          )}
          {success && (
            <div style={{ marginBottom: 12, fontSize: 12, color: 'var(--green, #2d6a4f)' }}>{success}</div>
          )}

          <button
            className="btn-lg"
            style={{ width: '100%', padding: 11, fontSize: 14, marginBottom: 10 }}
            onClick={handleSendBroadcast}
            disabled={sending || loading}
          >
            {sending ? 'Sending…' : 'Send broadcast →'}
          </button>

          <button
            className="btn-out-lg"
            style={{ width: '100%', padding: 11, fontSize: 13 }}
            onClick={handleSendDuesReminder}
            disabled={sending || loading}
          >
            Send dues reminder (GHS 120)
          </button>
        </div>
      </div>

      {/* History */}
      <div className="admin-card">
        <div className="admin-card-head">
          <span className="admin-card-title serif">Broadcast history</span>
        </div>
        {loading && (
          <div style={{ padding: 20, fontSize: 13, color: 'var(--muted)' }}>Loading history…</div>
        )}
        {!loading && history.length === 0 && (
          <div style={{ padding: 20, fontSize: 13, color: 'var(--muted)' }}>No broadcasts sent yet.</div>
        )}
        {!loading && history.map(([message, date, rcpts, status]) => (
          <div key={`${date}-${message.slice(0, 24)}`} className="sms-row">
            <div className="sms-msg">{message}</div>
            <div className="sms-meta">
              <span>{date}</span>
              <span>{rcpts} recipients</span>
              <span className="sms-rate">{STATUS_LABEL[status] ?? status}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
