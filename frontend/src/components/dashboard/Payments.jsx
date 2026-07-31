// src/components/dashboard/Payments.jsx
import React, { useCallback, useMemo, useState } from 'react'
import { RefreshCw, ReceiptText } from 'lucide-react'
import { fetchTransactionReceipt, reconcileTransaction } from '../../api/transactions'
import { exportDashboardReport } from '../../api/reports'
import { TableSectionSkeleton } from './DashboardSkeleton'
import { DashboardPagination, DashboardTableToolbar, useDashboardTable } from './DashboardTableTools'

function fmtGHS(amount) {
  return `GHS ${Number(amount).toLocaleString('en-GH', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

// ── Main Component ────────────────────────────────────────────────────────
export default function Payments({ farmers = [], transactions = [], cooperativeId, loading, onRefresh, dataStale = false }) {
  const [exporting, setExporting] = useState(false)
  const [processingTransaction, setProcessingTransaction] = useState(null)
  const [operationError, setOperationError] = useState('')
  const [exportError, setExportError] = useState('')

  const completed = transactions.filter(t => t.status === 'completed')
  const totalCollected = completed.reduce((s, t) => s + t.amount, 0)

  const ussdChannels = ['13', '6', '7']
  const ussdAmount = completed.filter(t => ussdChannels.includes(t.channel)).reduce((s, t) => s + t.amount, 0)
  const momoAmount = completed.filter(t => !ussdChannels.includes(t.channel) && t.channel).reduce((s, t) => s + t.amount, 0)

  const ussdPct = totalCollected > 0 ? Math.round((ussdAmount / totalCollected) * 100) : 0
  const momoPct = totalCollected > 0 ? Math.round((momoAmount / totalCollected) * 100) : 0

  const sorted = useMemo(
    () => [...transactions].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)),
    [transactions],
  )
  const farmerName = useCallback(
    transaction => farmers.find(f => f.id === transaction.farmer_id)?.name || `Farmer #${transaction.farmer_id}`,
    [farmers],
  )
  const searchableText = useCallback(
    transaction => `${farmerName(transaction)} ${transaction.id} ${transaction.channel || ''}`,
    [farmerName],
  )
  const statusValue = useCallback(transaction => transaction.status, [])
  const dateValue = useCallback(transaction => transaction.created_at, [])
  const table = useDashboardTable({
    rows: sorted,
    searchableText,
    statusValue,
    dateValue,
  })
  const handleExport = async () => {
    setExporting(true)
    setExportError('')
    try {
      await exportDashboardReport('payments', cooperativeId, table.exportFilters)
    } catch (error) {
      setExportError(error.message || 'Could not export payments. Please try again.')
    } finally {
      setExporting(false)
    }
  }
  const handleReconcile = async (transactionId) => {
    setProcessingTransaction(transactionId)
    setOperationError('')
    try {
      await reconcileTransaction(transactionId)
      if (onRefresh) await onRefresh()
    } catch (error) {
      setOperationError(error.message || 'Could not reconcile payment.')
    } finally {
      setProcessingTransaction(null)
    }
  }
  const handleReceipt = async (transactionId) => {
    setProcessingTransaction(transactionId)
    setOperationError('')
    try {
      const receipt = await fetchTransactionReceipt(transactionId)
      const url = window.URL.createObjectURL(new window.Blob(
        [JSON.stringify(receipt, null, 2)],
        { type: 'application/json' },
      ))
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `${receipt.receipt_number}.json`
      anchor.click()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      setOperationError(error.message || 'Could not generate receipt.')
    } finally {
      setProcessingTransaction(null)
    }
  }

  if (loading) return <TableSectionSkeleton statCount={3} rows={6} columns={5} />

  return (
    <>
      <DashboardTableToolbar
        label="Payments"
        table={table}
        statuses={[
          { value: 'completed', label: 'Paid' },
          { value: 'pending', label: 'Pending' },
          { value: 'failed', label: 'Failed' },
        ]}
        onExport={handleExport}
        exporting={exporting}
        exportError={exportError}
      />
      <div className="info-banner" role="status" style={{ marginBottom: 16 }}>
        Cooperatives create dues obligations and send reminders. Members initiate dues and loan repayments through AgroOS USSD; this ledger only records and reconciles those payments.
      </div>
      {dataStale && (
        <div className="info-banner" role="status" style={{ marginBottom: 16 }}>
          Collections are paused until members and payments refresh successfully.
        </div>
      )}
      {operationError && <div className="dashboard-inline-error" role="alert">{operationError}</div>}

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

        {table.filteredRows.length === 0 ? (
          <div style={{ padding: '32px 20px', color: 'var(--muted)', fontSize: 14 }}>
            {transactions.length === 0
              ? 'No farmer-initiated payments have been recorded yet.'
              : 'No payments match the current filters.'}
          </div>
        ) : (
          <div className="table-scroll">
            <div className="pay-head">
              {['Member', 'Amount', 'Method', 'Date', 'Status'].map(h => <span key={h} className="pt-lbl">{h}</span>)}
            </div>
            {table.pageRows.map(tx => {
              const farmer = farmers.find(f => f.id === tx.farmer_id)
              const name = farmer ? farmer.name : `Farmer #${tx.farmer_id}`
              const channelLabel = {
                ussdk: 'Farmer USSD',
                moolre_ussd: 'Farmer USSD',
                dashboard: 'Legacy staff request',
              }
              const method = channelLabel[tx.initiation_channel]
                || (ussdChannels.includes(tx.channel) ? 'USSD' : (tx.channel || 'Manual'))
              const date = new Date(tx.created_at).toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })
              let cls = 'bdg-amber', label = 'Pending'
              if (tx.status === 'pending' && tx.customer_action === 'initiating') label = 'Confirming initiation'
              if (tx.status === 'pending' && tx.customer_action === 'otp') label = 'Awaiting member OTP'
              if (tx.status === 'pending' && tx.customer_action === 'processing_otp') label = 'Processing member OTP'
              if (tx.status === 'pending' && tx.customer_action === 'approval') label = 'Awaiting phone approval'
              if (tx.status === 'completed') { cls = 'bdg-green'; label = 'Paid' }
              if (tx.status === 'failed') { cls = 'bdg-red'; label = 'Failed' }
              if (tx.customer_action === 'expired') { cls = 'bdg-red'; label = 'Expired' }
              return (
                <div key={tx.id} className="pay-row">
                  <div><div className="pt-name">{name}</div><div className="pt-id">#{tx.id}</div></div>
                  <span className="pt-v">{fmtGHS(tx.amount)}</span>
                  <span className="pt-m">{method}</span>
                  <span className="pt-m">{date}</span>
                  <div className="payment-row-actions">
                    <span className={`bdg ${cls}`}>{label}</span>
                    <button
                      type="button"
                      className="table-row-action"
                      onClick={() => handleReceipt(tx.id)}
                      disabled={processingTransaction === tx.id}
                      aria-label={`Download receipt for transaction ${tx.id}`}
                    >
                      <ReceiptText size={12} /> Receipt
                    </button>
                    {tx.status === 'pending' && (
                      <button
                        type="button"
                        className="table-row-action"
                        onClick={() => handleReconcile(tx.id)}
                        disabled={processingTransaction === tx.id}
                        aria-label={`Reconcile pending transaction ${tx.id}`}
                      >
                        <RefreshCw size={12} /> Check
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
        <DashboardPagination label="Payments" table={table} />
      </div>
    </>
  )
}
