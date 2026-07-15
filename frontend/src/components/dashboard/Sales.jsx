import React, { useState } from 'react'
import { confirmSale, createSale, recordSaleReceipt, verifySaleReceipt } from '../../api/commerce'
import { ActionButton, CommerceTable, InlineForm, StatusBadge, fieldStyle, money } from './CommerceTools'
import { TableSectionSkeleton } from './DashboardSkeleton'

function receiptRecorded(sale) {
  return Array.isArray(sale.receipts) && sale.receipts.length > 0
}

function receiptVerified(sale) {
  return String(sale.status).toLowerCase() === 'funded'
    || sale.receipts?.some(receipt => receipt.status === 'verified')
}

export default function Sales({ sales = [], buyers = [], batches = [], cooperativeId, loading, onRefresh }) {
  const [showForm, setShowForm] = useState(false)
  const [receiptSale, setReceiptSale] = useState(null)
  const [receipt, setReceipt] = useState({ amount: '', reference: '' })
  const [busy, setBusy] = useState(null)
  const [error, setError] = useState('')
  const closedBatches = batches.filter(batch => String(batch.status || batch.state).toLowerCase() === 'closed')

  async function act(id, operation) {
    setBusy(id)
    setError('')
    try {
      await operation()
      setReceiptSale(null)
      await onRefresh?.()
    } catch (reason) {
      setError(reason.message || 'Could not update sale.')
    } finally {
      setBusy(null)
    }
  }

  if (loading) return <TableSectionSkeleton statCount={0} rows={6} columns={6} />

  return (
    <>
      {showForm && (
        <InlineForm
          title="Record buyer sale"
          submitLabel="Record sale"
          initial={{ aggregation_batch_id: '', buyer_id: '', quantity_kg: '', unit_price: '' }}
          fields={[
            { name: 'aggregation_batch_id', label: 'Closed batch', type: 'select', options: closedBatches.map(batch => ({ value: batch.id, label: batch.code || batch.name || `Batch #${batch.id}` })) },
            { name: 'buyer_id', label: 'Buyer', type: 'select', options: buyers.map(buyer => ({ value: buyer.id, label: buyer.name || buyer.business_name })) },
            { name: 'quantity_kg', label: 'Sale quantity (kg)', type: 'number', min: '0.01', step: '0.01' },
            { name: 'unit_price', label: 'Price per kg (GHS)', type: 'number', min: '0.01', step: '0.01' },
          ]}
          onSubmit={async values => {
            await createSale({
              ...values,
              aggregation_batch_id: Number(values.aggregation_batch_id),
              buyer_id: Number(values.buyer_id),
              quantity_kg: Number(values.quantity_kg),
              unit_price: Number(values.unit_price),
            })
            setShowForm(false)
            await onRefresh?.()
          }}
        />
      )}
      {receiptSale && (
        <form
          className="admin-card"
          style={{ padding: 18, marginBottom: 20 }}
          onSubmit={event => {
            event.preventDefault()
            act(receiptSale.id, () => recordSaleReceipt(receiptSale.id, {
              amount: Number(receipt.amount),
              reference: receipt.reference,
            }))
          }}
        >
          <div className="admin-card-title">Record receipt for sale #{receiptSale.id}</div>
          <div className="modal-row" style={{ marginTop: 12 }}>
            <label>Amount received<input aria-label="Amount received" style={fieldStyle} type="number" min="0.01" step="0.01" required value={receipt.amount} onChange={event => setReceipt(current => ({ ...current, amount: event.target.value }))} /></label>
            <label>Payment reference<input aria-label="Payment reference" style={fieldStyle} required value={receipt.reference} onChange={event => setReceipt(current => ({ ...current, reference: event.target.value }))} /></label>
          </div>
          <div className="payment-row-actions" style={{ marginTop: 12 }}>
            <button className="btn-nav" type="submit" disabled={busy === receiptSale.id}>Save receipt</button>
            <button className="table-row-action" type="button" onClick={() => setReceiptSale(null)}>Cancel</button>
          </div>
        </form>
      )}
      {error && <div className="dashboard-inline-error" role="alert">{error}</div>}
      <div className="info-banner" role="status" style={{ marginBottom: 16 }}>
        Buyer funds must be recorded and independently verified before farmer settlement can be calculated.
      </div>
      <CommerceTable
        label="Buyer sales"
        report="sales"
        cooperativeId={cooperativeId}
        rows={sales}
        empty="No buyer sales have been recorded."
        statuses={[
          { value: 'draft', label: 'Draft' },
          { value: 'confirmed', label: 'Confirmed' },
          { value: 'receipt_recorded', label: 'Receipt recorded' },
          { value: 'verified', label: 'Funds verified' },
        ]}
        columns={[
          { label: 'Sale', render: row => `#${row.id}` },
          { label: 'Buyer', width: '1.4fr', render: row => row.buyer_name || buyers.find(b => Number(b.id) === Number(row.buyer_id))?.name || `Buyer #${row.buyer_id}` },
          { label: 'Quantity', render: row => `${Number(row.quantity_kg ?? row.sale_quantity_kg ?? 0).toLocaleString()} kg` },
          { label: 'Gross value', render: row => money(row.total_amount ?? row.gross_amount ?? Number(row.quantity_kg || 0) * Number(row.unit_price || 0)) },
          {
            label: 'Funds',
            render: row => <StatusBadge status={receiptVerified(row) ? 'verified' : receiptRecorded(row) ? 'receipt_recorded' : row.status || 'draft'} />,
          },
          {
            label: 'Actions',
            width: '2fr',
            render: row => (
              <div className="payment-row-actions">
                {String(row.status || 'draft').toLowerCase() === 'draft' && (
                  <ActionButton disabled={busy === row.id} onClick={() => act(row.id, () => confirmSale(row.id))} label={`Confirm sale ${row.id}`}>Confirm terms</ActionButton>
                )}
                {String(row.status || '').toLowerCase() !== 'draft' && (
                  <ActionButton onClick={() => { setReceiptSale(row); setReceipt({ amount: row.gross_amount || row.total_amount || '', reference: '' }) }} label={`Record receipt for sale ${row.id}`}>Record receipt</ActionButton>
                )}
                {row.receipts?.find(receipt => receipt.status === 'pending') && (
                  <ActionButton
                    disabled={busy === row.id}
                    onClick={() => act(row.id, () => verifySaleReceipt(
                      row.id,
                      row.receipts.find(receipt => receipt.status === 'pending').id,
                    ))}
                    label={`Verify funds for sale ${row.id}`}
                  >
                    Verify funds
                  </ActionButton>
                )}
                {String(row.status).toLowerCase() === 'funded' && <span className="pt-m">Ready to settle</span>}
              </div>
            ),
          },
        ]}
      >
        <button type="button" className="btn-nav" onClick={() => setShowForm(current => !current)}>
          {showForm ? 'Cancel' : 'Record sale'}
        </button>
      </CommerceTable>
    </>
  )
}
