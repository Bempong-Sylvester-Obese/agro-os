import { useState } from 'react'
import { createWorker, updateWorker } from '../../api/workers'

export default function WorkerForm({ cooperativeId, worker, onSaved, onCancel }) {
  const isEdit = !!worker
  const [form, setForm] = useState({
    name: worker?.name || '',
    phone: worker?.phone || '',
    wage_rate: worker?.wage_rate ?? '',
    role: worker?.role || 'worker',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const payload = { ...form, wage_rate: parseFloat(form.wage_rate) || 0 }
      if (isEdit) {
        await updateWorker(cooperativeId, worker.id, payload)
      } else {
        await createWorker(cooperativeId, payload)
      }
      onSaved()
    } catch (e) { setError(e.message) }
    finally { setSaving(false) }
  }

  return (
    <div className="modal-content">
      <h2>{isEdit ? 'Edit worker' : 'Add worker'}</h2>
      {error && <div className="error-banner">{error}</div>}
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Name</label>
          <input className="form-input" required value={form.name}
            onChange={e => setForm({...form, name: e.target.value})} />
        </div>
        <div className="form-group">
          <label>Phone</label>
          <input className="form-input" required value={form.phone}
            onChange={e => setForm({...form, phone: e.target.value})} />
        </div>
        <div className="form-group">
          <label>Wage rate (GHS per day)</label>
          <input className="form-input" type="number" step="0.01" min="0" value={form.wage_rate}
            onChange={e => setForm({...form, wage_rate: e.target.value})} />
        </div>
        <div className="form-group">
          <label>Role</label>
          <select className="form-input" value={form.role}
            onChange={e => setForm({...form, role: e.target.value})}>
            <option value="worker">Worker</option>
            <option value="supervisor">Supervisor</option>
          </select>
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
