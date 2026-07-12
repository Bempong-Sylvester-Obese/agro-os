// src/components/dashboard/Production.jsx
import { useState } from 'react'
import { Plus, X, Loader2 } from 'lucide-react'
import { logProduction } from '../../api/production'
import { TableSectionSkeleton } from './DashboardSkeleton'
import { useModal } from '../../hooks/useModal'

function quantityKg(prod) {
  const value = prod.quantity_kg ?? prod.yield_amount
  return value == null || Number.isNaN(Number(value)) ? null : Number(value)
}

function expectedKg(prod) {
  const value = prod.expected_kg ?? prod.acreage
  return value == null || Number.isNaN(Number(value)) ? null : Number(value)
}

function formatKg(value) {
  return value == null ? '—' : value.toLocaleString()
}

function formatHarvestDate(prod) {
  if (!prod.harvest_date) return '—'
  const date = new Date(prod.harvest_date)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })
}

// ── Log Production Modal ────────────────────────────────────────────────────────
function LogProductionModal({ farmers, onClose, onSuccess }) {
  const { onBackdropClick, dialogProps, titleId, closeButtonProps } = useModal(onClose, { label: 'production dialog' })
  const [form, setForm] = useState({ farmerId: '', cropType: '', expectedKg: '', quantityKg: '', harvestDate: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
  const activeFarmers = farmers.filter(f => f.membership_status === 'active')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.farmerId || !form.cropType || !form.expectedKg || !form.quantityKg || !form.harvestDate) {
      setError('Please fill in all fields.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      await logProduction(form.farmerId, form.cropType, form.expectedKg, form.quantityKg, form.harvestDate)
      onSuccess()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const input = {
    width: '100%', padding: '10px 12px', border: '1.5px solid var(--border)',
    borderRadius: 8, fontSize: 14, fontFamily: "'DM Sans', sans-serif",
    outline: 'none', background: '#fff', color: 'var(--text)', boxSizing: 'border-box',
    marginTop: 6
  }

  return (
    <div
      onClick={onBackdropClick}
      style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.48)',
      backdropFilter: 'blur(4px)', zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
    }}>
      <div
        {...dialogProps}
        style={{
        background: '#fff', borderRadius: 16, width: '100%', maxWidth: 400,
        boxShadow: '0 32px 80px rgba(0,0,0,0.22)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '24px 28px 20px', borderBottom: '1px solid var(--border)' }}>
          <div>
            <div id={titleId} className="serif" style={{ fontWeight: 700, fontSize: 19 }}>Log Production</div>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>Record a member's harvest yield</div>
          </div>
          <button {...closeButtonProps} onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)' }}><X size={20} /></button>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: '24px 28px' }}>
          {error && <div style={{ padding: 12, background: '#FEF2F2', color: '#991B1B', borderRadius: 8, fontSize: 13, marginBottom: 16 }}>{error}</div>}
          
          <div style={{ marginBottom: 16 }}>
            <label htmlFor="production-member" style={{ fontSize: 13, fontWeight: 600 }}>Member</label>
            <select id="production-member" style={input} value={form.farmerId} onChange={e => setForm({...form, farmerId: e.target.value})} required disabled={loading}>
              <option value="">Select a member...</option>
              {activeFarmers.map(f => <option key={f.id} value={f.id}>{f.name} ({f.phone})</option>)}
            </select>
          </div>

          <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
            <div style={{ flex: 1 }}>
              <label htmlFor="production-crop" style={{ fontSize: 13, fontWeight: 600 }}>Crop Type</label>
              <input id="production-crop" style={input} type="text" value={form.cropType} onChange={e => setForm({...form, cropType: e.target.value})} placeholder="e.g. Maize" required disabled={loading}/>
            </div>
            <div style={{ flex: 1 }}>
              <label htmlFor="production-expected" style={{ fontSize: 13, fontWeight: 600 }}>Expected yield (kg)</label>
              <input id="production-expected" style={input} type="number" min="0.1" step="0.1" value={form.expectedKg} onChange={e => setForm({...form, expectedKg: e.target.value})} placeholder="e.g. 600" required disabled={loading}/>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
            <div style={{ flex: 1 }}>
              <label htmlFor="production-quantity" style={{ fontSize: 13, fontWeight: 600 }}>Harvest quantity (kg)</label>
              <input id="production-quantity" style={input} type="number" min="1" step="1" value={form.quantityKg} onChange={e => setForm({...form, quantityKg: e.target.value})} placeholder="e.g. 500" required disabled={loading}/>
            </div>
            <div style={{ flex: 1 }}>
              <label htmlFor="production-date" style={{ fontSize: 13, fontWeight: 600 }}>Harvest Date</label>
              <input id="production-date" style={input} type="date" value={form.harvestDate} onChange={e => setForm({...form, harvestDate: e.target.value})} required disabled={loading}/>
            </div>
          </div>

          <button type="submit" className="btn-lg" disabled={loading} style={{ width: '100%', padding: 12, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 8 }}>
            {loading ? <><Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> Submitting...</> : 'Save Production Log'}
          </button>
        </form>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────────────
export default function Production({ farmers = [], productions = [], loading, onRefresh }) {
  const [showModal, setShowModal] = useState(false)

  if (loading) {
    return (
      <TableSectionSkeleton
        statCount={3}
        rows={6}
        columns={5}
        gridStyle={{ gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr' }}
      />
    )
  }

  const totalExpected = productions.reduce((sum, p) => sum + (expectedKg(p) ?? 0), 0)
  const totalYield = productions.reduce((sum, p) => sum + (quantityKg(p) ?? 0), 0)

  const crops = {}
  productions.forEach(p => {
    const qty = quantityKg(p)
    if (qty == null || !p.crop_type) return
    crops[p.crop_type] = (crops[p.crop_type] || 0) + qty
  })
  const topCrop = Object.keys(crops).sort((a, b) => crops[b] - crops[a])[0]

  const sorted = [...productions].sort((a, b) => {
    const aTime = a.harvest_date ? new Date(a.harvest_date).getTime() : 0
    const bTime = b.harvest_date ? new Date(b.harvest_date).getTime() : 0
    return (Number.isNaN(bTime) ? 0 : bTime) - (Number.isNaN(aTime) ? 0 : aTime)
  })

  return (
    <>
      {showModal && (
        <LogProductionModal 
          farmers={farmers} 
          onClose={() => setShowModal(false)} 
          onSuccess={() => { setShowModal(false); if (onRefresh) onRefresh(); }} 
        />
      )}

      {/* ── Toolbar ── */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 20 }}>
        <button className="btn-nav" onClick={() => setShowModal(true)} style={{ fontSize: 13, padding: '8px 16px', display: 'flex', alignItems: 'center', gap: 6, background: 'var(--text)', color: '#fff' }}>
          <Plus size={15} /> Log Production
        </button>
      </div>

      <div className="pay-stats">
        {[
          ['Total harvest (kg)', totalYield > 0 ? formatKg(totalYield) : '—', 'Across all harvest logs'],
          ['Total expected (kg)', totalExpected > 0 ? formatKg(totalExpected) : '—', 'Planned yield across members'],
          ['Top producing crop', topCrop || '—', topCrop ? `${formatKg(crops[topCrop])} kg logged` : 'No data yet'],
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
          <span className="admin-card-title serif">Production Logs</span>
          <span className="admin-card-action">{productions.length} record{productions.length !== 1 ? 's' : ''}</span>
        </div>

        {sorted.length === 0 ? (
          <div style={{ padding: '32px 20px', color: 'var(--muted)', fontSize: 14 }}>
            No production records found. Click "Log Production" to record a harvest.
          </div>
        ) : (
          <>
            <div className="pay-head" style={{ gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr' }}>
              <span className="pt-lbl">Member</span>
              <span className="pt-lbl">Crop Type</span>
              <span className="pt-lbl">Expected (kg)</span>
              <span className="pt-lbl">Harvest (kg)</span>
              <span className="pt-lbl">Harvest Date</span>
            </div>
            {sorted.map(prod => {
              const farmer = farmers.find(
                f => Number(f.id) === Number(prod.farmer_id)
              )
              const name = farmer ? farmer.name : `Farmer #${prod.farmer_id}`

              return (
                <div key={prod.id} className="pay-row" style={{ gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr', alignItems: 'center' }}>
                  <div><div className="pt-name">{name}</div><div className="pt-id">#{prod.id}</div></div>
                  <span className="pt-m">{prod.crop_type || '—'}</span>
                  <span className="pt-m">{formatKg(expectedKg(prod))}</span>
                  <span className="pt-v">{formatKg(quantityKg(prod))}</span>
                  <span className="pt-m">{formatHarvestDate(prod)}</span>
                </div>
              )
            })}
          </>
        )}
      </div>
    </>
  )
}
