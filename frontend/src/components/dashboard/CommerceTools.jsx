import React, { useState } from 'react'
import { exportDashboardReport } from '../../api/reports'
import { DashboardPagination, DashboardTableToolbar, useDashboardTable } from './DashboardTableTools'

export const fieldStyle = {
  width: '100%',
  padding: '9px 10px',
  border: '1px solid var(--border)',
  borderRadius: 8,
  font: 'inherit',
  boxSizing: 'border-box',
}

export function money(value) {
  const amount = Number(value)
  return Number.isFinite(amount)
    ? `GHS ${amount.toLocaleString('en-GH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : '—'
}

export function dateText(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleDateString('en-GH')
}

export function statusOf(row) {
  const value = row.status || row.state || (row.is_active === true ? 'active' : row.is_active === false ? 'inactive' : 'pending')
  return String(value).toLowerCase()
}

export function StatusBadge({ status }) {
  const value = String(status || 'pending').toLowerCase()
  const green = ['accepted', 'active', 'batched', 'closed', 'confirmed', 'funded', 'verified', 'approved', 'paid', 'completed', 'success']
  const red = ['rejected', 'failed', 'cancelled']
  const color = green.includes(value) ? 'bdg-green' : red.includes(value) ? 'bdg-red' : 'bdg-amber'
  return <span className={`bdg ${color}`}>{value.replaceAll('_', ' ')}</span>
}

export function downloadCsv(label, rows) {
  const keys = [...new Set(rows.flatMap(row => Object.keys(row)))]
  const escape = value => `"${String(value ?? '').replaceAll('"', '""')}"`
  const csv = [keys.map(escape), ...rows.map(row => keys.map(key => escape(
    typeof row[key] === 'object' ? JSON.stringify(row[key]) : row[key],
  )))].map(columns => columns.join(',')).join('\n')
  const url = window.URL.createObjectURL(new window.Blob([csv], { type: 'text/csv' }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `${label.toLowerCase().replaceAll(' ', '-')}.csv`
  anchor.click()
  window.URL.revokeObjectURL(url)
}

const defaultSearchableText = row => Object.values(row).join(' ')
const defaultDateValue = row => row.created_at || row.date

export function CommerceTable({
  label,
  rows,
  columns,
  statuses,
  empty,
  children,
  searchableText = defaultSearchableText,
  dateValue = defaultDateValue,
  report,
  cooperativeId,
}) {
  const table = useDashboardTable({ rows, searchableText, statusValue: statusOf, dateValue })

  return (
    <>
      <DashboardTableToolbar
        label={label}
        table={table}
        statuses={statuses}
        onExport={() => (
          report
            ? exportDashboardReport(report, cooperativeId, table.exportFilters)
            : downloadCsv(label, table.filteredRows)
        )}
      >
        {children}
      </DashboardTableToolbar>
      <div className="admin-card">
        <div className="admin-card-head">
          <span className="admin-card-title">{label}</span>
          <span className="admin-card-action">{rows.length} records</span>
        </div>
        {table.filteredRows.length === 0 ? (
          <div className="dashboard-empty">{rows.length ? 'No records match the current filters.' : empty}</div>
        ) : (
          <div className="table-scroll">
            <div className="pay-head" style={{ gridTemplateColumns: columns.map(column => column.width || '1fr').join(' ') }}>
              {columns.map(column => <span className="pt-lbl" key={column.label}>{column.label}</span>)}
            </div>
            {table.pageRows.map((row, index) => (
              <div
                className="pay-row"
                style={{ gridTemplateColumns: columns.map(column => column.width || '1fr').join(' ') }}
                key={row.id ?? index}
              >
                {columns.map(column => <div key={column.label}>{column.render(row)}</div>)}
              </div>
            ))}
          </div>
        )}
        <DashboardPagination label={label} table={table} />
      </div>
    </>
  )
}

export function InlineForm({ title, fields, initial, submitLabel, onSubmit }) {
  const [values, setValues] = useState(initial)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await onSubmit(values)
      setValues(initial)
    } catch (reason) {
      setError(reason.message || `Could not ${submitLabel.toLowerCase()}.`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="admin-card" onSubmit={submit} style={{ padding: 18, marginBottom: 20 }}>
      <div className="admin-card-title" style={{ marginBottom: 14 }}>{title}</div>
      {error && <div className="dashboard-inline-error" role="alert">{error}</div>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 10 }}>
        {fields.map(field => (
          <label key={field.name} style={{ fontSize: 12, fontWeight: 600 }}>
            {field.label}
            {field.type === 'select' ? (
              <select
                aria-label={field.label}
                style={fieldStyle}
                value={values[field.name]}
                onChange={event => setValues(current => ({ ...current, [field.name]: event.target.value }))}
                required={field.required !== false}
              >
                <option value="">Select…</option>
                {field.options.map(option => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            ) : (
              <input
                aria-label={field.label}
                style={fieldStyle}
                type={field.type || 'text'}
                min={field.min}
                step={field.step}
                value={values[field.name]}
                onChange={event => setValues(current => ({ ...current, [field.name]: event.target.value }))}
                required={field.required !== false}
              />
            )}
          </label>
        ))}
      </div>
      <button className="btn-nav" type="submit" disabled={busy} style={{ marginTop: 14 }}>
        {busy ? 'Working…' : submitLabel}
      </button>
    </form>
  )
}

export function ActionButton({ children, onClick, disabled, label }) {
  return (
    <button type="button" className="table-row-action" onClick={onClick} disabled={disabled} aria-label={label}>
      {children}
    </button>
  )
}
