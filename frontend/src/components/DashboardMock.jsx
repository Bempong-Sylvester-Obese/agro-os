// src/components/DashboardMock.jsx
import React from 'react'

const MOCK_ROWS = [
  ['Abena Mensah', 'GHS 120', 'MoMo',  'Paid',    'bdg-green'],
  ['Kwame Asante', 'GHS 120', 'USSD',  'Paid',    'bdg-green'],
  ['Ama Osei',     'GHS 120', 'Card',  'Pending', 'bdg-amber'],
]

export default function DashboardMock() {
  return (
    <div className="mock">
      <div className="mock-bar">
        <span className="mock-bar-title">AgroOS Dashboard</span>
        <div className="mock-dots">
          <div className="mock-dot" style={{ background: '#FF5F57' }} />
          <div className="mock-dot" style={{ background: '#FFBD2E' }} />
          <div className="mock-dot" style={{ background: '#28C840' }} />
        </div>
      </div>

      <div className="mock-body">
        <div className="mock-side">
          {['Overview', 'Members', 'Payments', 'Scores', 'SMS'].map((n, i) => (
            <div key={n} className={`mock-nav${i === 0 ? ' on' : ''}`}>{n}</div>
          ))}
        </div>

        <div className="mock-main">
          <div className="mock-stats">
            {[['248','Members'],['GHS 29,760','Collected'],['74.2','Avg Score'],['12','Pending']].map(([v, l]) => (
              <div key={l} className="mock-stat">
                <div className="mock-stat-v">{v}</div>
                <div className="mock-stat-l">{l}</div>
              </div>
            ))}
          </div>

          <div className="mock-th">
            {['Member','Amount','Method','Status'].map(h => (
              <span key={h} className="mock-tl">{h}</span>
            ))}
          </div>

          {MOCK_ROWS.map(([name, amt, method, status, cls]) => (
            <div key={name} className="mock-tr">
              <span className="mock-tr-n">{name}</span>
              <span className="mock-tr-v">{amt}</span>
              <span className="mock-tr-v">{method}</span>
              <span className={`bdg ${cls}`}>{status}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
