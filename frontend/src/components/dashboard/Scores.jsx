// src/components/dashboard/Scores.jsx
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { fetchFarmerTrustScore, recalculateTrustScore } from '../../api/farmers'
import { exportDashboardReport } from '../../api/reports'
import { RefreshCw, Loader2 } from 'lucide-react'
import { ScoresSkeleton, Skeleton } from './DashboardSkeleton'
import { DashboardPagination, DashboardTableToolbar, useDashboardTable } from './DashboardTableTools'

const scoreTier = (score) => {
  if (score >= 82) return 'sh'
  if (score >= 60) return 'sm'
  return 'sl'
}

const pct = (value) =>
  value != null ? `${Math.round(value * 100)}%` : '—'

// Trust score factor weights match the backend TrustScoreService formula
const FACTOR_LABELS = [
  { key: 'payment_compliance',  label: 'Payment compliance',  weight: '40%' },
  { key: 'production_history',  label: 'Production history',  weight: '25%' },
  { key: 'loan_repayment',      label: 'Loan repayment',      weight: '20%' },
  { key: 'attendance',          label: 'Cooperative attendance', weight: '15%' },
]

function creditRecommendation(score) {
  if (score >= 82) return { band: 'Low risk',      rec: 'Approve full input credit' }
  if (score >= 68) return { band: 'Moderate risk', rec: 'Approve with standard monitoring' }
  if (score >= 55) return { band: 'Watchlist',     rec: 'Review manually before approval' }
  return              { band: 'High risk',      rec: 'Defer credit and require dues recovery' }
}

// ── Detail panel ─────────────────────────────────────────────────────────────
function ScoreDetail({ farmer }) {
  const [breakdown, setBreakdown] = useState(null)
  const [loadingBreakdown, setLoadingBreakdown] = useState(false)
  const [recalculating, setRecalculating] = useState(false)

  useEffect(() => {
    if (!farmer) return
    setBreakdown(null)
    // Only fetch breakdown if a score has been calculated — avoids a 404
    if (!farmer.trust_score || farmer.trust_score === 0) {
      setLoadingBreakdown(false)
      return
    }
    setLoadingBreakdown(true)
    fetchFarmerTrustScore(farmer.id)
      .then(data => { setBreakdown(data); setLoadingBreakdown(false) })
      .catch(() => setLoadingBreakdown(false))
  }, [farmer?.id, farmer?.trust_score])

  const handleRecalculate = async () => {
    setRecalculating(true)
    try {
      const updated = await recalculateTrustScore(farmer.id)
      if (updated) setBreakdown(updated)
    } catch {
      // keep existing breakdown; button re-enables in finally
    } finally {
      setRecalculating(false)
    }
  }

  if (!farmer) return null

  const score = farmer.trust_score ? Math.round(farmer.trust_score) : 0
  const eligible = score >= 68
  const { band, rec } = creditRecommendation(score)

  return (
    <div className="admin-card score-detail-card">
      {/* Hero */}
      <div className="score-detail-hero">
        <div>
          <div className="pt-id">#{farmer.id} · {farmer.location || 'Unknown location'}</div>
          <div className="score-detail-name serif">{farmer.name}</div>
          <div className="score-detail-sub">
            {farmer.crop_type || 'No crop type'} farmer
            {farmer.acreage ? ` · ${farmer.acreage} acres` : ''}
          </div>
        </div>
        <span className={`score-bdg score-bdg-lg ${scoreTier(score)}`}>{score || '—'}</span>
      </div>

      {/* Decision card */}
      <div className="decision-card">
        <div className="decision-label">{band}</div>
        <div className="decision-title serif">{rec}</div>
        <div className="decision-copy">
          {eligible
            ? `This member meets the credit threshold. Trust score: ${score}/100.`
            : `Trust score (${score}/100) is below the 68-point credit threshold.`}
        </div>
      </div>

      {/* Trust score breakdown */}
      {loadingBreakdown ? (
        <div className="feature-grid">
          {FACTOR_LABELS.map(({ key }) => (
            <div key={key} className="feature-pill">
              <Skeleton width="72%" height={11} radius={4} />
              <Skeleton width={28} height={14} radius={4} style={{ marginTop: 6 }} />
            </div>
          ))}
        </div>
      ) : breakdown ? (
        <div className="feature-grid">
          {FACTOR_LABELS.map(({ key, label, weight }) => (
            <div key={key} className="feature-pill">
              <span>{label} <span style={{ color: 'var(--muted)', fontSize: 10 }}>({weight})</span></span>
              <strong>{pct(breakdown[key])}</strong>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ padding: '12px 0', color: 'var(--muted)', fontSize: 13 }}>
          No trust score breakdown available yet. Record payments, production, and attendance data, then recalculate.
        </div>
      )}

      {/* Recalculate button */}
      <div style={{ marginTop: 16 }}>
        <button
          onClick={handleRecalculate}
          disabled={recalculating}
          style={{
            display: 'flex', alignItems: 'center', gap: 7,
            background: 'none', border: '1.5px solid var(--border)', borderRadius: 8,
            padding: '8px 14px', fontSize: 13, fontWeight: 600,
            fontFamily: "'DM Sans', sans-serif", cursor: 'pointer',
            color: recalculating ? 'var(--muted)' : 'var(--text)',
          }}
        >
          {recalculating
            ? <><Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} /> Recalculating…</>
            : <><RefreshCw size={13} /> Recalculate trust score</>}
        </button>
      </div>

      {breakdown && (
        <div className="reason-list" style={{ marginTop: 16 }}>
          <div className="pt-lbl">Score calculated</div>
          <div className="reason-item">
            {new Date(breakdown.calculated_at).toLocaleString('en-US', {
              month: 'short', day: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main Scores page ──────────────────────────────────────────────────────────
export default function Scores({ farmers = [], cooperativeId, loading }) {
  const [selectedId, setSelectedId] = useState(null)
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState('')

  // Default selection: highest scoring farmer
  const sorted = useMemo(
    () => [...farmers].sort((a, b) => b.trust_score - a.trust_score),
    [farmers],
  )
  const searchableText = useCallback(
    farmer => `${farmer.name} ${farmer.phone || ''} ${farmer.location || ''} ${farmer.crop_type || ''}`,
    [],
  )
  const statusValue = useCallback(farmer => farmer.trust_score >= 68 ? 'eligible' : 'review', [])
  const dateValue = useCallback(farmer => farmer.updated_at, [])
  const table = useDashboardTable({
    rows: sorted,
    searchableText,
    statusValue,
    dateValue,
  })
  const selectedFarmer = table.filteredRows.find(f => f.id === selectedId) || table.filteredRows[0] || null
  const handleExport = async () => {
    setExporting(true)
    setExportError('')
    try {
      await exportDashboardReport('scores', cooperativeId, table.exportFilters)
    } catch (error) {
      setExportError(error.message || 'Could not export scores. Please try again.')
    } finally {
      setExporting(false)
    }
  }

  if (loading) return <ScoresSkeleton />

  if (farmers.length === 0) {
    return (
      <div className="admin-card" style={{ padding: 56, textAlign: 'center' }}>
        <div className="serif" style={{ fontSize: 20, marginBottom: 8 }}>No members yet</div>
        <div style={{ color: 'var(--muted)', fontSize: 14 }}>
          Add members and record their payments, production, and attendance to generate trust scores.
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="info-banner">
        <strong>AgroCredit Trust Score</strong> — Calculated from real cooperative data: payment compliance (40%),
        production history (25%), loan repayment (20%), and attendance (15%). Threshold for credit eligibility: 68/100.
      </div>
      <DashboardTableToolbar
        label="Scores"
        table={table}
        statuses={[
          { value: 'eligible', label: 'Eligible' },
          { value: 'review', label: 'Review' },
        ]}
        onExport={handleExport}
        exporting={exporting}
        exportError={exportError}
      />

      <div className="score-layout">
        {/* ── Left: farmer list ── */}
        <div className="admin-card">
          <div className="admin-card-head">
            <span className="admin-card-title serif">Credit decision queue</span>
            <span className="admin-card-action">Real data</span>
          </div>
          <div className="table-scroll">
            <div className="sc-head">
              {['Member', 'Crop', 'Status', 'Score'].map(h => (
                <span key={h} className="pt-lbl">{h}</span>
              ))}
            </div>
            {table.pageRows.map(farmer => {
              const score = farmer.trust_score ? Math.round(farmer.trust_score) : 0
              const eligible = score >= 68
              const isSelected = farmer.id === (selectedFarmer?.id)
              return (
                <button
                  key={farmer.id}
                  className={`sc-row sc-row-btn${isSelected ? ' on' : ''}`}
                  onClick={() => setSelectedId(farmer.id)}
                >
                  <div>
                    <div className="pt-name">{farmer.name}</div>
                    <div className="pt-id">{farmer.location || '—'}</div>
                  </div>
                  <span className="pt-m" style={{ fontSize: 11 }}>{farmer.crop_type || '—'}</span>
                  <span className={`bdg ${eligible ? 'bdg-green' : 'bdg-amber'}`}>
                    {eligible ? 'Eligible' : 'Review'}
                  </span>
                  <span className={`score-bdg ${scoreTier(score)}`}>
                    {score || '—'}
                  </span>
                </button>
              )
            })}
            {table.filteredRows.length === 0 && (
              <div style={{ padding: '24px 20px', color: 'var(--muted)', fontSize: 14 }}>
                No scores match the current filters.
              </div>
            )}
          </div>
          <DashboardPagination label="Scores" table={table} />
        </div>

        {/* ── Right: detail panel ── */}
        {selectedFarmer && <ScoreDetail farmer={selectedFarmer} />}
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </>
  )
}
