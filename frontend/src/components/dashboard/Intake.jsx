import React, { useState } from 'react'
import {
  acceptIntake,
  assignIntake,
  cancelIntake,
  createIntake,
  rejectIntake,
} from '../../api/commerce'
import { ActionButton, CommerceTable, InlineForm, StatusBadge, dateText } from './CommerceTools'
import { TableSectionSkeleton } from './DashboardSkeleton'

export default function Intake({ records = [], farmers = [], batches = [], cooperativeId, loading, onRefresh }) {
  const [showForm, setShowForm] = useState(false)
  const [busy, setBusy] = useState(null)
  const [error, setError] = useState('')
  const [assignments, setAssignments] = useState({})
  const [reviewing, setReviewing] = useState(null)
  const farmerOptions = farmers.map(farmer => ({ value: farmer.id, label: farmer.name }))
  const openBatches = batches.filter(batch => !['closed', 'sold'].includes(String(batch.status || batch.state).toLowerCase()))
  const batchOptions = openBatches.map(batch => ({
    value: batch.id,
    label: batch.code || batch.name || `Batch #${batch.id}`,
  }))

  async function act(key, operation) {
    setBusy(key)
    setError('')
    try {
      await operation()
      await onRefresh?.()
    } catch (reason) {
      setError(reason.message || 'Could not update produce intake.')
    } finally {
      setBusy(null)
    }
  }

  if (loading) return <TableSectionSkeleton statCount={0} rows={6} columns={6} />

  return (
    <>
      {showForm && (
        <InlineForm
          title="Record produce intake"
          submitLabel="Record intake"
          initial={{ membership_id: '', crop_type: '', quantity_kg: '', quality_grade: '', collection_point: '' }}
          fields={[
            { name: 'membership_id', label: 'Farmer', type: 'select', options: farmerOptions },
            { name: 'crop_type', label: 'Crop' },
            { name: 'quantity_kg', label: 'Weight (kg)', type: 'number', min: '0.01', step: '0.01' },
            { name: 'quality_grade', label: 'Grade', required: false },
            { name: 'collection_point', label: 'Collection point', required: false },
          ]}
          onSubmit={async values => {
            await createIntake({ ...values, membership_id: Number(values.membership_id), quantity_kg: Number(values.quantity_kg) })
            setShowForm(false)
            await onRefresh?.()
          }}
        />
      )}
      {reviewing && (
        <InlineForm
          title={reviewing.type === 'accept' ? 'Accept and grade intake' : 'Reject intake'}
          submitLabel={reviewing.type === 'accept' ? 'Accept intake' : 'Reject intake'}
          initial={
            reviewing.type === 'accept'
              ? {
                  net_quantity_kg: reviewing.row.quantity_kg,
                  quality_grade: reviewing.row.quality_grade || '',
                }
              : { reason: '' }
          }
          fields={
            reviewing.type === 'accept'
              ? [
                  {
                    name: 'net_quantity_kg',
                    label: 'Accepted net weight (kg)',
                    type: 'number',
                    min: '0.001',
                    step: '0.001',
                  },
                  { name: 'quality_grade', label: 'Final grade', required: false },
                ]
              : [{ name: 'reason', label: 'Rejection reason' }]
          }
          onSubmit={async values => {
            if (reviewing.type === 'accept') {
              await acceptIntake(reviewing.row.id, {
                ...values,
                net_quantity_kg: Number(values.net_quantity_kg),
              })
            } else {
              await rejectIntake(reviewing.row.id, values.reason)
            }
            setReviewing(null)
            await onRefresh?.()
          }}
        />
      )}
      {error && <div className="dashboard-inline-error" role="alert">{error}</div>}
      <CommerceTable
        label="Produce intake"
        report="intake"
        cooperativeId={cooperativeId}
        rows={records}
        empty="No produce deliveries have been recorded."
        statuses={[
          { value: 'received', label: 'Received' },
          { value: 'accepted', label: 'Accepted' },
          { value: 'rejected', label: 'Rejected' },
          { value: 'batched', label: 'Batched' },
          { value: 'cancelled', label: 'Cancelled' },
        ]}
        columns={[
          { label: 'Farmer', width: '1.5fr', render: row => row.farmer_name || farmers.find(f => Number(f.id) === Number(row.membership_id))?.name || `Farmer #${row.membership_id}` },
          { label: 'Crop', render: row => row.crop_type || row.crop || '—' },
          {
            label: 'Weight',
            render: row => (
              <span>
                {Number(row.quantity_kg || 0).toLocaleString()} kg gross
                {row.net_quantity_kg && ` · ${Number(row.net_quantity_kg).toLocaleString()} kg net`}
              </span>
            ),
          },
          { label: 'Received', render: row => dateText(row.received_at || row.created_at) },
          { label: 'Status', render: row => <StatusBadge status={row.status || row.state} /> },
          {
            label: 'Actions',
            width: '2fr',
            render: row => {
              const status = String(row.status || row.state || 'received').toLowerCase()
              return (
                <div className="payment-row-actions">
                  {status === 'received' && (
                    <>
                      <ActionButton
                        disabled={busy === row.id}
                        onClick={() => setReviewing({ type: 'accept', row })}
                        label={`Accept intake ${row.id}`}
                      >
                        Review
                      </ActionButton>
                      <ActionButton
                        disabled={busy === row.id}
                        onClick={() => setReviewing({ type: 'reject', row })}
                        label={`Reject intake ${row.id}`}
                      >
                        Reject
                      </ActionButton>
                      <ActionButton disabled={busy === row.id} onClick={() => act(row.id, () => cancelIntake(row.id))} label={`Cancel intake ${row.id}`}>Cancel</ActionButton>
                    </>
                  )}
                  {status === 'accepted' && (
                    <>
                      <select
                        aria-label={`Aggregation batch for intake ${row.id}`}
                        value={assignments[row.id] || ''}
                        onChange={event => setAssignments(current => ({ ...current, [row.id]: event.target.value }))}
                      >
                        <option value="">Choose batch…</option>
                        {batchOptions.map(option => <option value={option.value} key={option.value}>{option.label}</option>)}
                      </select>
                      <ActionButton
                        disabled={!assignments[row.id] || busy === row.id}
                        onClick={() => act(row.id, () => assignIntake(row.id, assignments[row.id]))}
                        label={`Assign intake ${row.id} to batch`}
                      >
                        Assign
                      </ActionButton>
                    </>
                  )}
                </div>
              )
            },
          },
        ]}
      >
        <button type="button" className="btn-nav" onClick={() => setShowForm(current => !current)}>
          {showForm ? 'Cancel' : 'Record intake'}
        </button>
      </CommerceTable>
    </>
  )
}
