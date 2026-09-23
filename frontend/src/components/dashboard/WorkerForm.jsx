import { useState } from 'react'
import { createWorker, updateWorker } from '../../api/workers'
import UpgradePrompt from './UpgradePrompt'

const WAGE_SUFFIX = {
  daily: 'GHS per day',
  shift: 'GHS per shift',
  monthly: 'GHS per month',
}

export default function WorkerForm({ cooperativeId, worker, onSaved, onCancel }) {
  const isEdit = !!worker
  const [form, setForm] = useState({
    name: worker?.name || '',
    phone: worker?.phone || '',
    wage_rate: worker?.wage_rate ?? '',
    role: worker?.role || 'worker',
    hire_date: worker?.hire_date || '',
    pay_type: worker?.pay_type || 'daily',
    user_id: worker?.user_id ?? '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const payload = {
        name: form.name,
        phone: form.phone,
        wage_rate: parseFloat(form.wage_rate) || 0,
        role: form.role,
        pay_type: form.pay_type,
        hire_date: form.hire_date || null,
        user_id: form.user_id === '' ? null : Number(form.user_id),
      }
      if (isEdit) {
        await updateWorker(cooperativeId, worker.id, payload)
      } else {
        await createWorker(cooperativeId, payload)
      }
      onSaved()
    } catch (e) { setError(e) }
    finally { setSaving(false) }
  }

  return (
    <div className="modal-content">
      <h2>{isEdit ? 'Edit worker' : 'Add worker'}</h2>
      <UpgradePrompt error={error} className="error-banner" />
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="worker-name">Name</label>
          <input id="worker-name" className="form-input" required value={form.name}
            onChange={e => setForm({...form, name: e.target.value})} />
        </div>
        <div className="form-group">
          <label htmlFor="worker-phone">Phone</label>
          <input id="worker-phone" className="form-input" required value={form.phone}
            onChange={e => setForm({...form, phone: e.target.value})} />
        </div>
        <div className="form-group">
          <label htmlFor="worker-pay-type">Pay type</label>
          <select id="worker-pay-type" className="form-input" value={form.pay_type}
            onChange={e => setForm({...form, pay_type: e.target.value})}>
            <option value="daily">Daily</option>
            <option value="shift">Shift</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>
        <div className="form-group">
          <label htmlFor="worker-wage">Wage rate ({WAGE_SUFFIX[form.pay_type] || 'GHS'})</label>
          <input id="worker-wage" className="form-input" type="number" step="0.01" min="0" value={form.wage_rate}
            onChange={e => setForm({...form, wage_rate: e.target.value})} />
        </div>
        <div className="form-group">
          <label htmlFor="worker-role">Role</label>
          <select id="worker-role" className="form-input" value={form.role}
            onChange={e => setForm({...form, role: e.target.value})}>
            <option value="worker">Worker</option>
            <option value="supervisor">Supervisor</option>
          </select>
        </div>
        <div className="form-group">
          <label htmlFor="worker-hire-date">Hire date</label>
          <input id="worker-hire-date" className="form-input" type="date" value={form.hire_date}
            onChange={e => setForm({...form, hire_date: e.target.value})} />
        </div>
        <div className="form-group">
          <label htmlFor="worker-user-id">Linked user ID (optional)</label>
          <input id="worker-user-id" className="form-input" type="number" min="1" value={form.user_id}
            onChange={e => setForm({...form, user_id: e.target.value})} />
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
