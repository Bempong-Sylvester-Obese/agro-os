import { useEffect, useState } from 'react'
import { Plus, Pencil } from 'lucide-react'
import { fetchFarmProductions, createFarmProduction, updateFarmProduction } from '../../api/farm_production'
import DashboardTableToolbar from './DashboardTableToolbar'
import DashboardPagination from './DashboardPagination'
import ModalPresence from './ModalPresence'

const PAGE_SIZE = 20

export default function FarmProduction({ cooperativeId }) {
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [page, setPage] = useState(0)
  const [search, setSearch] = useState('')

  function load() {
    if (!cooperativeId) return
    setLoading(true)
    fetchFarmProductions(cooperativeId)
      .then(setRecords)
      .catch(setError)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [cooperativeId])

  useEffect(() => { setPage(0) }, [search])

  const filtered = records.filter(r =>
    !search || r.crop_type.toLowerCase().includes(search.toLowerCase())
  )
  const pageCount = Math.ceil(filtered.length / PAGE_SIZE)
  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  const totalExpected = records.reduce((s, r) => s + (r.expected_quantity_kg || 0), 0)
  const totalActual = records.reduce((s, r) => s + (r.actual_quantity_kg || 0), 0)

  if (loading) return <div className="skeleton-box" style={{ height: 400 }} />
  if (error) return <div className="error-banner">Failed to load farm production records</div>

  return (
    <div className="section-card">
      <div className="section-header">
        <h2>Farm Production ({records.length})</h2>
        <button className="btn btn-primary" onClick={() => { setEditing(null); setShowForm(true) }}>
          <Plus size={16} /> Add Record
        </button>
      </div>

      <div className="pay-stats">
        <div className="stat-card">
          <div className="stat-lbl">Total expected (kg)</div>
          <div className="stat-val serif">{totalExpected.toLocaleString()}</div>
          <div className="stat-sub">Across all seasons</div>
        </div>
        <div className="stat-card">
          <div className="stat-lbl">Total harvested (kg)</div>
          <div className="stat-val serif">{totalActual > 0 ? totalActual.toLocaleString() : '—'}</div>
          <div className="stat-sub">Actual yield recorded</div>
        </div>
        <div className="stat-card">
          <div className="stat-lbl">Active seasons</div>
          <div className="stat-val serif">{new Set(records.map(r => r.season)).size}</div>
          <div className="stat-sub">Unique growing seasons</div>
        </div>
      </div>

      <div className="dashboard-table-toolbar">
        <DashboardTableToolbar search={search} onSearch={setSearch} placeholder="Search by crop type..." />
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th>Crop Type</th>
            <th>Season</th>
            <th>Planted Date</th>
            <th>Harvest Date</th>
            <th>Expected (kg)</th>
            <th>Actual (kg)</th>
            <th>Quality Grade</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {paged.map(r => (
            <tr key={r.id}>
              <td><span className="badge">{r.crop_type}</span></td>
              <td>{r.season}</td>
              <td>{r.planted_date ? new Date(r.planted_date).toLocaleDateString() : '—'}</td>
              <td>{r.actual_harvest_date ? new Date(r.actual_harvest_date).toLocaleDateString() : r.expected_harvest_date ? new Date(r.expected_harvest_date).toLocaleDateString() : '—'}</td>
              <td>{r.expected_quantity_kg?.toLocaleString()}</td>
              <td>{r.actual_quantity_kg != null ? r.actual_quantity_kg.toLocaleString() : '—'}</td>
              <td>{r.quality_grade || '—'}</td>
              <td className="actions-cell">
                <button className="btn-icon" title="Edit"
                  onClick={() => { setEditing(r); setShowForm(true) }}>
                  <Pencil size={15} />
                </button>
              </td>
            </tr>
          ))}
          {paged.length === 0 && (
            <tr><td colSpan={8} className="empty-state">No production records yet</td></tr>
          )}
        </tbody>
      </table>

      <DashboardPagination page={page} pageCount={pageCount} onPage={setPage} total={filtered.length}
        rangeStart={page * PAGE_SIZE + 1} rangeEnd={Math.min((page + 1) * PAGE_SIZE, filtered.length)} />

      <ModalPresence show={showForm} onClose={() => setShowForm(false)}>
        <FarmProductionForm
          cooperativeId={cooperativeId}
          record={editing}
          onSaved={() => { setShowForm(false); load() }}
          onCancel={() => setShowForm(false)}
        />
      </ModalPresence>
    </div>
  )
}

function FarmProductionForm({ cooperativeId, record, onSaved, onCancel }) {
  const isEdit = !!record
  const [form, setForm] = useState({
    crop_type: record?.crop_type || '',
    season: record?.season || '',
    location: record?.location || '',
    planted_date: record?.planted_date || '',
    expected_harvest_date: record?.expected_harvest_date || '',
    actual_harvest_date: record?.actual_harvest_date || '',
    expected_quantity_kg: record?.expected_quantity_kg || '',
    actual_quantity_kg: record?.actual_quantity_kg || '',
    quality_grade: record?.quality_grade || '',
    notes: record?.notes || '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  function set(field, value) {
    setForm(prev => ({ ...prev, [field]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const payload = {
        crop_type: form.crop_type,
        season: form.season,
        location: form.location || undefined,
        planted_date: form.planted_date,
        expected_harvest_date: form.expected_harvest_date || undefined,
        actual_harvest_date: form.actual_harvest_date || undefined,
        expected_quantity_kg: parseFloat(form.expected_quantity_kg),
        actual_quantity_kg: form.actual_quantity_kg ? parseFloat(form.actual_quantity_kg) : undefined,
        quality_grade: form.quality_grade || undefined,
        notes: form.notes || undefined,
      }
      if (isEdit) {
        await updateFarmProduction(cooperativeId, record.id, payload)
      } else {
        await createFarmProduction(cooperativeId, payload)
      }
      onSaved()
    } catch (err) { setError(err.message) }
    finally { setSaving(false) }
  }

  return (
    <div className="modal-content">
      <h2>{isEdit ? 'Edit Production Record' : 'Add Production Record'}</h2>
      {error && <div className="error-banner">{error}</div>}
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Crop Type</label>
          <input className="form-input" required value={form.crop_type}
            onChange={e => set('crop_type', e.target.value)} />
        </div>
        <div className="form-group">
          <label>Season</label>
          <input className="form-input" required value={form.season}
            onChange={e => set('season', e.target.value)} placeholder="e.g. 2026A, Long Rains" />
        </div>
        <div className="form-row">
          <div className="form-group">
            <label>Planted Date</label>
            <input className="form-input" type="date" required value={form.planted_date}
              onChange={e => set('planted_date', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Expected Harvest Date</label>
            <input className="form-input" type="date" value={form.expected_harvest_date}
              onChange={e => set('expected_harvest_date', e.target.value)} />
          </div>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label>Expected Quantity (kg)</label>
            <input className="form-input" type="number" min="0" step="0.1" required value={form.expected_quantity_kg}
              onChange={e => set('expected_quantity_kg', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Actual Quantity (kg)</label>
            <input className="form-input" type="number" min="0" step="0.1" value={form.actual_quantity_kg}
              onChange={e => set('actual_quantity_kg', e.target.value)} />
          </div>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label>Actual Harvest Date</label>
            <input className="form-input" type="date" value={form.actual_harvest_date}
              onChange={e => set('actual_harvest_date', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Quality Grade</label>
            <select className="form-input" value={form.quality_grade}
              onChange={e => set('quality_grade', e.target.value)}>
              <option value="">—</option>
              <option value="A">A (Premium)</option>
              <option value="B">B (Standard)</option>
              <option value="C">C (Sub-grade)</option>
            </select>
          </div>
        </div>
        <div className="form-group">
          <label>Location (optional)</label>
          <input className="form-input" value={form.location}
            onChange={e => set('location', e.target.value)} placeholder="e.g. Field 3, North Block" />
        </div>
        <div className="form-group">
          <label>Notes (optional)</label>
          <textarea className="form-input" rows={3} value={form.notes}
            onChange={e => set('notes', e.target.value)} />
        </div>
        <div className="form-actions">
          <button type="button" className="btn btn-secondary" onClick={onCancel}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Saving...' : isEdit ? 'Update' : 'Create'}
          </button>
        </div>
      </form>
    </div>
  )
}
