// src/components/dashboard/Members.jsx
import { FARMER_ASSESSMENTS } from '../../data/payments'

const DUE_CLS = { Paid: 'bdg-green', Pending: 'bdg-amber', Overdue: 'bdg-red' }

const scoreTier = (score) => {
  if (score >= 82) return 'sh'
  if (score >= 60) return 'sm'
  return 'sl'
}

export default function Members({ farmers = FARMER_ASSESSMENTS, onAddMember }) {
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
          {onAddMember && (
            <button className="btn-nav" style={{ fontSize: 12, padding: '7px 14px' }} onClick={onAddMember}>
              + Add member
            </button>
          )}
        </div>
      </div>

      <div className="admin-card">
        <div className="mt-head">
          {['Member','Phone','Region','Dues','Agro-AI','Review'].map(h => (
            <span key={h} className="pt-lbl">{h}</span>
          ))}
        </div>
        {farmers.map((farmer) => (
          <div key={farmer.farmer_id} className="mt-row">
            <div>
              <div className="pt-name">{farmer.name}</div>
              <div className="pt-id">{farmer.farmer_id} · {farmer.crop}</div>
            </div>
            <span className="pt-m" style={{ fontSize: 11 }}>{farmer.phone}</span>
            <span className="pt-m">{farmer.region}</span>
            <span className={`bdg ${DUE_CLS[farmer.dues_status]}`}>{farmer.dues_status}</span>
            <span className={`score-bdg ${scoreTier(farmer.score)}`}>{farmer.score}</span>
            <span className="admin-card-action" style={{ fontSize: 11 }}>
              {farmer.eligible ? 'Eligible' : 'Review'}
            </span>
          </div>
        ))}
      </div>
    </>
  )
}
