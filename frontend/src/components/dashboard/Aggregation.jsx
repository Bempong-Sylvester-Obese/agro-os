import React, { useState } from 'react'
import { closeAggregation, createAggregation } from '../../api/commerce'
import { ActionButton, CommerceTable, InlineForm, StatusBadge, dateText } from './CommerceTools'
import { TableSectionSkeleton } from './DashboardSkeleton'

export default function Aggregation({ batches = [], cooperativeId, loading, onRefresh }) {
  const [showForm, setShowForm] = useState(false)
  const [busy, setBusy] = useState(null)
  const [error, setError] = useState('')

  async function close(batch) {
    setBusy(batch.id)
    setError('')
    try {
      await closeAggregation(batch.id)
      await onRefresh?.()
    } catch (reason) {
      setError(reason.message || 'Could not close aggregation batch.')
    } finally {
      setBusy(null)
    }
  }

  if (loading) return <TableSectionSkeleton statCount={0} rows={6} columns={6} />

  return (
    <>
      {showForm && (
        <InlineForm
          title="Open aggregation batch"
          submitLabel="Open batch"
          initial={{ code: '', crop_type: '' }}
          fields={[
            { name: 'code', label: 'Batch code' },
            { name: 'crop_type', label: 'Crop' },
          ]}
          onSubmit={async values => {
            await createAggregation(values)
            setShowForm(false)
            await onRefresh?.()
          }}
        />
      )}
      {error && <div className="dashboard-inline-error" role="alert">{error}</div>}
      <CommerceTable
        label="Aggregation batches"
        report="aggregation"
        cooperativeId={cooperativeId}
        rows={batches}
        empty="No aggregation batches are open."
        statuses={[
          { value: 'open', label: 'Open' },
          { value: 'closed', label: 'Closed' },
          { value: 'sold', label: 'Sold' },
        ]}
        columns={[
          { label: 'Batch', width: '1.5fr', render: row => <><div className="pt-name">{row.code || row.name || `Batch #${row.id}`}</div><div className="pt-id">#{row.id}</div></> },
          { label: 'Crop', render: row => row.crop_type || row.crop || '—' },
          { label: 'Accepted weight', render: row => `${Number(row.total_quantity_kg ?? row.quantity_kg ?? row.accepted_weight_kg ?? 0).toLocaleString()} kg` },
          { label: 'Opened', render: row => dateText(row.opened_at || row.created_at) },
          { label: 'Status', render: row => <StatusBadge status={row.status || row.state || 'open'} /> },
          {
            label: 'Actions',
            render: row => String(row.status || row.state || 'open').toLowerCase() === 'open'
              ? <ActionButton disabled={busy === row.id} onClick={() => close(row)} label={`Close batch ${row.id}`}>Close batch</ActionButton>
              : '—',
          },
        ]}
      >
        <button type="button" className="btn-nav" onClick={() => setShowForm(current => !current)}>
          {showForm ? 'Cancel' : 'Open batch'}
        </button>
      </CommerceTable>
    </>
  )
}
