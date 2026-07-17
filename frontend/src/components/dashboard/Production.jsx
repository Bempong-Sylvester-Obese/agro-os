import React, { useCallback, useMemo, useState } from 'react'
import { Loader2, Plus, X } from 'lucide-react'
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
import { DashboardPagination, DashboardTableToolbar, useDashboardTable } from './DashboardTableTools'
import { useModal } from '../../hooks/useModal'
import { ModalPresence } from '../Motion'

function formatProductionDate(record) {
  const value = productionDate(record)
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })
}

function LogProductionModal({ farmers, onClose, onSuccess }) {
  const { onBackdropClick, dialogProps, titleId, closeButtonProps } = useModal(onClose, { label: 'production dialog' })
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
      setError('Please fill in all fields.')
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

  const input = {
    width: '100%',
    padding: '10px 12px',
    border: '1.5px solid var(--border)',
    borderRadius: 8,
    fontSize: 14,
    fontFamily: "'DM Sans', sans-serif",
    outline: 'none',
    background: '#fff',
    color: 'var(--text)',
    boxSizing: 'border-box',
    marginTop: 6,
  }
  const kindLabel = kind === 'animal' ? 'Animal' : 'Crop'

  return (
    <div className="dashboard-modal-overlay" onClick={onBackdropClick}>
      <div className="dashboard-modal" {...dialogProps} style={{ maxWidth: 500 }}>
        <div className="dashboard-modal-head">
          <div>
            <div id={titleId} className="serif">Log production</div>
            <div className="pt-id">Record a member&apos;s crop or animal output</div>
          </div>
          <button {...closeButtonProps} onClick={onClose} className="dashboard-icon-close"><X size={20} /></button>
        </div>
        <form onSubmit={handleSubmit} className="dashboard-modal-body">
          {error && <div role="alert" className="dashboard-form-error">{error}</div>}
          <div style={{ marginBottom: 16 }}>
            <label htmlFor="production-member" style={{ fontSize: 13, fontWeight: 600 }}>Member</label>
            <select id="production-member" style={input} value={form.farmerId} onChange={selectFarmer} required disabled={loading}>
              <option value="">Select a member...</option>
              {activeFarmers.map(farmer => (
                <option key={farmer.id} value={farmer.id}>{farmer.name} ({farmer.phone})</option>
              ))}
            </select>
          </div>

          {selectedFocus === 'mixed' && (
            <div style={{ marginBottom: 16 }}>
              <label htmlFor="production-kind" style={{ fontSize: 13, fontWeight: 600 }}>Production type</label>
              <select id="production-kind" style={input} value={form.productionKind} onChange={event => {
                setForm(previous => ({ ...previous, productionKind: event.target.value, productName: '', activity: '' }))
              }} required disabled={loading}>
                <option value="">Select crop or animal...</option>
                {PRODUCTION_KIND_OPTIONS.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </div>
          )}

          {kind && (
            <>
              <div className="modal-row" style={{ marginBottom: 16 }}>
                <div>
                  <label htmlFor="production-product" style={{ fontSize: 13, fontWeight: 600 }}>{kindLabel} product</label>
                  <input
                    id="production-product"
                    style={input}
                    value={form.productName}
                    onChange={event => update('productName', event.target.value)}
                    placeholder={kind === 'animal' ? 'e.g. Cattle, Milk, Eggs' : 'e.g. Maize, Cocoa, Rice'}
                    required
                    disabled={loading}
                  />
                </div>
                <div>
                  <label htmlFor="production-activity" style={{ fontSize: 13, fontWeight: 600 }}>Activity / output</label>
                  <select id="production-activity" style={input} value={form.activity} onChange={event => update('activity', event.target.value)} required disabled={loading}>
                    <option value="">Select activity...</option>
                    {activities.map(activity => <option key={activity} value={activity}>{activity}</option>)}
                  </select>
                </div>
              </div>
              <div className="modal-row" style={{ marginBottom: 16 }}>
                <div>
                  <label htmlFor="production-expected" style={{ fontSize: 13, fontWeight: 600 }}>Expected output</label>
                  <input id="production-expected" style={input} type="number" min="0" step="any" value={form.expectedQuantity} onChange={event => update('expectedQuantity', event.target.value)} required disabled={loading} />
                </div>
                <div>
                  <label htmlFor="production-quantity" style={{ fontSize: 13, fontWeight: 600 }}>Actual output</label>
                  <input id="production-quantity" style={input} type="number" min="0" step="any" value={form.quantity} onChange={event => update('quantity', event.target.value)} required disabled={loading} />
                </div>
              </div>
              <div className="modal-row" style={{ marginBottom: 24 }}>
                <div>
                  <label htmlFor="production-unit" style={{ fontSize: 13, fontWeight: 600 }}>Unit</label>
                  <select id="production-unit" style={input} value={form.unit} onChange={event => update('unit', event.target.value)} required disabled={loading}>
                    {PRODUCTION_UNITS.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
                  </select>
                </div>
                <div>
                  <label htmlFor="production-date" style={{ fontSize: 13, fontWeight: 600 }}>Production date</label>
                  <input id="production-date" style={input} type="date" value={form.productionDate} onChange={event => update('productionDate', event.target.value)} required disabled={loading} />
                </div>
              </div>
            </>
          )}

          <button type="submit" className="btn-lg" disabled={loading || !kind} style={{ width: '100%', padding: 12, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 8 }}>
            {loading ? <><Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> Submitting...</> : 'Save production log'}
          </button>
        </form>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
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
        onExport={handleExport}
        exporting={exporting}
        exportError={exportError}
      >
        <button className="btn-nav" onClick={() => setShowModal(true)} style={{ fontSize: 13, padding: '8px 16px', display: 'flex', alignItems: 'center', gap: 6, background: 'var(--text)', color: '#fff' }}>
          <Plus size={15} /> Log production
        </button>
      </DashboardTableToolbar>

      <div className="pay-stats">
        {[
          ['Actual output', formatUnitTotals(actualTotals), 'Totals shown separately by unit'],
          ['Expected output', formatUnitTotals(expectedTotals), 'No incompatible units combined'],
          ['Most logged product', topProduct || '—', topProduct ? `${productCounts[topProduct]} record${productCounts[topProduct] === 1 ? '' : 's'}` : 'No data yet'],
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
          <span className="admin-card-action">{productions.length} record{productions.length === 1 ? '' : 's'}</span>
        </div>
        {table.filteredRows.length === 0 ? (
          <div style={{ padding: '32px 20px', color: 'var(--muted)', fontSize: 14 }}>
            {productions.length === 0 ? 'No production records found. Log crop or animal output to get started.' : 'No production records match the current filters.'}
          </div>
        ) : (
          <div className="table-scroll">
            <div className="pay-head" style={{ gridTemplateColumns: '1.5fr .7fr 1fr 1fr 1fr 1fr' }}>
              {['Member', 'Type', 'Product / activity', 'Expected', 'Actual', 'Date'].map(label => <span key={label} className="pt-lbl">{label}</span>)}
            </div>
            {table.pageRows.map(record => (
              <div key={record.id} className="pay-row" style={{ gridTemplateColumns: '1.5fr .7fr 1fr 1fr 1fr 1fr', alignItems: 'center' }}>
                <div><div className="pt-name">{farmerName(record)}</div><div className="pt-id">#{record.id}</div></div>
                <span className="bdg bdg-green" style={{ textTransform: 'capitalize' }}>{productionKind(record)}</span>
                <span className="pt-m">{productionProduct(record)}<span style={{ display: 'block', fontSize: 11 }}>{productionActivity(record)}</span></span>
                <span className="pt-m">{formatProductionQuantity(productionExpected(record), productionUnit(record))}</span>
                <span className="pt-v">{formatProductionQuantity(productionQuantity(record), productionUnit(record))}</span>
                <span className="pt-m">{formatProductionDate(record)}</span>
              </div>
            ))}
          </div>
        )}
        <DashboardPagination label="Production" table={table} />
      </div>
    </>
  )
}
