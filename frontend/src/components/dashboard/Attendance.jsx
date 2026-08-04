import { useEffect, useState } from 'react'
import { fetchAttendance, logAttendance } from '../../api/attendance'
import { fetchWorkers } from '../../api/workers'
import DashboardTableToolbar from './DashboardTableToolbar'
import DashboardPagination from './DashboardPagination'

const PAGE_SIZE = 20
const SHIFT_OPTIONS = ['morning', 'afternoon', 'full_day']

export default function Attendance({ cooperativeId }) {
  const [records, setRecords] = useState([])
  const [workers, setWorkers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(0)

  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [filterWorkerId, setFilterWorkerId] = useState('')

  const [form, setForm] = useState({
    worker_id: '', date: '', shift: 'morning', hours_worked: '', notes: '',
  })
  const [submitting, setSubmitting] = useState(false)

  function load() {
    if (!cooperativeId) return
    setLoading(true)
    setError(null)
    const filters = {}
    if (dateFrom) filters.date_from = dateFrom
    if (dateTo) filters.date_to = dateTo
    if (filterWorkerId) filters.worker_id = filterWorkerId
    Promise.all([
      fetchAttendance(cooperativeId, filters),
      fetchWorkers(cooperativeId),
    ])
      .then(([att, wrk]) => { setRecords(att); setWorkers(wrk) })
      .catch(setError)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [cooperativeId, dateFrom, dateTo, filterWorkerId])

  const pageCount = Math.ceil(records.length / PAGE_SIZE)
  const paged = records.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  const workerMap = Object.fromEntries(workers.map(w => [w.id, w]))

  function resetForm() {
    setForm({ worker_id: '', date: '', shift: 'morning', hours_worked: '', notes: '' })
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.worker_id || !form.date) return
    setSubmitting(true)
    try {
      await logAttendance(cooperativeId, {
        worker_id: parseInt(form.worker_id, 10),
        date: form.date,
        shift: form.shift,
        hours_worked: form.hours_worked ? parseFloat(form.hours_worked) : null,
        notes: form.notes || null,
      })
      resetForm()
      load()
    } catch (err) { alert(err.message) }
    finally { setSubmitting(false) }
  }

  if (loading) return <div className="skeleton-box" style={{ height: 400 }} />
  if (error) return <div className="error-banner">Failed to load attendance</div>

  return (
    <div className="section-card">
      <div className="section-header">
        <h2>Attendance ({records.length})</h2>
      </div>

      <DashboardTableToolbar>
        <label>
          From
          <input type="date" value={dateFrom} onChange={e => { setPage(0); setDateFrom(e.target.value) }} />
        </label>
        <label>
          To
          <input type="date" value={dateTo} onChange={e => { setPage(0); setDateTo(e.target.value) }} />
        </label>
        <label>
          Worker
          <select value={filterWorkerId} onChange={e => { setPage(0); setFilterWorkerId(e.target.value) }}>
            <option value="">All workers</option>
            {workers.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
          </select>
        </label>
      </DashboardTableToolbar>

      <table className="data-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Worker Name</th>
            <th>Task</th>
            <th>Shift</th>
            <th>Hours Worked</th>
            <th>Notes</th>
          </tr>
        </thead>
        <tbody>
          <tr className="inline-form-row">
            <td>
              <input type="date" value={form.date}
                onChange={e => setForm(f => ({ ...f, date: e.target.value }))} required />
            </td>
            <td>
              <select value={form.worker_id}
                onChange={e => setForm(f => ({ ...f, worker_id: e.target.value }))} required>
                <option value="">Select worker</option>
                {workers.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
              </select>
            </td>
            <td>—</td>
            <td>
              <select value={form.shift}
                onChange={e => setForm(f => ({ ...f, shift: e.target.value }))}>
                {SHIFT_OPTIONS.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
              </select>
            </td>
            <td>
              <input type="number" step="0.5" min="0" placeholder="Hours"
                value={form.hours_worked}
                onChange={e => setForm(f => ({ ...f, hours_worked: e.target.value }))} />
            </td>
            <td>
              <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                <input type="text" placeholder="Notes" value={form.notes}
                  onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
                <button className="btn btn-primary btn-sm" onClick={handleSubmit} disabled={submitting}>
                  {submitting ? 'Logging…' : 'Log'}
                </button>
              </div>
            </td>
          </tr>
          {paged.map(r => {
            const worker = workerMap[r.worker_id]
            return (
              <tr key={r.id}>
                <td>{r.date}</td>
                <td>{worker?.name ?? `Worker #${r.worker_id}`}</td>
                <td>{r.work_task_id ? `Task #${r.work_task_id}` : '—'}</td>
                <td><span className="badge">{r.shift.replace('_', ' ')}</span></td>
                <td>{r.hours_worked != null ? r.hours_worked : '—'}</td>
                <td>{r.notes || '—'}</td>
              </tr>
            )
          })}
          {paged.length === 0 && (
            <tr><td colSpan={6} className="empty-state">No attendance records yet</td></tr>
          )}
        </tbody>
      </table>

      <DashboardPagination page={page} pageCount={pageCount} onPage={setPage} total={records.length}
        rangeStart={page * PAGE_SIZE + 1} rangeEnd={Math.min((page + 1) * PAGE_SIZE, records.length)} />
    </div>
  )
}
