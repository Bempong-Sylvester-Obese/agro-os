import React, { useState } from 'react'
import { createBuyer } from '../../api/commerce'
import { CommerceTable, InlineForm, StatusBadge } from './CommerceTools'
import { TableSectionSkeleton } from './DashboardSkeleton'

export default function Buyers({ buyers = [], cooperativeId, loading, onRefresh }) {
  const [showForm, setShowForm] = useState(false)

  if (loading) return <TableSectionSkeleton statCount={0} rows={6} columns={5} />

  return (
    <>
      {showForm && (
        <InlineForm
          title="Add produce buyer"
          submitLabel="Add buyer"
          initial={{ name: '', phone: '', email: '', address: '' }}
          fields={[
            { name: 'name', label: 'Business name' },
            { name: 'phone', label: 'Phone' },
            { name: 'email', label: 'Email', type: 'email', required: false },
            { name: 'address', label: 'Address', required: false },
          ]}
          onSubmit={async values => {
            await createBuyer(values)
            setShowForm(false)
            await onRefresh?.()
          }}
        />
      )}
      <CommerceTable
        label="Produce buyers"
        report="buyers"
        cooperativeId={cooperativeId}
        rows={buyers}
        empty="No produce buyers have been added."
        statuses={[
          { value: 'active', label: 'Active' },
          { value: 'inactive', label: 'Inactive' },
        ]}
        columns={[
          { label: 'Buyer', width: '1.5fr', render: row => <><div className="pt-name">{row.name || row.business_name}</div><div className="pt-id">#{row.id}</div></> },
          { label: 'Phone', render: row => row.phone || '—' },
          { label: 'Email', width: '1.5fr', render: row => row.email || '—' },
          { label: 'Address', width: '1.5fr', render: row => row.address || '—' },
          { label: 'Status', render: row => <StatusBadge status={row.status || (row.is_active === false ? 'inactive' : 'active')} /> },
        ]}
      >
        <button type="button" className="btn-nav" onClick={() => setShowForm(current => !current)}>
          {showForm ? 'Cancel' : 'Add buyer'}
        </button>
      </CommerceTable>
    </>
  )
}
