// src/components/dashboard/Loans.jsx
import { useState } from 'react'
import { Plus, X, Loader2, Check, XCircle, Send } from 'lucide-react'
import { createLoan, approveLoan, rejectLoan, disburseLoan } from '../../api/loans'
import { TableSectionSkeleton } from './DashboardSkeleton'
import { useModal } from '../../hooks/useModal'

function fmtGHS(amount) {
  return `GHS ${Number(amount).toLocaleString('en-GH', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

// ── Log Loan Request Modal ──────────────────────────────────────────────────────
function RequestLoanModal({ farmers, onClose, onSuccess }) {
  const { onBackdropClick, dialogProps } = useModal(onClose)
  const [form, setForm] = useState({ farmerId: '', amount: '', purpose: '', repaymentDate: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
  const activeFarmers = farmers.filter(f => f.membership_status === 'active')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.farmerId || !form.amount || !form.purpose || !form.repaymentDate) {
      setError('Please fill in all fields.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      await createLoan(form.farmerId, form.amount, form.purpose, form.repaymentDate)
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
            <div className="serif" style={{ fontWeight: 700, fontSize: 19 }}>Log Loan Request</div>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>Log a new input or cash loan request from a member</div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)' }}><X size={20} /></button>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: '24px 28px' }}>
          {error && <div style={{ padding: 12, background: '#FEF2F2', color: '#991B1B', borderRadius: 8, fontSize: 13, marginBottom: 16 }}>{error}</div>}
          
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 13, fontWeight: 600 }}>Member</label>
            <select style={input} value={form.farmerId} onChange={e => setForm({...form, farmerId: e.target.value})} required disabled={loading}>
              <option value="">Select a member...</option>
              {activeFarmers.map(f => <option key={f.id} value={f.id}>{f.name} ({f.phone})</option>)}
            </select>
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 13, fontWeight: 600 }}>Amount (GHS)</label>
            <input style={input} type="number" min="1" step="0.5" value={form.amount} onChange={e => setForm({...form, amount: e.target.value})} placeholder="e.g. 500" required disabled={loading}/>
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 13, fontWeight: 600 }}>Purpose</label>
            <input style={input} type="text" value={form.purpose} onChange={e => setForm({...form, purpose: e.target.value})} placeholder="e.g. Fertilizer, Seeds" required disabled={loading}/>
          </div>

          <div style={{ marginBottom: 24 }}>
            <label style={{ fontSize: 13, fontWeight: 600 }}>Expected Repayment Date</label>
            <input style={input} type="date" value={form.repaymentDate} onChange={e => setForm({...form, repaymentDate: e.target.value})} required disabled={loading}/>
          </div>

          <button type="submit" className="btn-lg" disabled={loading} style={{ width: '100%', padding: 12, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 8 }}>
            {loading ? <><Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> Submitting...</> : 'Log Request'}
          </button>
        </form>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────────────
export default function Loans({ farmers = [], loans = [], loading, onRefresh }) {
  const [showModal, setShowModal] = useState(false)
  const [processing, setProcessing] = useState(null) // ID of loan being processed
  const [actionError, setActionError] = useState(null)

  if (loading) {
    return (
      <TableSectionSkeleton
        statCount={3}
        rows={6}
        columns={6}
        gridStyle={{ gridTemplateColumns: '2fr 1fr 1fr 1fr 100px 140px' }}
      />
    )
  }

  const disbursed = loans.filter(l => l.status === 'disbursed')
  const requested = loans.filter(l => l.status === 'requested')
  const totalDisbursedAmount = disbursed.reduce((s, l) => s + l.amount, 0)
  const totalRequestedAmount = requested.reduce((s, l) => s + l.amount, 0)

  const sorted = [...loans].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))

  const handleAction = async (loanId, action) => {
    setProcessing(loanId)
    setActionError(null)
    try {
      if (action === 'approve') await approveLoan(loanId)
      if (action === 'reject') await rejectLoan(loanId)
      if (action === 'disburse') await disburseLoan(loanId)
      if (onRefresh) onRefresh()
    } catch (err) {
      setActionError(err.message)
    } finally {
      setProcessing(null)
    }
  }

  return (
    <>
      {showModal && (
        <RequestLoanModal 
          farmers={farmers} 
          onClose={() => setShowModal(false)} 
          onSuccess={() => { setShowModal(false); if (onRefresh) onRefresh(); }} 
        />
      )}

      {/* ── Toolbar ── */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 20 }}>
        <button className="btn-nav" onClick={() => setShowModal(true)} style={{ fontSize: 13, padding: '8px 16px', display: 'flex', alignItems: 'center', gap: 6, background: 'var(--text)', color: '#fff' }}>
          <Plus size={15} /> Log Loan Request
        </button>
      </div>

      {actionError && (
        <div style={{ padding: 12, background: '#FEF2F2', color: '#991B1B', borderRadius: 8, fontSize: 13, marginBottom: 16 }}>
          {actionError}
        </div>
      )}

      <div className="pay-stats">
        {[
          ['Total Disbursed', totalDisbursedAmount > 0 ? fmtGHS(totalDisbursedAmount) : '—', `${disbursed.length} active loan${disbursed.length !== 1 ? 's' : ''}`],
          ['Pending Requests', totalRequestedAmount > 0 ? fmtGHS(totalRequestedAmount) : '—', `${requested.length} awaiting approval`],
          ['Avg. Loan Size', disbursed.length > 0 ? fmtGHS(totalDisbursedAmount / disbursed.length) : '—', 'Based on active loans'],
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
          <span className="admin-card-title serif">Loan History</span>
          <span className="admin-card-action">{loans.length} record{loans.length !== 1 ? 's' : ''}</span>
        </div>

        {sorted.length === 0 ? (
          <div style={{ padding: '32px 20px', color: 'var(--muted)', fontSize: 14 }}>
            No loans recorded yet. Click "Log Loan Request" to log a new application.
          </div>
        ) : (
          <>
            {/* Using a custom grid similar to pay-head but accommodating actions */}
            <div className="pay-head" style={{ gridTemplateColumns: '2fr 1fr 1fr 1fr 100px 140px' }}>
              <span className="pt-lbl">Member</span>
              <span className="pt-lbl">Amount</span>
              <span className="pt-lbl">Purpose</span>
              <span className="pt-lbl">Repayment</span>
              <span className="pt-lbl">Status</span>
              <span className="pt-lbl" style={{ textAlign: 'right' }}>Action</span>
            </div>
            {sorted.map(loan => {
              const farmer = farmers.find(f => f.id === loan.farmer_id)
              const name = farmer ? farmer.name : `Farmer #${loan.farmer_id}`
              const repayDate = new Date(loan.repayment_date).toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })
              
              let cls = 'bdg-amber', label = loan.status
              if (['approved', 'disbursed', 'repaid'].includes(loan.status)) cls = 'bdg-green'
              if (loan.status === 'rejected') cls = 'bdg-red'

              return (
                <div key={loan.id} className="pay-row" style={{ gridTemplateColumns: '2fr 1fr 1fr 1fr 100px 140px', alignItems: 'center' }}>
                  <div><div className="pt-name">{name}</div><div className="pt-id">#{loan.id}</div></div>
                  <span className="pt-v">{fmtGHS(loan.amount)}</span>
                  <span className="pt-m" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{loan.purpose}</span>
                  <span className="pt-m">{repayDate}</span>
                  <span className={`bdg ${cls}`} style={{ textTransform: 'capitalize' }}>{label}</span>
                  <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                    {loan.status === 'requested' && (
                      <>
                        <button 
                          disabled={processing === loan.id}
                          onClick={() => handleAction(loan.id, 'approve')}
                          style={{ background: '#ecfdf5', color: '#047857', border: '1px solid #a7f3d0', borderRadius: 6, padding: '4px 8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, fontWeight: 600 }}
                        >
                          {processing === loan.id ? <Loader2 size={12} className="spin" /> : <Check size={12} />} Approve
                        </button>
                        <button 
                          disabled={processing === loan.id}
                          onClick={() => handleAction(loan.id, 'reject')}
                          style={{ background: '#FEF2F2', color: '#991B1B', border: '1px solid #fecaca', borderRadius: 6, padding: '4px 8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, fontWeight: 600 }}
                        >
                          <XCircle size={12} /> Reject
                        </button>
                      </>
                    )}
                    {loan.status === 'approved' && (
                      <button 
                        disabled={processing === loan.id}
                        onClick={() => handleAction(loan.id, 'disburse')}
                        style={{ background: 'var(--text)', color: '#fff', border: 'none', borderRadius: 6, padding: '4px 12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, fontWeight: 600 }}
                      >
                        {processing === loan.id ? <Loader2 size={12} className="spin" /> : <Send size={12} />} Disburse
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </>
        )}
      </div>
    </>
  )
}
