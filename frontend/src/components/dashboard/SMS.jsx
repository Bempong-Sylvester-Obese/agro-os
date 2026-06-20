// src/components/dashboard/SMS.jsx
import { useState } from 'react'

const HISTORY = [
  ['June dues reminder: Please pay by June 10th via MoMo or USSD.', 'Jun 01', '248 recipients', '98% delivered'],
  ['Harvest season meeting: Saturday 8th at Cooperative HQ, 10AM.',  'May 28', '248 recipients', '96% delivered'],
  ['New production tracking feature is now live. Log your yields today.', 'May 15', '248 recipients', '99% delivered'],
]

export default function SMS() {
  const [msg, setMsg] = useState('')

  return (
    <div className="sms-grid">
      {/* Compose */}
      <div className="admin-card">
        <div className="admin-card-head">
          <span className="admin-card-title serif">Compose broadcast</span>
        </div>
        <div style={{ padding: 20 }}>
          <div className="sms-lbl">Recipients</div>
          <select className="sms-select">
            <option>All members (248)</option>
            <option>Dues paid — June</option>
            <option>Overdue members</option>
            <option>Northern region</option>
          </select>

          <div className="sms-lbl">Message</div>
          <textarea
            className="sms-textarea"
            placeholder="Type your message here..."
            value={msg}
            onChange={(e) => setMsg(e.target.value)}
          />
          <div style={{ fontSize: 11, color: 'var(--muted)', textAlign: 'right', margin: '5px 0 14px' }}>
            {msg.length} / 160 characters
          </div>

          <button className="btn-lg" style={{ width: '100%', padding: 11, fontSize: 14 }}>
            Send broadcast →
          </button>
        </div>
      </div>

      {/* History */}
      <div className="admin-card">
        <div className="admin-card-head">
          <span className="admin-card-title serif">Broadcast history</span>
        </div>
        {HISTORY.map(([message, date, rcpts, rate]) => (
          <div key={date} className="sms-row">
            <div className="sms-msg">{message}</div>
            <div className="sms-meta">
              <span>{date}</span>
              <span>{rcpts}</span>
              <span className="sms-rate">{rate}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
