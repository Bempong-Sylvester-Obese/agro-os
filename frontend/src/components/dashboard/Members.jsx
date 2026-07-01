// src/components/dashboard/Members.jsx
import { useState } from 'react'
import { DB_FARMERS_FALLBACK } from '../../api/farmers'
import { FARMER_ASSESSMENTS } from '../../data/payments'
import { findFarmerByName, formatTrustScore, scoreTier } from '../../utils/scores'

const STATUS_CLS = {
  active: 'bdg-green',
  inactive: 'bdg-amber',
  suspended: 'bdg-red',
}

export default function Members({ dbFarmers, agroAi, onAddMember }) {
  const [query, setQuery] = useState('')
  const farmers = dbFarmers?.farmers || DB_FARMERS_FALLBACK
  const agroAiFarmers = agroAi?.farmers || FARMER_ASSESSMENTS

  const filtered = farmers.filter((farmer) => {
    const haystack = [
      farmer.name,
      farmer.phone,
      farmer.location,
      String(farmer.id),
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()

    return haystack.includes(query.toLowerCase())
  })

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div className="search-wrap">
          🔍
          <input
            placeholder="Search members..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
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

      <div className="info-banner" style={{ marginBottom: 20 }}>
        <strong>Trust Score</strong> comes from verified cooperative records and updates after payment webhooks.
        <strong> Agro-AI credit</strong> is a separate ML assessment for loan decisions.
      </div>

      <div className="admin-card">
        <div className="mt-head">
          {['Member', 'Phone', 'Region', 'Status', 'Trust Score', 'Agro-AI', 'Review'].map((h) => (
            <span key={h} className="pt-lbl">{h}</span>
          ))}
        </div>
        {filtered.length === 0 && (
          <div style={{ padding: '28px 22px', textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>
            No members match your search.
          </div>
        )}
        {filtered.map((farmer) => {
          const agroAiMatch = findFarmerByName(agroAiFarmers, farmer.name)

          return (
            <div key={farmer.id} className="mt-row">
              <div>
                <div className="pt-name">{farmer.name}</div>
                <div className="pt-id">#{farmer.id}{farmer.crop_type ? ` · ${farmer.crop_type}` : ''}</div>
              </div>
              <span className="pt-m" style={{ fontSize: 11 }}>{farmer.phone}</span>
              <span className="pt-m">{farmer.location || '—'}</span>
              <span className={`bdg ${STATUS_CLS[farmer.membership_status] || 'bdg-amber'}`}>
                {farmer.membership_status}
              </span>
              <span className={`score-bdg ${scoreTier(farmer.trust_score)}`} title="Rules-based Trust Score">
                {formatTrustScore(farmer.trust_score)}
              </span>
              <span className={`score-bdg ${scoreTier(agroAiMatch?.score)}`} title="Agro-AI credit score">
                {agroAiMatch ? agroAiMatch.score : '—'}
              </span>
              <span className="admin-card-action" style={{ fontSize: 11 }}>
                {agroAiMatch ? (agroAiMatch.eligible ? 'Eligible' : 'Review') : '—'}
              </span>
            </div>
          )
        })}
      </div>
    </>
  )
}
