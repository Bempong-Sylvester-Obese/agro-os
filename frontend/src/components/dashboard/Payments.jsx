// src/components/dashboard/Payments.jsx
import { PAYMENTS } from '../../data/payments'

export default function Payments() {
  return (
    <>
      <div className="pay-stats">
        {[
          ['Total collected', 'GHS 29,760', 'June 2026'],
          ['Via MoMo',        'GHS 18,240', '61% of total'],
          ['Via USSD',        'GHS 7,800',  '26% of total'],
        ].map(([lbl, val, sub]) => (
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
          <span className="admin-card-action">Export CSV →</span>
        </div>
        <div className="pay-head">
          {['Member','Amount','Method','Date','Status'].map(h => (
            <span key={h} className="pt-lbl">{h}</span>
          ))}
        </div>
        {PAYMENTS.map(([name, id, amt, method, date, status, cls]) => (
          <div key={name + date} className="pay-row">
            <div>
              <div className="pt-name">{name}</div>
              <div className="pt-id">{id}</div>
            </div>
            <span className="pt-v">{amt}</span>
            <span className="pt-m">{method}</span>
            <span className="pt-m">{date}</span>
            <span className={`bdg ${cls}`}>{status}</span>
          </div>
        ))}
      </div>
    </>
  )
}
