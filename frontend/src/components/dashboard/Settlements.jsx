import React, { useState } from 'react'
import {
  approveSettlement,
  calculateSettlement,
  paySettlement,
  retrySettlement,
  reviewSettlement,
} from '../../api/commerce'
import { ActionButton, CommerceTable, StatusBadge, money } from './CommerceTools'
import { TableSectionSkeleton } from './DashboardSkeleton'

export function settlementLines(settlement) {
  for (const key of ['farmer_lines', 'lines', 'items', 'breakdown']) {
    if (Array.isArray(settlement?.[key])) return settlement[key]
  }
  return []
}

function deductionsFor(line) {
  if (Array.isArray(line.deductions)) return line.deductions.map((deduction, index) => ({
    label: (deduction.label || deduction.deduction_type || deduction.type || deduction.name || `Deduction ${index + 1}`).replaceAll('_', ' '),
    amount: Number(deduction.amount || deduction.value || 0),
  }))
  if (line.deductions && typeof line.deductions === 'object') {
    return Object.entries(line.deductions).map(([label, amount]) => ({ label: label.replaceAll('_', ' '), amount: Number(amount || 0) }))
  }
  const known = [
    ['Cooperative fee', line.cooperative_fee],
    ['Transport', line.transport_deduction],
    ['Quality adjustment', line.quality_deduction],
    ['Loan recovery', line.loan_recovery],
  ]
  return known.filter(([, amount]) => Number(amount) !== 0).map(([label, amount]) => ({ label, amount: Number(amount) }))
}

function lineAmounts(line) {
  const deductions = deductionsFor(line)
  const gross = Number(line.gross_amount ?? line.gross ?? 0)
  const deductionTotal = Number(line.deductions_total ?? line.total_deductions ?? line.deduction_amount ?? deductions.reduce((sum, item) => sum + item.amount, 0))
  const net = Number(line.net_amount ?? line.net_payable ?? line.net ?? gross - deductionTotal)
  return { gross, deductionTotal, net, deductions }
}

function isVerifiedSale(sale) {
  return Boolean(sale.receipt_verified_at || sale.funds_verified_at || sale.payment_verified || sale.funds_verified)
    || ['funded', 'verified', 'funds_verified', 'settlement_ready'].includes(String(sale.status || sale.state).toLowerCase())
}

function failedLines(settlement) {
  return settlementLines(settlement).filter(line => ['failed', 'error'].includes(String(line.payout_status || line.status).toLowerCase()))
}

export function SettlementBreakdown({ settlement, farmers = [] }) {
  const lines = settlementLines(settlement)
  return (
    <div className="admin-card" style={{ marginBottom: 20 }}>
      <div className="admin-card-head">
        <div>
          <div className="admin-card-title">Farmer settlement preview</div>
          <div className="pt-m">Review gross earnings, every deduction, and net payout before approval.</div>
        </div>
        <StatusBadge status={settlement.status || settlement.state || 'calculated'} />
      </div>
      {lines.length === 0 ? (
        <div className="dashboard-empty">No farmer lines were returned for this settlement.</div>
      ) : lines.map((line, index) => {
        const amounts = lineAmounts(line)
        const membershipId = line.membership_id ?? line.farmer_id
        const name = line.farmer_name || farmers.find(f => Number(f.id) === Number(membershipId))?.name || `Farmer #${membershipId}`
        return (
          <div className="pay-row" style={{ gridTemplateColumns: '1.5fr 1fr 1.4fr 1fr' }} key={line.id ?? line.farmer_id ?? index}>
            <div>
              <div className="pt-name">{name}</div>
              <div className="pt-id">{Number(line.quantity_kg ?? line.accepted_quantity_kg ?? 0).toLocaleString()} kg × {money(line.unit_price)}/kg</div>
            </div>
            <div><div className="pt-id">Gross</div><strong>{money(amounts.gross)}</strong></div>
            <div>
              <div className="pt-id">Deductions ({money(amounts.deductionTotal)})</div>
              {amounts.deductions.length
                ? amounts.deductions.map(item => <div className="pt-m" key={item.label}>{item.label}: {money(item.amount)}</div>)
                : <div className="pt-m">No deductions</div>}
            </div>
            <div><div className="pt-id">Net payable</div><strong>{money(amounts.net)}</strong></div>
          </div>
        )
      })}
    </div>
  )
}

export default function Settlements({ settlements = [], sales = [], farmers = [], cooperativeId, loading, onRefresh }) {
  const [saleId, setSaleId] = useState('')
  const [preview, setPreview] = useState(null)
  const [busy, setBusy] = useState(null)
  const [error, setError] = useState('')
  const verifiedSales = sales.filter(isVerifiedSale)

  async function act(key, operation, showResult = false) {
    setBusy(key)
    setError('')
    try {
      const result = await operation()
      if (showResult && result) setPreview(result)
      await onRefresh?.()
    } catch (reason) {
      setError(reason.message || 'Could not update settlement.')
    } finally {
      setBusy(null)
    }
  }

  if (loading) return <TableSectionSkeleton statCount={0} rows={6} columns={6} />

  return (
    <>
      <div className="admin-card" style={{ padding: 18, marginBottom: 20 }}>
        <div className="admin-card-title">Calculate farmer settlement</div>
        <p className="pt-m">Only sales with independently verified buyer funds are eligible.</p>
        {verifiedSales.length === 0 ? (
          <div className="info-banner" role="status">No verified buyer funds are available. Record and verify a sale receipt first.</div>
        ) : (
          <div className="payment-row-actions">
            <label>
              <span className="sr-only">Verified sale</span>
              <select aria-label="Verified sale" value={saleId} onChange={event => setSaleId(event.target.value)}>
                <option value="">Select verified sale…</option>
                {verifiedSales.map(sale => <option key={sale.id} value={sale.id}>Sale #{sale.id} · {money(sale.total_amount || sale.gross_amount)}</option>)}
              </select>
            </label>
            <button
              type="button"
              className="btn-nav"
              disabled={!saleId || busy === 'calculate'}
              onClick={() => act('calculate', () => calculateSettlement(Number(saleId), {}), true)}
            >
              Calculate settlement
            </button>
          </div>
        )}
      </div>
      {error && <div className="dashboard-inline-error" role="alert">{error}</div>}
      {preview && <SettlementBreakdown settlement={preview} farmers={farmers} />}
      <CommerceTable
        label="Farmer settlements"
        report="settlements"
        cooperativeId={cooperativeId}
        rows={settlements}
        empty="No farmer settlements have been calculated."
        statuses={[
          { value: 'draft', label: 'Draft' },
          { value: 'pending_approval', label: 'Pending approval' },
          { value: 'approved', label: 'Approved' },
          { value: 'processing', label: 'Processing' },
          { value: 'partially_paid', label: 'Partially paid' },
          { value: 'completed', label: 'Completed' },
        ]}
        columns={[
          { label: 'Settlement', render: row => `#${row.id}` },
          { label: 'Sale', render: row => `#${row.sale_id ?? row.buyer_sale_id ?? '—'}` },
          { label: 'Farmers', render: row => settlementLines(row).length || row.farmer_count || '—' },
          { label: 'Gross', render: row => money(row.gross_total ?? row.total_gross ?? row.gross_amount) },
          { label: 'Net payable', render: row => money(row.net_total ?? row.total_net ?? row.net_payable) },
          { label: 'Status', render: row => <StatusBadge status={row.status || row.state} /> },
          {
            label: 'Actions',
            width: '2fr',
            render: row => {
              const status = String(row.status || row.state || 'draft').toLowerCase()
              const failed = failedLines(row)
              return (
                <div className="payment-row-actions">
                  <ActionButton onClick={() => setPreview(row)} label={`View settlement ${row.id} breakdown`}>View breakdown</ActionButton>
                  {status === 'draft' && <ActionButton disabled={busy === row.id} onClick={() => act(row.id, () => reviewSettlement(row.id))} label={`Review settlement ${row.id}`}>Submit for approval</ActionButton>}
                  {status === 'pending_approval' && <ActionButton disabled={busy === row.id} onClick={() => act(row.id, () => approveSettlement(row.id))} label={`Approve settlement ${row.id}`}>Approve</ActionButton>}
                  {status === 'approved' && <ActionButton disabled={busy === row.id} onClick={() => act(row.id, () => paySettlement(row.id))} label={`Pay settlement ${row.id}`}>Pay farmers</ActionButton>}
                  {failed.length > 0 && (
                    <ActionButton disabled={busy === row.id} onClick={() => act(row.id, () => retrySettlement(row.id))} label={`Retry ${failed.length} failed transfers for settlement ${row.id}`}>
                      Retry {failed.length} failed
                    </ActionButton>
                  )}
                </div>
              )
            },
          },
        ]}
      />
    </>
  )
}
