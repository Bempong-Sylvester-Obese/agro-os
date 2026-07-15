// src/components/dashboard/Loans.jsx
import React, { useCallback, useEffect, useState } from 'react'
import { Plus, X, Loader2, Check, XCircle, Send, RefreshCw, Banknote, Ban } from 'lucide-react'
import {
  createLoan,
  approveLoan,
  rejectLoan,
  disburseLoan,
  cancelLoan,
  fetchDisbursementStatus,
  repayLoan,
  verifyLoanRepayment,
  RepaymentVerificationRequiredError,
} from '../../api/loans'
import { TableSectionSkeleton } from './DashboardSkeleton'
import { useModal } from '../../hooks/useModal'
import { ModalPresence } from '../Motion'
import { exportDashboardReport } from '../../api/reports'
import { DashboardPagination, DashboardTableToolbar, useDashboardTable } from './DashboardTableTools'

function fmtGHS(amount) {
  return `GHS ${Number(amount).toLocaleString('en-GH', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

function fmtRepaymentDate(raw) {
  if (!raw) return '—'
  const normalized = typeof raw === 'string' && raw.length === 10 ? `${raw}T12:00:00` : raw
  const d = new Date(normalized)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })
}

// ── Log Loan Request Modal ──────────────────────────────────────────────────────
function RequestLoanModal({ farmers, onClose, onSuccess }) {
  const { onBackdropClick, dialogProps, titleId, closeButtonProps } = useModal(onClose, { label: 'loan request dialog' })
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
      className="dashboard-modal-overlay"
      onClick={onBackdropClick}
      style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.48)',
      backdropFilter: 'blur(4px)', zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
    }}>
      <div
        className="dashboard-modal"
        {...dialogProps}
        style={{
        background: '#fff', borderRadius: 16, width: '100%', maxWidth: 400,
        boxShadow: '0 32px 80px rgba(0,0,0,0.22)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '24px 28px 20px', borderBottom: '1px solid var(--border)' }}>
          <div>
            <div id={titleId} className="serif" style={{ fontWeight: 700, fontSize: 19 }}>Log Loan Request</div>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>Log a new input or cash loan request from a member</div>
          </div>
          <button {...closeButtonProps} onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)' }}><X size={20} /></button>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: '24px 28px' }}>
          {error && <div style={{ padding: 12, background: '#FEF2F2', color: '#991B1B', borderRadius: 8, fontSize: 13, marginBottom: 16 }}>{error}</div>}
          
          <div style={{ marginBottom: 16 }}>
            <label htmlFor="loan-member" style={{ fontSize: 13, fontWeight: 600 }}>Member</label>
            <select id="loan-member" style={input} value={form.farmerId} onChange={e => setForm({...form, farmerId: e.target.value})} required disabled={loading}>
              <option value="">Select a member...</option>
              {activeFarmers.map(f => <option key={f.id} value={f.id}>{f.name} ({f.phone})</option>)}
            </select>
          </div>

          <div style={{ marginBottom: 16 }}>
            <label htmlFor="loan-amount" style={{ fontSize: 13, fontWeight: 600 }}>Amount (GHS)</label>
            <input id="loan-amount" style={input} type="number" min="1" step="0.5" value={form.amount} onChange={e => setForm({...form, amount: e.target.value})} placeholder="e.g. 500" required disabled={loading}/>
          </div>

          <div style={{ marginBottom: 16 }}>
            <label htmlFor="loan-purpose" style={{ fontSize: 13, fontWeight: 600 }}>Purpose</label>
            <input id="loan-purpose" style={input} type="text" value={form.purpose} onChange={e => setForm({...form, purpose: e.target.value})} placeholder="e.g. Fertilizer, Seeds" required disabled={loading}/>
          </div>

          <div style={{ marginBottom: 24 }}>
            <label htmlFor="loan-repayment-date" style={{ fontSize: 13, fontWeight: 600 }}>Expected Repayment Date</label>
            <input id="loan-repayment-date" style={input} type="date" value={form.repaymentDate} onChange={e => setForm({...form, repaymentDate: e.target.value})} required disabled={loading}/>
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

const ACTION_COPY = {
  approve: ['Approve loan?', 'This loan will become eligible for disbursement.', 'Approve loan'],
  reject: ['Reject loan?', 'This action closes the request and cannot be undone.', 'Reject loan'],
  cancel: ['Cancel loan?', 'Provide a reason for cancelling this loan.', 'Cancel loan'],
  disburse: ['Disburse loan?', 'This starts a payout to the member. Confirm the amount and member before continuing.', 'Start disbursement'],
  retry: ['Retry payout?', 'This retries the failed payout using the existing loan details.', 'Retry payout'],
  repay: ['Collect repayment?', 'This starts repayment collection. The member may need to provide an OTP.', 'Collect repayment'],
}

const actionButtonStyle = {
  border: 0,
  borderRadius: 8,
  padding: '9px 14px',
  cursor: 'pointer',
  fontSize: 13,
  fontWeight: 700,
}

function ConfirmationModal({ action, processing, error, onClose, onConfirm }) {
  const { onBackdropClick, dialogProps, titleId, closeButtonProps } = useModal(onClose, {
    closeOnBackdrop: !processing,
    label: `${action.type} loan dialog`,
  })
  const [reason, setReason] = useState('')
  const [validationError, setValidationError] = useState('')
  const [title, description, confirmLabel] = ACTION_COPY[action.type]
  const destructive = ['reject', 'cancel'].includes(action.type)

  const submit = (event) => {
    event.preventDefault()
    if (action.type === 'cancel' && !reason.trim()) {
      setValidationError('Enter a cancellation reason.')
      return
    }
    onConfirm(reason)
  }

  return (
    <div className="dashboard-modal-overlay" onClick={onBackdropClick} style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.48)', backdropFilter: 'blur(4px)',
      zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
    }}>
      <form className="dashboard-modal" {...dialogProps} onSubmit={submit} style={{
        background: '#fff', borderRadius: 16, width: '100%', maxWidth: 430,
        boxShadow: '0 32px 80px rgba(0,0,0,0.22)', padding: 24,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
          <div>
            <h2 id={titleId} className="serif" style={{ fontSize: 20, margin: 0 }}>{title}</h2>
            <p style={{ color: 'var(--muted)', fontSize: 13, lineHeight: 1.5, margin: '8px 0 0' }}>{description}</p>
          </div>
          <button {...closeButtonProps} disabled={processing} onClick={onClose} style={{ background: 'none', border: 0, color: 'var(--muted)', cursor: 'pointer', height: 28 }}>
            <X size={20} />
          </button>
        </div>
        <div style={{ background: 'var(--sage)', borderRadius: 10, padding: 12, marginTop: 18, fontSize: 13 }}>
          <strong>Loan #{action.loan.id}</strong> · {fmtGHS(action.loan.amount)}
        </div>
        {action.type === 'cancel' && (
          <div style={{ marginTop: 16 }}>
            <label htmlFor="loan-cancel-reason" style={{ fontSize: 13, fontWeight: 700 }}>Cancellation reason</label>
            <textarea
              id="loan-cancel-reason"
              value={reason}
              onChange={(event) => { setReason(event.target.value); setValidationError('') }}
              disabled={processing}
              rows={3}
              style={{ display: 'block', width: '100%', boxSizing: 'border-box', marginTop: 6, padding: 10, border: '1px solid var(--border)', borderRadius: 8, resize: 'vertical', font: 'inherit' }}
            />
          </div>
        )}
        {(validationError || error) && <div role="alert" style={{ color: '#991B1B', fontSize: 13, marginTop: 14 }}>{validationError || error}</div>}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 22 }}>
          <button type="button" disabled={processing} onClick={onClose} style={{ ...actionButtonStyle, background: '#fff', border: '1px solid var(--border)', color: 'var(--text)' }}>Go back</button>
          <button type="submit" disabled={processing} style={{ ...actionButtonStyle, background: destructive ? '#991B1B' : 'var(--text)', color: '#fff' }}>
            {processing ? 'Working…' : confirmLabel}
          </button>
        </div>
      </form>
    </div>
  )
}

function RepaymentOtpModal({ repayment, processing, error, onClose, onVerify }) {
  const { onBackdropClick, dialogProps, titleId, closeButtonProps } = useModal(onClose, {
    closeOnBackdrop: !processing,
    label: 'repayment verification dialog',
  })
  const [otpCode, setOtpCode] = useState('')

  return (
    <div className="dashboard-modal-overlay" onClick={onBackdropClick} style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.48)', backdropFilter: 'blur(4px)',
      zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
    }}>
      <form className="dashboard-modal" {...dialogProps} onSubmit={(event) => { event.preventDefault(); onVerify(otpCode) }} style={{
        background: '#fff', borderRadius: 16, width: '100%', maxWidth: 400,
        boxShadow: '0 32px 80px rgba(0,0,0,0.22)', padding: 24,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
          <div>
            <h2 id={titleId} className="serif" style={{ fontSize: 20, margin: 0 }}>Verify repayment</h2>
            <p style={{ color: 'var(--muted)', fontSize: 13, lineHeight: 1.5, margin: '8px 0 0' }}>{repayment.message}</p>
          </div>
          <button {...closeButtonProps} disabled={processing} onClick={onClose} style={{ background: 'none', border: 0, color: 'var(--muted)', cursor: 'pointer', height: 28 }}><X size={20} /></button>
        </div>
        {repayment.transactionId && <div style={{ color: 'var(--muted)', fontSize: 11, marginTop: 12 }}>Transaction: {repayment.transactionId}</div>}
        <label htmlFor="repayment-otp" style={{ display: 'block', fontSize: 13, fontWeight: 700, marginTop: 18 }}>One-time password</label>
        <input
          id="repayment-otp"
          value={otpCode}
          onChange={(event) => setOtpCode(event.target.value)}
          inputMode="numeric"
          autoComplete="one-time-code"
          required
          disabled={processing}
          style={{ width: '100%', boxSizing: 'border-box', marginTop: 6, padding: 11, border: '1px solid var(--border)', borderRadius: 8, font: 'inherit', letterSpacing: 3 }}
        />
        {error && <div role="alert" style={{ color: '#991B1B', fontSize: 13, marginTop: 14 }}>{error}</div>}
        <button type="submit" disabled={processing || !otpCode.trim()} style={{ ...actionButtonStyle, width: '100%', background: 'var(--text)', color: '#fff', marginTop: 20 }}>
          {processing ? 'Verifying…' : 'Verify and complete repayment'}
        </button>
      </form>
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────────────
export default function Loans({ farmers = [], loans = [], cooperativeId, loading, onRefresh, dataStale = false }) {
  const [showModal, setShowModal] = useState(false)
  const [activeAction, setActiveAction] = useState(null)
  const [repayment, setRepayment] = useState(null)
  const [processing, setProcessing] = useState(null)
  const [actionError, setActionError] = useState(null)
  const [actionMessage, setActionMessage] = useState(null)
  const [payoutStatuses, setPayoutStatuses] = useState({})
  const [reconciling, setReconciling] = useState(null)
  const [exporting, setExporting] = useState(false)

  const reconcileLoan = useCallback(async (loanId, { quiet = false } = {}) => {
    if (!quiet) {
      setReconciling(loanId)
      setActionError(null)
    }
    try {
      const status = await fetchDisbursementStatus(loanId)
      setPayoutStatuses(current => ({ ...current, [loanId]: status }))
      if (!quiet) setActionMessage(`Loan #${loanId} payout status reconciled: ${status.payout_status}.`)
      return status
    } catch (error) {
      if (!quiet) setActionError(error.message || 'Could not reconcile payout status')
      return null
    } finally {
      if (!quiet) setReconciling(null)
    }
  }, [])

  useEffect(() => {
    let active = true
    const eligible = loans.filter(loan => !['rejected', 'cancelled', 'repaid'].includes(loan.status))
    Promise.all(eligible.map(async loan => {
      try {
        const status = await fetchDisbursementStatus(loan.id)
        return [loan.id, status]
      } catch {
        return null
      }
    })).then(results => {
      if (!active) return
      setPayoutStatuses(current => ({
        ...current,
        ...Object.fromEntries(results.filter(Boolean)),
      }))
    })
    return () => { active = false }
  }, [loans])

  const sorted = [...loans].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  const farmerName = loan => farmers.find(farmer => farmer.id === loan.farmer_id)?.name || `Farmer #${loan.farmer_id}`
  const table = useDashboardTable({
    rows: sorted,
    searchableText: loan => `${farmerName(loan)} ${loan.id} ${loan.purpose || ''} ${loan.moolre_transfer_ref || ''}`,
    statusValue: loan => loan.status,
    dateValue: loan => loan.created_at,
  })

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

  const openAction = (loan, type) => {
    setActionError(null)
    setActiveAction({ loan, type })
  }

  const handleAction = async (reason = '') => {
    const { loan, type } = activeAction
    setProcessing(loan.id)
    setActionError(null)
    setActionMessage(null)
    try {
      if (type === 'approve') await approveLoan(loan.id)
      if (type === 'reject') await rejectLoan(loan.id)
      if (type === 'cancel') await cancelLoan(loan.id, reason)
      if (type === 'disburse' || type === 'retry') {
        const result = await disburseLoan(loan.id)
        if (result.status === 'approved') {
          setActionMessage('Payout accepted and processing. Use Reconcile payout to check for completion.')
        }
        await reconcileLoan(loan.id, { quiet: true })
      }
      if (type === 'repay') {
        try {
          await repayLoan(loan.id)
          setActionMessage(`Repayment for loan #${loan.id} completed.`)
        } catch (error) {
          if (error instanceof RepaymentVerificationRequiredError) {
            setActiveAction(null)
            setRepayment({
              loanId: error.loanId || loan.id,
              transactionId: error.transactionId,
              message: error.message,
            })
            return
          }
          throw error
        }
      }
      setActiveAction(null)
      if (onRefresh) onRefresh()
    } catch (err) {
      setActionError(err.message || 'Action failed')
    } finally {
      setProcessing(null)
    }
  }

  const handleVerifyRepayment = async (otpCode) => {
    setProcessing(repayment.loanId)
    setActionError(null)
    try {
      await verifyLoanRepayment(repayment.loanId, otpCode)
      setActionMessage(`Repayment for loan #${repayment.loanId} verified and completed.`)
      setRepayment(null)
      if (onRefresh) onRefresh()
    } catch (error) {
      setActionError(error.message || 'Repayment verification failed')
    } finally {
      setProcessing(null)
    }
  }

  const rowButton = {
    borderRadius: 6, padding: '5px 8px', cursor: 'pointer', display: 'inline-flex',
    alignItems: 'center', gap: 4, fontSize: 11, fontWeight: 700, whiteSpace: 'nowrap',
  }
  const handleExport = async () => {
    setExporting(true)
    try {
      await exportDashboardReport('loans', cooperativeId, table.exportFilters)
    } finally {
      setExporting(false)
    }
  }

  return (
    <>
      <ModalPresence show={showModal}>
        <RequestLoanModal 
          farmers={farmers} 
          onClose={() => setShowModal(false)} 
          onSuccess={() => { setShowModal(false); if (onRefresh) onRefresh(); }} 
        />
      </ModalPresence>
      <ModalPresence show={Boolean(activeAction)}>
        {activeAction && (
          <ConfirmationModal
            action={activeAction}
            processing={processing === activeAction.loan.id}
            error={actionError}
            onClose={() => { if (!processing) { setActiveAction(null); setActionError(null) } }}
            onConfirm={handleAction}
          />
        )}
      </ModalPresence>
      <ModalPresence show={Boolean(repayment)}>
        {repayment && (
          <RepaymentOtpModal
            repayment={repayment}
            processing={processing === repayment.loanId}
            error={actionError}
            onClose={() => { if (!processing) { setRepayment(null); setActionError(null) } }}
            onVerify={handleVerifyRepayment}
          />
        )}
      </ModalPresence>

      {/* ── Toolbar ── */}
      {dataStale && (
        <div className="info-banner" role="status" style={{ marginBottom: 16 }}>
          Financial actions are paused until members and loans refresh successfully.
        </div>
      )}
      <DashboardTableToolbar
        label="Loans"
        table={table}
        statuses={[
          { value: 'requested', label: 'Requested' },
          { value: 'approved', label: 'Approved' },
          { value: 'disbursed', label: 'Disbursed' },
          { value: 'repaid', label: 'Repaid' },
          { value: 'rejected', label: 'Rejected' },
          { value: 'cancelled', label: 'Cancelled' },
        ]}
        onExport={handleExport}
        exporting={exporting}
      >
        <button className="btn-nav" disabled={dataStale} onClick={() => setShowModal(true)} style={{ fontSize: 13, padding: '8px 16px', display: 'flex', alignItems: 'center', gap: 6, background: 'var(--text)', color: '#fff' }}>
          <Plus size={15} /> Log Loan Request
        </button>
      </DashboardTableToolbar>

      {actionError && !activeAction && !repayment && (
        <div style={{ padding: 12, background: '#FEF2F2', color: '#991B1B', borderRadius: 8, fontSize: 13, marginBottom: 16 }}>
          {actionError}
        </div>
      )}
      {actionMessage && (
        <div style={{ padding: 12, background: '#EFF6FF', color: '#1E40AF', borderRadius: 8, fontSize: 13, marginBottom: 16 }}>
          {actionMessage}
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

        {table.filteredRows.length === 0 ? (
          <div style={{ padding: '32px 20px', color: 'var(--muted)', fontSize: 14 }}>
            {loans.length === 0
              ? 'No loans recorded yet. Click "Log Loan Request" to log a new application.'
              : 'No loans match the current filters.'}
          </div>
        ) : (
          <div className="table-scroll loans-table">
            <div className="pay-head">
              <span className="pt-lbl">Member</span>
              <span className="pt-lbl">Amount</span>
              <span className="pt-lbl">Purpose</span>
              <span className="pt-lbl">Repayment</span>
              <span className="pt-lbl">Status</span>
              <span className="pt-lbl" style={{ textAlign: 'right' }}>Action</span>
            </div>
            {table.pageRows.map(loan => {
              const farmer = farmers.find(f => f.id === loan.farmer_id)
              const name = farmer ? farmer.name : `Farmer #${loan.farmer_id}`
              const repayDate = fmtRepaymentDate(loan.expected_repayment_date || loan.repayment_date)
              const payout = payoutStatuses[loan.id]
              const payoutStatus = payout?.payout_status || 'none'
              const payoutLabels = {
                none: 'Payout: not started',
                pending: 'Payout: pending',
                failed: 'Payout: failed',
                completed: 'Payout: completed',
              }

              let cls = 'bdg-amber', label = loan.status
              if (['approved', 'disbursed', 'repaid'].includes(loan.status)) cls = 'bdg-green'
              if (['rejected', 'cancelled'].includes(loan.status)) cls = 'bdg-red'

              return (
                <div key={loan.id} className="pay-row" style={{ alignItems: 'center' }}>
                  <div><div className="pt-name">{name}</div><div className="pt-id">#{loan.id}</div></div>
                  <span className="pt-v">{fmtGHS(loan.amount)}</span>
                  <span className="pt-m" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{loan.purpose}</span>
                  <span className="pt-m">{repayDate}</span>
                  <div>
                    <span className={`bdg ${cls}`} style={{ textTransform: 'capitalize' }}>{label}</span>
                    <div style={{ fontSize: 10, color: payoutStatus === 'failed' ? '#991B1B' : 'var(--muted)', marginTop: 5 }}>
                      {payoutLabels[payoutStatus] || `Payout: ${payoutStatus}`}
                    </div>
                    {payout?.transfer_reference && <div className="pt-id" title={payout.transfer_reference}>{payout.transfer_reference}</div>}
                    {loan.approved_by && (
                      <div className="pt-id">
                        Approved by {loan.approved_by}{loan.approved_at ? ` · ${fmtRepaymentDate(loan.approved_at)}` : ''}
                      </div>
                    )}
                    {loan.repaid_at && <div className="pt-id">Repaid {fmtRepaymentDate(loan.repaid_at)}</div>}
                    {loan.cancellation_reason && (
                      <div className="pt-id" title={loan.cancellation_reason}>Cancelled: {loan.cancellation_reason}</div>
                    )}
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, justifyContent: 'flex-end' }}>
                    {loan.status === 'requested' && (
                      <>
                        <button disabled={dataStale} onClick={() => openAction(loan, 'approve')} style={{ ...rowButton, background: '#ecfdf5', color: '#047857', border: '1px solid #a7f3d0' }}>
                          <Check size={12} /> Approve
                        </button>
                        <button disabled={dataStale} onClick={() => openAction(loan, 'reject')} style={{ ...rowButton, background: '#FEF2F2', color: '#991B1B', border: '1px solid #fecaca' }}>
                          <XCircle size={12} /> Reject
                        </button>
                      </>
                    )}
                    {loan.status === 'approved' && payoutStatus === 'none' && (
                      <button disabled={dataStale} onClick={() => openAction(loan, 'disburse')} style={{ ...rowButton, background: 'var(--text)', color: '#fff', border: '1px solid var(--text)' }}>
                        <Send size={12} /> Disburse
                      </button>
                    )}
                    {payoutStatus === 'failed' && payout?.can_retry && (
                      <button disabled={dataStale} onClick={() => openAction(loan, 'retry')} style={{ ...rowButton, background: '#FFF7ED', color: '#9A3412', border: '1px solid #FDBA74' }}>
                        <RefreshCw size={12} /> Retry payout
                      </button>
                    )}
                    {['approved', 'disbursed'].includes(loan.status) && (
                      <button disabled={reconciling === loan.id} onClick={() => reconcileLoan(loan.id)} style={{ ...rowButton, background: '#fff', color: 'var(--text)', border: '1px solid var(--border)' }}>
                        {reconciling === loan.id ? <Loader2 size={12} className="spin" /> : <RefreshCw size={12} />} Reconcile payout
                      </button>
                    )}
                    {loan.status === 'disbursed' && (
                      <button disabled={dataStale} onClick={() => openAction(loan, 'repay')} style={{ ...rowButton, background: '#EFF6FF', color: '#1E40AF', border: '1px solid #BFDBFE' }}>
                        <Banknote size={12} /> Collect repayment
                      </button>
                    )}
                    {payout?.can_cancel && (
                      <button disabled={dataStale} onClick={() => openAction(loan, 'cancel')} style={{ ...rowButton, background: '#fff', color: '#991B1B', border: '1px solid #fecaca' }}>
                        <Ban size={12} /> Cancel
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
        <DashboardPagination label="Loans" table={table} />
      </div>
    </>
  )
}
