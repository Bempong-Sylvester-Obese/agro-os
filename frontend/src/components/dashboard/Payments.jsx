// src/components/dashboard/Payments.jsx
import { useState } from 'react'
import { Plus, X, Loader2 } from 'lucide-react'
import { collectDues, verifyDuesCollect } from '../../api/transactions'
import { TableSectionSkeleton } from './DashboardSkeleton'
import { useModal } from '../../hooks/useModal'

function fmtGHS(amount) {
  return `GHS ${Number(amount).toLocaleString('en-GH', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

// ── Collect Dues Modal ────────────────────────────────────────────────────────
function CollectDuesModal({ farmers, onClose, onSuccess }) {
  const { onBackdropClick, dialogProps } = useModal(onClose)
  const [form, setForm] = useState({ farmerId: '', amount: '', channel: '13' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [msg, setMsg] = useState(null)
  const [otpRequired, setOtpRequired] = useState(false)
  const [otpCode, setOtpCode] = useState('')
  const [externalRef, setExternalRef] = useState(null)
  const [transactionId, setTransactionId] = useState(null)

  const activeFarmers = farmers.filter(f => f.membership_status === 'active')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.farmerId || !form.amount) {
      setError('Please select a member and enter an amount.')
      return
    }
    
    setLoading(true)
    setError(null)
    setMsg(null)

    try {
      if (!otpRequired) {
        const res = await collectDues(form.farmerId, form.amount, form.channel, 'Cooperative dues')
        if (res.verification_required) {
          setOtpRequired(true)
          setExternalRef(res.moolre_reference)
          setTransactionId(res.transaction_id)
          setMsg('Moolre sent an SMS with an OTP to the member. Please enter it below.')
        } else if (res.status === 'pending') {
          setMsg('Payment initiated. Waiting for member to approve on their phone.')
          setTimeout(() => onSuccess(), 3000)
        } else {
          setError(res.message || 'Payment failed to initiate. Please try again.')
        }
      } else {
        if (!otpCode) {
          setError('Please enter the OTP.')
          setLoading(false)
          return
        }
        if (!transactionId) {
          setError('Missing payment session. Please start the payment again.')
          setLoading(false)
          return
        }
        const res = await verifyDuesCollect(transactionId, otpCode)
        if (res.status === 'pending') {
          setMsg('OTP verified! Waiting for member to approve on their phone.')
          setTimeout(() => onSuccess(), 3000)
        } else {
          setError('Verification failed. ' + res.message)
        }
      }
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
            <div className="serif" style={{ fontWeight: 700, fontSize: 19 }}>Collect Dues</div>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>Send a USSD payment prompt</div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)' }}><X size={20} /></button>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: '24px 28px' }}>
          {error && <div style={{ padding: 12, background: '#FEF2F2', color: '#991B1B', borderRadius: 8, fontSize: 13, marginBottom: 16 }}>{error}</div>}
          {msg && <div style={{ padding: 12, background: 'var(--sage)', color: 'var(--g)', borderRadius: 8, fontSize: 13, marginBottom: 16, fontWeight: 500 }}>{msg}</div>}
          
          {!otpRequired ? (
            <>
              <div style={{ marginBottom: 16 }}>
                <label style={{ fontSize: 13, fontWeight: 600 }}>Member</label>
                {activeFarmers.length === 0 ? (
                  <div style={{ marginTop: 6, padding: 12, background: 'var(--sage)', color: 'var(--g)', borderRadius: 8, fontSize: 13 }}>
                    No active members available. Add members before collecting dues.
                  </div>
                ) : (
                  <select style={input} value={form.farmerId} onChange={e => setForm({...form, farmerId: e.target.value})} required disabled={loading || msg}>
                    <option value="">Select a member...</option>
                    {activeFarmers.map(f => <option key={f.id} value={f.id}>{f.name} ({f.phone})</option>)}
                  </select>
                )}
              </div>

              <div style={{ marginBottom: 16 }}>
                <label style={{ fontSize: 13, fontWeight: 600 }}>Amount (GHS)</label>
                <input style={input} type="number" min="1" step="0.5" value={form.amount} onChange={e => setForm({...form, amount: e.target.value})} placeholder="e.g. 50" required disabled={loading || msg}/>
              </div>

              <div style={{ marginBottom: 24 }}>
                <label style={{ fontSize: 13, fontWeight: 600 }}>Network Channel</label>
                <select style={input} value={form.channel} onChange={e => setForm({...form, channel: e.target.value})} disabled={loading || msg}>
                  <option value="13">MTN Ghana</option>
                  <option value="6">Telecel</option>
                  <option value="7">AT</option>
                </select>
              </div>

              <button type="submit" className="btn-lg" disabled={loading || msg || activeFarmers.length === 0} style={{ width: '100%', padding: 12, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 8 }}>
                {loading ? <><Loader2 size={16} className="spin" /> Processing...</> : msg ? 'Prompt Sent ✓' : 'Send Payment Prompt'}
              </button>
            </>
          ) : (
            <>
              <div style={{ marginBottom: 24 }}>
                <label style={{ fontSize: 13, fontWeight: 600 }}>Enter SMS OTP</label>
                <input 
                  style={{...input, fontSize: 18, letterSpacing: 4, textAlign: 'center'}} 
                  type="text" 
                  value={otpCode} 
                  onChange={e => setOtpCode(e.target.value)} 
                  placeholder="123456" 
                  required 
                  disabled={loading || msg && msg.includes('verified')}
                  autoFocus
                />
              </div>
              <button type="submit" className="btn-lg" disabled={loading || msg && msg.includes('verified')} style={{ width: '100%', padding: 12, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 8 }}>
                {loading ? <><Loader2 size={16} className="spin" /> Verifying...</> : (msg && msg.includes('verified')) ? 'Verified ✓' : 'Submit OTP'}
              </button>
            </>
          )}
        </form>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────────────
export default function Payments({ farmers = [], transactions = [], loading, onRefresh }) {
  const [showModal, setShowModal] = useState(false)

  if (loading) return <TableSectionSkeleton statCount={3} rows={6} columns={5} />

  const completed = transactions.filter(t => t.status === 'completed')
  const totalCollected = completed.reduce((s, t) => s + t.amount, 0)

  const ussdChannels = ['13', '6', '7']
  const ussdAmount = completed.filter(t => ussdChannels.includes(t.channel)).reduce((s, t) => s + t.amount, 0)
  const momoAmount = completed.filter(t => !ussdChannels.includes(t.channel) && t.channel).reduce((s, t) => s + t.amount, 0)

  const ussdPct = totalCollected > 0 ? Math.round((ussdAmount / totalCollected) * 100) : 0
  const momoPct = totalCollected > 0 ? Math.round((momoAmount / totalCollected) * 100) : 0

  const sorted = [...transactions].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))

  return (
    <>
      {showModal && (
        <CollectDuesModal 
          farmers={farmers} 
          onClose={() => setShowModal(false)} 
          onSuccess={() => { setShowModal(false); if (onRefresh) onRefresh(); }} 
        />
      )}

      {/* ── Toolbar ── */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 20 }}>
        <button className="btn-nav" onClick={() => setShowModal(true)} style={{ fontSize: 13, padding: '8px 16px', display: 'flex', alignItems: 'center', gap: 6, background: 'var(--text)', color: '#fff' }}>
          <Plus size={15} /> Collect Dues
        </button>
      </div>

      <div className="pay-stats">
        {[
          ['Total collected', totalCollected > 0 ? fmtGHS(totalCollected) : '—', `${completed.length} completed payment${completed.length !== 1 ? 's' : ''}`],
          ['Via MoMo / card', momoAmount > 0 ? fmtGHS(momoAmount) : '—', momoPct > 0 ? `${momoPct}% of total` : 'No card payments yet'],
          ['Via USSD', ussdAmount > 0 ? fmtGHS(ussdAmount) : '—', ussdPct > 0 ? `${ussdPct}% of total` : 'No USSD payments yet'],
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
          <span className="admin-card-action">{transactions.length} record{transactions.length !== 1 ? 's' : ''}</span>
        </div>

        {sorted.length === 0 ? (
          <div style={{ padding: '32px 20px', color: 'var(--muted)', fontSize: 14 }}>
            No transactions recorded yet. Click "Collect Dues" to initiate a MoMo push to a member.
          </div>
        ) : (
          <>
            <div className="pay-head">
              {['Member', 'Amount', 'Method', 'Date', 'Status'].map(h => <span key={h} className="pt-lbl">{h}</span>)}
            </div>
            {sorted.map(tx => {
              const farmer = farmers.find(f => f.id === tx.farmer_id)
              const name = farmer ? farmer.name : `Farmer #${tx.farmer_id}`
              const method = ussdChannels.includes(tx.channel) ? 'USSD' : (tx.channel || 'Manual')
              const date = new Date(tx.created_at).toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })
              let cls = 'bdg-amber', label = 'Pending'
              if (tx.status === 'completed') { cls = 'bdg-green'; label = 'Paid' }
              if (tx.status === 'failed') { cls = 'bdg-red'; label = 'Failed' }
              return (
                <div key={tx.id} className="pay-row">
                  <div><div className="pt-name">{name}</div><div className="pt-id">#{tx.id}</div></div>
                  <span className="pt-v">{fmtGHS(tx.amount)}</span>
                  <span className="pt-m">{method}</span>
                  <span className="pt-m">{date}</span>
                  <span className={`bdg ${cls}`}>{label}</span>
                </div>
              )
            })}
          </>
        )}
      </div>
    </>
  )
}
