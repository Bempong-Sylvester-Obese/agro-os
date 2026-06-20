// src/components/dashboard/Members.jsx
import { MEMBERS } from '../../data/payments'

const DUE_CLS = { Paid: 'bdg-green', Pending: 'bdg-amber', Overdue: 'bdg-red' }

export default function Members() {
  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div className="search-wrap">
          🔍
          <input placeholder="Search members..." />
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button style={{ background: 'none', border: '1px solid var(--border)', borderRadius: 7, fontSize: 12, padding: '7px 14px', cursor: 'pointer', fontFamily: "'DM Sans',sans-serif" }}>
            Filter
          </button>
          <button className="btn-nav" style={{ fontSize: 12, padding: '7px 14px' }}>+ Add member</button>
        </div>
      </div>

      <div className="admin-card">
        <div className="mt-head">
          {['Member','Phone','Region','Dues','Score',''].map(h => (
            <span key={h} className="pt-lbl">{h}</span>
          ))}
        </div>
        {MEMBERS.map(([name, id, phone, region, dues, score, tier]) => (
          <div key={id} className="mt-row">
            <div>
              <div className="pt-name">{name}</div>
              <div className="pt-id">{id}</div>
            </div>
            <span className="pt-m" style={{ fontSize: 11 }}>{phone}</span>
            <span className="pt-m">{region}</span>
            <span className={`bdg ${DUE_CLS[dues]}`}>{dues}</span>
            <span className={`score-bdg ${tier}`}>{score}</span>
            <span className="admin-card-action" style={{ fontSize: 11 }}>View →</span>
          </div>
        ))}
      </div>
    </>
  )
}
