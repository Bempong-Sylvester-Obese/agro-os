import { useEffect, useState } from 'react'
import { createTask, updateTask, assignWorkers } from '../../api/tasks'
import { fetchWorkers } from '../../api/workers'

export default function TaskForm({ cooperativeId, task, onSaved, onCancel }) {
  const isEdit = !!task
  const [form, setForm] = useState({
    title: task?.title || '',
    description: task?.description || '',
    task_type: task?.task_type || 'general',
    location: task?.location || '',
    scheduled_date: task?.scheduled_date || '',
    status: task?.status || 'open',
  })
  const [workerIds, setWorkerIds] = useState(task?.assignments?.map(a => a.worker_id) || [])
  const [workers, setWorkers] = useState([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchWorkers(cooperativeId).then(setWorkers).catch(() => {})
  }, [cooperativeId])

  function toggleWorker(id) {
    setWorkerIds(prev =>
      prev.includes(id) ? prev.filter(w => w !== id) : [...prev, id]
    )
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const payload = {
        title: form.title,
        description: form.description,
        task_type: form.task_type,
        location: form.location,
        scheduled_date: form.scheduled_date,
      }
      if (isEdit) {
        const editPayload = {
          title: form.title,
          description: form.description,
          location: form.location,
          scheduled_date: form.scheduled_date,
          status: form.status,
        }
        await updateTask(cooperativeId, task.id, editPayload)
        const currentIds = task.assignments?.map(a => a.worker_id) || []
        const changed = currentIds.length !== workerIds.length ||
          currentIds.some(id => !workerIds.includes(id)) ||
          workerIds.some(id => !currentIds.includes(id))
        if (changed) {
          await assignWorkers(cooperativeId, task.id, workerIds)
        }
      } else {
        const created = await createTask(cooperativeId, payload)
        if (workerIds.length > 0) {
          await assignWorkers(cooperativeId, created.id, workerIds)
        }
      }
      onSaved()
    } catch (e) { setError(e.message) }
    finally { setSaving(false) }
  }

  return (
    <div className="modal-content">
      <h2>{isEdit ? 'Edit Task' : 'Create Task'}</h2>
      {error && <div className="error-banner">{error}</div>}
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Title</label>
          <input className="form-input" required value={form.title}
            onChange={e => setForm({...form, title: e.target.value})} />
        </div>
        <div className="form-group">
          <label>Description</label>
          <textarea className="form-input" rows={3} value={form.description}
            onChange={e => setForm({...form, description: e.target.value})} />
        </div>
        <div className="form-group">
          <label>Task type</label>
          {isEdit ? (
            <input className="form-input" value={form.task_type} disabled />
          ) : (
            <select className="form-input" value={form.task_type}
              onChange={e => setForm({...form, task_type: e.target.value})}>
              <option value="general">General</option>
              <option value="planting">Planting</option>
              <option value="weeding">Weeding</option>
              <option value="harvesting">Harvesting</option>
              <option value="irrigation">Irrigation</option>
              <option value="fertilizing">Fertilizing</option>
            </select>
          )}
        </div>
        <div className="form-group">
          <label>Location</label>
          <input className="form-input" value={form.location}
            onChange={e => setForm({...form, location: e.target.value})} />
        </div>
        <div className="form-group">
          <label>Scheduled date</label>
          <input className="form-input" type="date" required value={form.scheduled_date}
            onChange={e => setForm({...form, scheduled_date: e.target.value})} />
        </div>
        {isEdit && (
          <div className="form-group">
            <label>Status</label>
            <select className="form-input" value={form.status}
              onChange={e => setForm({...form, status: e.target.value})}>
              <option value="open">Open</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
        )}
        <div className="form-group">
          <label>Assign workers ({workerIds.length} selected)</label>
          <div className="checkbox-list">
            {workers.map(w => (
              <label key={w.id} className="checkbox-label">
                <input type="checkbox" checked={workerIds.includes(w.id)}
                  onChange={() => toggleWorker(w.id)} />
                {w.name}
              </label>
            ))}
            {workers.length === 0 && <span className="empty-state">No workers available</span>}
          </div>
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
