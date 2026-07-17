import React, { useCallback, useMemo, useState } from 'react'
import { Loader2, Plus } from 'lucide-react'
import { logProduction } from '../../api/production'
import { exportDashboardReport } from '../../api/reports'
import {
  formatProductionQuantity,
  formatUnitTotals,
  productionActivity,
  productionDate,
  productionExpected,
  productionFocus,
  productionKind,
  productionProduct,
  productionQuantity,
  productionUnit,
  PRODUCTION_ACTIVITIES,
  PRODUCTION_KIND_OPTIONS,
  PRODUCTION_UNITS,
  totalsByUnit,
} from '../../utils/production'
import { TableSectionSkeleton } from './DashboardSkeleton'
import DashboardModal, { ModalField } from './DashboardModal'
import { DashboardPagination, DashboardTableToolbar, useDashboardTable } from './DashboardTableTools'
import { ModalPresence } from '../Motion'

function formatProductionDate(record) {
  const value = productionDate(record)
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })
}

function LogProductionModal({ farmers, onClose, onSuccess }) {
  const [form, setForm] = useState({
    farmerId: '',
    productionKind: '',
    productName: '',
    activity: '',
    unit: 'kg',
    expectedQuantity: '',
    quantity: '',
    productionDate: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const activeFarmers = farmers.filter(farmer => farmer.membership_status === 'active')
  const selectedFarmer = activeFarmers.find(farmer => String(farmer.id) === String(form.farmerId))
  const selectedFocus = selectedFarmer ? productionFocus(selectedFarmer) : null
  const kind = selectedFocus === 'mixed' ? form.productionKind : selectedFocus
  const activities = kind ? PRODUCTION_ACTIVITIES[kind] : []
  const kindLabel = kind === 'animal' ? 'Animal' : 'Crop'

  const update = (key, value) => setForm(previous => ({ ...previous, [key]: value }))

  const selectFarmer = event => {
    const farmerId = event.target.value
    const farmer = activeFarmers.find(item => String(item.id) === farmerId)
    const focus = farmer ? productionFocus(farmer) : ''
    setForm(previous => ({
      ...previous,
      farmerId,
      productionKind: focus === 'mixed' ? '' : focus,
      productName: '',
      activity: '',
    }))
  }

  const handleSubmit = async event => {
    event.preventDefault()
    if (!form.farmerId || !kind || !form.productName.trim() || !form.activity || !form.unit || !form.expectedQuantity || !form.quantity || !form.productionDate) {
      setError('Fill in every field before saving this production log.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      await logProduction({ ...form, productionKind: kind })
      onSuccess()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <DashboardModal
      title="Log production"
      subtitle="Record crop harvest or animal output for one cooperative member."
      onClose={onClose}
      closeDisabled={loading}
      closeOnBackdrop={!loading}
      label="production dialog"
      as="form"
      bodyProps={{ onSubmit: handleSubmit }}
    >
      <div className="dashboard-modal-body">
        {error && <div role="alert" className="dashboard-form-error">{error}</div>}

        <ModalField htmlFor="production-member" label="Member">
          <select
            id="production-member"
            className="dashboard-modal-select"
            value={form.farmerId}
            onChange={selectFarmer}
            required
            disabled={loading}
          >
            <option value="">Select a member…</option>
            {activeFarmers.map(farmer => (
              <option key={farmer.id} value={farmer.id}>
                {farmer.name} ({farmer.phone})
              </option>
            ))}
          </select>
        </ModalField>

        {selectedFocus === 'mixed' && (
          <ModalField
            htmlFor="production-kind"
            label="Production type"
            hint="This member grows crops and keeps animals. Choose which output you are logging."
          >
            <select
              id="production-kind"
              className="dashboard-modal-select"
              value={form.productionKind}
              onChange={event => {
                setForm(previous => ({
                  ...previous,
                  productionKind: event.target.value,
                  productName: '',
                  activity: '',
                }))
              }}
              required
              disabled={loading}
            >
              <option value="">Select crop or animal…</option>
              {PRODUCTION_KIND_OPTIONS.map(option => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </ModalField>
        )}

        {kind && (
          <>
            <div className="modal-row">
              <ModalField
                htmlFor="production-product"
                label={`${kindLabel} product`}
                hint={kind === 'animal' ? 'Species or product, such as eggs or milk.' : 'Crop name, such as maize or cocoa.'}
              >
                <input
                  id="production-product"
                  className="dashboard-modal-input"
                  value={form.productName}
                  onChange={event => update('productName', event.target.value)}
                  placeholder={kind === 'animal' ? 'e.g. Eggs, Milk, Cattle' : 'e.g. Maize, Cocoa, Rice'}
                  required
                  disabled={loading}
                />
              </ModalField>
              <ModalField htmlFor="production-activity" label="Activity">
                <select
                  id="production-activity"
                  className="dashboard-modal-select"
                  value={form.activity}
                  onChange={event => update('activity', event.target.value)}
                  required
                  disabled={loading}
                >
                  <option value="">Select activity…</option>
                  {activities.map(activity => (
                    <option key={activity} value={activity}>{activity}</option>
                  ))}
                </select>
              </ModalField>
            </div>

            <div className="modal-row">
              <ModalField htmlFor="production-expected" label="Expected output">
                <input
                  id="production-expected"
                  className="dashboard-modal-input"
                  type="number"
                  min="0"
                  step="any"
                  value={form.expectedQuantity}
                  onChange={event => update('expectedQuantity', event.target.value)}
                  required
                  disabled={loading}
                />
              </ModalField>
              <ModalField htmlFor="production-quantity" label="Actual output">
                <input
                  id="production-quantity"
                  className="dashboard-modal-input"
                  type="number"
                  min="0"
                  step="any"
                  value={form.quantity}
                  onChange={event => update('quantity', event.target.value)}
                  required
                  disabled={loading}
                />
              </ModalField>
            </div>

            <div className="modal-row">
              <ModalField htmlFor="production-unit" label="Unit">
                <select
                  id="production-unit"
                  className="dashboard-modal-select"
                  value={form.unit}
                  onChange={event => update('unit', event.target.value)}
                  required
                  disabled={loading}
                >
                  {PRODUCTION_UNITS.map(option => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </ModalField>
              <ModalField htmlFor="production-date" label="Production date">
                <input
                  id="production-date"
                  className="dashboard-modal-input"
                  type="date"
                  value={form.productionDate}
                  onChange={event => update('productionDate', event.target.value)}
                  required
                  disabled={loading}
                />
              </ModalField>
            </div>
          </>
        )}

        <div className="dashboard-modal-actions">
          <button type="button" className="dashboard-modal-btn-secondary" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button type="submit" className="btn-lg" disabled={loading || !kind}>
            {loading
              ? <><Loader2 size={16} className="spin" /> Saving…</>
              : 'Save production log'}
          </button>
        </div>
      </div>
      <style>{`.spin { animation: spin 1s linear infinite; } @keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </DashboardModal>
  )
}

export default function Production({ farmers = [], productions = [], cooperativeId, loading, onRefresh }) {
  const [showModal, setShowModal] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState('')
  const sorted = useMemo(() => [...productions].sort((left, right) => {
    const leftTime = productionDate(left) ? new Date(productionDate(left)).getTime() : 0
    const rightTime = productionDate(right) ? new Date(productionDate(right)).getTime() : 0
    return (Number.isNaN(rightTime) ? 0 : rightTime) - (Number.isNaN(leftTime) ? 0 : leftTime)
  }), [productions])
  const actualTotals = totalsByUnit(productions, productionQuantity)
  const expectedTotals = totalsByUnit(productions, productionExpected)
  const productCounts = productions.reduce((counts, record) => {
    const product = productionProduct(record)
    if (product !== '—') counts[product] = (counts[product] || 0) + 1
    return counts
  }, {})
  const topProduct = Object.keys(productCounts).sort((left, right) => productCounts[right] - productCounts[left])[0]

  const farmerName = useCallback(
    record => farmers.find(farmer => Number(farmer.id) === Number(record.farmer_id))?.name || `Farmer #${record.farmer_id}`,
    [farmers],
  )
  const searchableText = useCallback(
    record => `${farmerName(record)} ${productionKind(record)} ${productionProduct(record)} ${productionActivity(record)} ${productionUnit(record)}`,
    [farmerName],
  )
  const statusValue = useCallback(record => productionDate(record) ? 'recorded' : 'planned', [])
  const dateValue = useCallback(record => productionDate(record) || record.created_at, [])
  const table = useDashboardTable({ rows: sorted, searchableText, statusValue, dateValue })

  const handleExport = async () => {
    setExporting(true)
    setExportError('')
    try {
      await exportDashboardReport('production', cooperativeId, table.exportFilters)
    } catch (error) {
      setExportError(error.message || 'Could not export production. Please try again.')
    } finally {
      setExporting(false)
    }
  }

  if (loading) {
    return <TableSectionSkeleton statCount={3} rows={6} columns={6} gridStyle={{ gridTemplateColumns: '1.5fr .7fr 1fr 1fr 1fr 1fr' }} />
  }

  return (
    <>
      <ModalPresence show={showModal}>
        <LogProductionModal farmers={farmers} onClose={() => setShowModal(false)} onSuccess={() => {
          setShowModal(false)
          onRefresh?.()
        }} />
      </ModalPresence>
      <DashboardTableToolbar
        label="Production"
        table={table}
        statuses={[
          { value: 'recorded', label: 'Recorded' },
          { value: 'planned', label: 'Planned' },
        ]}
        exporting={exporting}
        onExport={handleExport}
      >
        <button className="btn-nav" onClick={() => setShowModal(true)} style={{ fontSize: 13, padding: '8px 16px', display: 'flex', alignItems: 'center', gap: 6, background: 'var(--text)', color: '#fff' }}>
          <Plus size={15} /> Log production
        </button>
      </DashboardTableToolbar>
      {exportError && <div role="alert" className="dashboard-inline-error">{exportError}</div>}

      <div className="pay-stats">
        {[
          ['Actual output', formatUnitTotals(actualTotals), 'Totals shown separately by unit'],
          ['Expected output', formatUnitTotals(expectedTotals), 'No incompatible units combined'],
          ['Most logged product', topProduct || '—', topProduct ? `${productCounts[topProduct]} record${productCounts[topProduct] === 1 ? '' : 's'}` : 'No logs yet'],
        ].map(([label, value, sub]) => (
          <div key={label} className="stat-card">
            <div className="stat-lbl">{label}</div>
            <div className="stat-val serif" style={{ fontSize: 22 }}>{value}</div>
            <div className="stat-sub">{sub}</div>
          </div>
        ))}
      </div>

      <div className="admin-card">
        <div className="admin-card-head">
          <span className="admin-card-title serif">Production logs</span>
          <span className="admin-card-action">{table.filteredRows.length} record{table.filteredRows.length === 1 ? '' : 's'}</span>
        </div>
        <div className="table-scroll">
          <div className="pay-head" style={{ gridTemplateColumns: '1.5fr .7fr 1fr 1fr 1fr 1fr' }}>
            {['Member', 'Type', 'Product / activity', 'Expected', 'Actual', 'Date'].map(heading => (
              <span key={heading} className="pt-lbl">{heading}</span>
            ))}
          </div>
          {table.pageRows.length === 0 ? (
            <div className="empty-state">{productions.length === 0 ? 'No production records found. Log crop or animal output to get started.' : 'No production records match the current filters.'}</div>
          ) : table.pageRows.map(record => (
            <div key={record.id} className="pay-row" style={{ gridTemplateColumns: '1.5fr .7fr 1fr 1fr 1fr 1fr', alignItems: 'center' }}>
              <div>
                <div className="pt-name">{farmerName(record)}</div>
                <div className="pt-id">#{record.farmer_id}</div>
              </div>
              <span className="bdg bdg-green" style={{ textTransform: 'capitalize' }}>{productionKind(record)}</span>
              <span className="pt-m">
                {productionProduct(record)}
                <span style={{ display: 'block', fontSize: 11 }}>{productionActivity(record)}</span>
              </span>
              <span className="pt-m">{formatProductionQuantity(productionExpected(record), productionUnit(record))}</span>
              <span className="pt-v">{formatProductionQuantity(productionQuantity(record), productionUnit(record))}</span>
              <span className="pt-m">{formatProductionDate(record)}</span>
            </div>
          ))}
        </div>
        <DashboardPagination label="Production" table={table} />
      </div>
      <style>{`.spin { animation: spin 1s linear infinite; } @keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </>
  )
}
