// src/components/dashboard/Loans.jsx
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { X, Loader2, Check, XCircle, Send, RefreshCw, Bell, Ban } from 'lucide-react'
import {
  approveLoan,
  rejectLoan,
  disburseLoan,
  cancelLoan,
  fetchDisbursementStatus,
  sendLoanReminder,
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

const ACTION_COPY = {
  approve: ['Approve loan?', 'This loan will become eligible for disbursement.', 'Approve loan'],
  reject: ['Reject loan?', 'Give the farmer a clear reason. AgroOS will send it by SMS.', 'Reject and notify'],
  cancel: ['Cancel loan?', 'Provide a reason for cancelling this loan.', 'Cancel loan'],
  disburse: ['Disburse loan?', 'This starts a payout to the member. Confirm the amount and member before continuing.', 'Start disbursement'],
  retry: ['Retry payout?', 'This retries the failed payout using the existing loan details.', 'Retry payout'],
  reminder: ['Send repayment reminder?', 'This sends an SMS reminder only. The member initiates repayment through AgroOS USSD.', 'Send reminder'],
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
  const [repaymentDate, setRepaymentDate] = useState('')
  const [validationError, setValidationError] = useState('')
  const [title, description, confirmLabel] = ACTION_COPY[action.type]
  const destructive = ['reject', 'cancel'].includes(action.type)

  const submit = (event) => {
    event.preventDefault()
    if (action.type === 'approve' && !repaymentDate) {
      setValidationError('Choose a future repayment due date.')
      return
    }
    if (['cancel', 'reject'].includes(action.type) && !reason.trim()) {
      setValidationError(
        action.type === 'reject'
          ? 'Enter a rejection reason for the farmer.'
          : 'Enter a cancellation reason.',
      )
      return
    }
    onConfirm({ reason, repaymentDate })
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
        {['cancel', 'reject'].includes(action.type) && (
          <div style={{ marginTop: 16 }}>
            <label htmlFor="loan-decision-reason" style={{ fontSize: 13, fontWeight: 700 }}>
              {action.type === 'reject' ? 'Reason sent to farmer' : 'Cancellation reason'}
            </label>
            <textarea
              id="loan-decision-reason"
              value={reason}
              onChange={(event) => { setReason(event.target.value); setValidationError('') }}
              disabled={processing}
              rows={3}
              style={{ display: 'block', width: '100%', boxSizing: 'border-box', marginTop: 6, padding: 10, border: '1px solid var(--border)', borderRadius: 8, resize: 'vertical', font: 'inherit' }}
            />
          </div>
        )}
        {action.type === 'approve' && (
          <div style={{ marginTop: 16 }}>
            <label htmlFor="loan-repayment-date" style={{ fontSize: 13, fontWeight: 700 }}>Repayment due date</label>
            <input
              id="loan-repayment-date"
              type="date"
              value={repaymentDate}
              onChange={(event) => { setRepaymentDate(event.target.value); setValidationError('') }}
              disabled={processing}
              required
              style={{ display: 'block', width: '100%', boxSizing: 'border-box', marginTop: 6, padding: 10, border: '1px solid var(--border)', borderRadius: 8, font: 'inherit' }}
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

// ── Main Component ────────────────────────────────────────────────────────
export default function Loans({ farmers = [], loans = [], cooperativeId, loading, onRefresh, dataStale = false }) {
  const [activeAction, setActiveAction] = useState(null)
  const [processing, setProcessing] = useState(null)
  const [actionError, setActionError] = useState(null)
  const [actionMessage, setActionMessage] = useState(null)
  const [payoutStatuses, setPayoutStatuses] = useState({})
  const [reconciling, setReconciling] = useState(null)
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState('')
  const requestedPayoutIds = useRef(new Set())

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
    const unknownEligible = loans.filter(loan => (
      !['rejected', 'cancelled', 'repaid'].includes(loan.status)
      && !requestedPayoutIds.current.has(loan.id)
    ))
    unknownEligible.forEach(loan => requestedPayoutIds.current.add(loan.id))
    Promise.all(unknownEligible.map(async loan => {
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

  const sorted = useMemo(
    () => [...loans].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)),
    [loans],
  )
  const farmerName = useCallback(
    loan => farmers.find(farmer => farmer.id === loan.farmer_id)?.name || `Farmer #${loan.farmer_id}`,
    [farmers],
  )
  const searchableText = useCallback(
    loan => `${farmerName(loan)} ${loan.id} ${loan.purpose || ''} ${loan.moolre_transfer_ref || ''}`,
    [farmerName],
  )
  const statusValue = useCallback(loan => loan.status, [])
  const dateValue = useCallback(loan => loan.created_at, [])
  const table = useDashboardTable({
    rows: sorted,
    searchableText,
    statusValue,
    dateValue,
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

  const handleAction = async ({ reason = '', repaymentDate = '' } = {}) => {
    const { loan, type } = activeAction
    setProcessing(loan.id)
    setActionError(null)
    setActionMessage(null)
    try {
      if (type === 'approve') await approveLoan(loan.id, repaymentDate)
      if (type === 'reject') {
        const result = await rejectLoan(loan.id, reason)
        setActionMessage(
          result.notification_status === 'sent'
            ? `Loan #${loan.id} rejected and the farmer was notified by SMS.`
            : `Loan #${loan.id} rejected, but the SMS could not be delivered.`,
        )
      }
      if (type === 'cancel') await cancelLoan(loan.id, reason)
      if (type === 'disburse' || type === 'retry') {
        const result = await disburseLoan(loan.id)
        if (result.status === 'approved') {
          setActionMessage('Payout accepted and processing. Use Reconcile payout to check for completion.')
        }
        await reconcileLoan(loan.id, { quiet: true })
      }
      if (type === 'reminder') {
        await sendLoanReminder(loan.id)
        setActionMessage(`Repayment reminder sent for loan #${loan.id}.`)
      }
      setActiveAction(null)
      if (onRefresh) onRefresh()
    } catch (err) {
      setActionError(err.message || 'Action failed')
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
    setExportError('')
    try {
      await exportDashboardReport('loans', cooperativeId, table.exportFilters)
    } catch (error) {
      setExportError(error.message || 'Could not export loans. Please try again.')
    } finally {
      setExporting(false)
    }
  }

  return (
    <>
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
        exportError={exportError}
      />

      {actionError && !activeAction && (
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
              ? 'No farmer loan requests yet. Requests submitted through USSD will appear here.'
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
              const dueLabels = {
                not_due: 'Not due',
                scheduled: 'Scheduled',
                due_soon: 'Due soon',
                due_today: 'Due today',
                overdue: `${loan.days_overdue || 0} days overdue`,
                paid: 'Paid',
              }
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
                  <div>
                    <div className="pt-name">{name}</div>
                    <div className="pt-id">
                      #{loan.id}
                      {['moolre_ussd', 'ussdk'].includes(loan.request_channel) ? ' · Farmer USSD request' : ''}
                    </div>
                  </div>
                  <span className="pt-v">{fmtGHS(loan.amount)}</span>
                  <span className="pt-m" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{loan.purpose}</span>
                  <span className="pt-m">
                    {repayDate}
                    <span className={`bdg ${loan.due_state === 'overdue' ? 'bdg-red' : 'bdg-amber'}`} style={{ display: 'block', width: 'fit-content', marginTop: 5 }}>
                      {dueLabels[loan.due_state] || 'Not due'}
                    </span>
                    {loan.last_reminder_at && (
                      <small style={{ display: 'block', marginTop: 5 }}>
                        Last reminder {new Date(loan.last_reminder_at).toLocaleDateString()}
                      </small>
                    )}
                    {loan.next_reminder_date && (
                      <small style={{ display: 'block' }}>
                        Next reminder {fmtRepaymentDate(loan.next_reminder_date)}
                      </small>
                    )}
                  </span>
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
                      <button disabled={dataStale} onClick={() => openAction(loan, 'reminder')} style={{ ...rowButton, background: '#EFF6FF', color: '#1E40AF', border: '1px solid #BFDBFE' }}>
                        <Bell size={12} /> Send reminder
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
