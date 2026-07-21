// src/components/DashboardMock.jsx
import { BarChart3, Users, Tractor, Star, CreditCard, Banknote, Inbox, MessageSquare, RefreshCw, Sprout } from 'lucide-react'

const NAV_GROUPS = [
  {
    label: 'Operations',
    items: [
      { label: 'Overview', icon: BarChart3, active: true },
      { label: 'Members', icon: Users },
      { label: 'Production', icon: Tractor },
      { label: 'Agro-AI scores', icon: Star },
    ],
  },
  {
    label: 'Finance',
    items: [
      { label: 'Payments', icon: CreditCard },
      { label: 'Loans', icon: Banknote },
    ],
  },
  {
    label: 'Commerce',
    items: [
      { label: 'Produce intake', icon: Inbox },
    ],
  },
  {
    label: 'Communications',
    items: [
      { label: 'SMS broadcasts', icon: MessageSquare },
    ],
  },
]

const STATS = [
  ['Total members', '248', '+12 this month'],
  ['Dues collected', 'GHS 29,760', '248 payments completed'],
  ['Credit eligible', '186', 'of 248 members assessed'],
  ['Avg trust score', '74.2', 'AgroCredit engine'],
]

const PAYMENTS = [
  ['Abena Mensah', '#1042', 'GHS 120', 'MoMo', 'Jul 18', 'Paid', 'bdg-green'],
  ['Kwame Asante', '#1038', 'GHS 120', 'USSD', 'Jul 17', 'Paid', 'bdg-green'],
  ['Ama Osei', '#1029', 'GHS 120', 'Card', 'Jul 16', 'Pending', 'bdg-amber'],
]

const TOP_SCORES = [
  ['Abena Mensah', 'Ashanti · Crop: Maize', 91, 'sh'],
  ['Yaw Boateng', 'Eastern · Crop: Cocoa', 88, 'sh'],
  ['Efua Darko', 'Volta · Crop: Cassava', 84, 'sh'],
  ['Kojo Mensah', 'Central · Crop: Rice', 79, 'sm'],
]

const REVIEW_QUEUE = [
  ['Ama Osei', '#1029 · Crop: Pepper', 52, 'Review manually before approval'],
  ['Kofi Adjei', '#1014 · Crop: Yam', 38, 'Defer credit and require dues recovery'],
]

export default function DashboardMock() {
  return (
    <div className="mock" aria-hidden="true">
      <div className="mock-bar">
        <span className="mock-bar-title">AgroOS Dashboard</span>
        <div className="mock-dots">
          <div className="mock-dot" style={{ background: '#FF5F57' }} />
          <div className="mock-dot" style={{ background: '#FFBD2E' }} />
          <div className="mock-dot" style={{ background: '#28C840' }} />
        </div>
      </div>

      <div className="mock-body">
        <aside className="mock-side">
          <div className="mock-side-head">
            <div className="mock-side-brand">
              <div className="mock-side-mark">
                <Sprout size={12} aria-hidden="true" />
              </div>
              <div className="mock-side-title">AgroOS</div>
            </div>
            <div className="mock-side-sub">
              <span className="mock-side-sub-label">Cooperative</span>
              <span className="mock-side-sub-name">Ashanti Growers Union</span>
            </div>
          </div>

          <nav className="mock-nav">
            {NAV_GROUPS.map((group) => (
              <div className="mock-nav-group" key={group.label}>
                <div className="mock-nav-lbl">{group.label}</div>
                {group.items.map(({ label, icon: Icon, active }) => (
                  <div key={label} className={`mock-nav-item${active ? ' on' : ''}`}>
                    <Icon size={11} aria-hidden="true" />
                    <span>{label}</span>
                  </div>
                ))}
              </div>
            ))}
          </nav>
        </aside>

        <div className="mock-main">
          <div className="mock-topbar">
            <div className="mock-topbar-heading">
              <span className="mock-page-title serif">Overview</span>
              <span className="mock-last-updated">Updated 09:42</span>
            </div>
            <div className="mock-refresh">
              <RefreshCw size={11} aria-hidden="true" />
              <span>Refresh</span>
            </div>
          </div>

          <div className="mock-content">
            <div className="mock-stats">
              {STATS.map(([lbl, val, sub]) => (
                <div key={lbl} className="mock-stat">
                  <div className="mock-stat-l">{lbl}</div>
                  <div className="mock-stat-v serif">{val}</div>
                  <div className="mock-stat-s">{sub}</div>
                </div>
              ))}
            </div>

            <div className="mock-grid">
              <div className="mock-card">
                <div className="mock-card-head">
                  <span className="mock-card-title serif">Recent payments</span>
                  <span className="mock-card-action">View payments</span>
                </div>
                <div className="mock-th">
                  {['Member', 'Amount', 'Method', 'Date', 'Status'].map((h) => (
                    <span key={h} className="mock-tl">{h}</span>
                  ))}
                </div>
                {PAYMENTS.map(([name, id, amt, method, date, status, cls]) => (
                  <div key={name} className="mock-tr">
                    <div>
                      <div className="mock-tr-n">{name}</div>
                      <div className="mock-tr-id">{id}</div>
                    </div>
                    <span className="mock-tr-v">{amt}</span>
                    <span className="mock-tr-m">{method}</span>
                    <span className="mock-tr-m">{date}</span>
                    <span className={`bdg ${cls}`}>{status}</span>
                  </div>
                ))}
              </div>

              <div className="mock-card">
                <div className="mock-card-head">
                  <span className="mock-card-title serif">Top credit scores</span>
                  <span className="mock-card-action">View scores</span>
                </div>
                {TOP_SCORES.map(([name, region, score, tier]) => (
                  <div key={name} className="mock-score-item">
                    <div>
                      <div className="mock-tr-n">{name}</div>
                      <div className="mock-tr-id">{region}</div>
                    </div>
                    <span className={`score-bdg ${tier}`}>{score}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="mock-card mock-review">
              <div className="mock-card-head">
                <span className="mock-card-title serif">Credit review queue</span>
                <span className="mock-card-action">2 need attention</span>
              </div>
              <div className="mock-review-grid">
                {REVIEW_QUEUE.map(([name, meta, score, rec]) => (
                  <div key={name} className="mock-review-card">
                    <div className="mock-review-top">
                      <div>
                        <div className="mock-tr-n">{name}</div>
                        <div className="mock-tr-id">{meta}</div>
                      </div>
                      <span className={`score-bdg ${score < 40 ? 'sl' : 'sm'}`}>{score}</span>
                    </div>
                    <div className="mock-review-rec">{rec}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
