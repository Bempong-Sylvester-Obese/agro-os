// src/components/dashboard/Overview.jsx
import { PAYMENTS } from '../../data/payments'

const TOP_SCORES = [
  ['#1 Kofi Darko',   'Brong-Ahafo', '92', 'sh'],
  ['#2 Abena Mensah', 'Ashanti',     '87', 'sh'],
  ['#3 Yaw Frimpong', 'Volta',       '79', 'sm'],
  ['#4 Kwame Asante', 'Northern',    '74', 'sm'],
]

export default function Overview() {
  return (
    <>
      <div className="stat-row">
        {[
          ['Total members',          '248',        '+12 this month'],
          ['Dues collected',         'GHS 29,760', 'June 2026'],
          ['Pending disbursements',  'GHS 4,200',  '3 pending'],
          ['Avg trust score',        '74.2',       '+3.1 vs last month'],
        ].map(([lbl, val, sub]) => (
          <div key={lbl} className="stat-card">
            <div className="stat-lbl">{lbl}</div>
            <div className="stat-val serif">{val}</div>
            <div className="stat-sub">{sub}</div>
          </div>
        ))}
      </div>

      <div className="admin-grid">
        {/* Recent payments */}
        <div className="admin-card">
          <div className="admin-card-head">
            <span className="admin-card-title serif">Recent payments</span>
            <span className="admin-card-action">View all →</span>
          </div>
          <div className="pt-head">
            {['Member','Amount','Method','Date','Status'].map(h => (
              <span key={h} className="pt-lbl">{h}</span>
            ))}
          </div>
          {PAYMENTS.map(([name, id, amt, method, date, status, cls]) => (
            <div key={name} className="pt-row">
              <div>
                <div className="pt-name">{name}</div>
                <div className="pt-id">{id}</div>
              </div>
              <span className="pt-v">{amt}</span>
              <span className="pt-m">{method}</span>
              <span className="pt-m">{date.split(',')[0]}</span>
              <span className={`bdg ${cls}`}>{status}</span>
            </div>
          ))}
        </div>

        {/* Top trust scores */}
        <div className="admin-card">
          <div className="admin-card-head">
            <span className="admin-card-title serif">Top trust scores</span>
            <span className="admin-card-action">View all →</span>
          </div>
          {TOP_SCORES.map(([name, region, score, tier]) => (
            <div key={name} className="score-item">
              <div>
                <div className="score-item-name">{name}</div>
                <div className="score-item-region">{region}</div>
              </div>
              <span className={`score-bdg ${tier}`}>{score}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  )
}
