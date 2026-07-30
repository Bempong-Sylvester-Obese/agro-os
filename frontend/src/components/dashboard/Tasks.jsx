import { useEffect, useState } from 'react'
import { Plus, Pencil, XCircle, CheckCircle } from 'lucide-react'
import { fetchTasks, updateTask } from '../../api/tasks'
import DashboardTableToolbar from './DashboardTableToolbar'
import DashboardPagination from './DashboardPagination'
import TaskForm from './TaskForm'
import ModalPresence from './ModalPresence'

const PAGE_SIZE = 20

const STATUS_CONFIG = {
  open: { label: 'Open', className: 'status-open' },
  in_progress: { label: 'In Progress', className: 'status-in_progress' },
  completed: { label: 'Completed', className: 'status-completed' },
  cancelled: { label: 'Cancelled', className: 'status-cancelled' },
}

export default function Tasks({ cooperativeId }) {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [editingTask, setEditingTask] = useState(null)
  const [page, setPage] = useState(0)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  function loadTasks() {
    if (!cooperativeId) return
    setLoading(true)
    fetchTasks(cooperativeId, statusFilter || undefined)
      .then(setTasks)
      .catch(setError)
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadTasks() }, [cooperativeId, statusFilter])

  useEffect(() => { setPage(0) }, [search, statusFilter])

  const filtered = tasks.filter(t =>
    !search || t.title.toLowerCase().includes(search.toLowerCase())
  )
  const pageCount = Math.ceil(filtered.length / PAGE_SIZE)
  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  async function handleStatusChange(taskId, status) {
    try {
      await updateTask(cooperativeId, taskId, { status })
      loadTasks()
    } catch (e) { alert(e.message) }
  }

  if (loading) return <div className="skeleton-box" style={{ height: 400 }} />
  if (error) return <div className="error-banner">Failed to load tasks</div>

  return (
    <div className="section-card">
      <div className="section-header">
        <h2>Tasks ({tasks.length})</h2>
        <button className="btn btn-primary" onClick={() => { setEditingTask(null); setShowForm(true) }}>
          <Plus size={16} /> Create Task
        </button>
      </div>

      <div className="dashboard-table-toolbar">
        <div className="dashboard-table-filters">
          <DashboardTableToolbar search={search} onSearch={setSearch} />
          <select className="form-input" value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}>
            <option value="">All statuses</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Type</th>
            <th>Status</th>
            <th>Scheduled Date</th>
            <th>Assigned Workers</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {paged.map(t => (
            <tr key={t.id}>
              <td>{t.title}</td>
              <td><span className="badge">{t.task_type}</span></td>
              <td>
                <span className={`status-badge ${STATUS_CONFIG[t.status]?.className || ''}`}>
                  {STATUS_CONFIG[t.status]?.label || t.status}
                </span>
              </td>
              <td>{t.scheduled_date ? new Date(t.scheduled_date).toLocaleDateString() : '—'}</td>
              <td>{t.assigned_workers?.length ?? 0}</td>
              <td className="actions-cell">
                <button className="btn-icon" title="Edit"
                  onClick={() => { setEditingTask(t); setShowForm(true) }}>
                  <Pencil size={15} />
                </button>
                {t.status !== 'completed' && t.status !== 'cancelled' && (
                  <>
                    <button className="btn-icon" title="Mark Complete"
                      onClick={() => handleStatusChange(t.id, 'completed')}>
                      <CheckCircle size={15} />
                    </button>
                    <button className="btn-icon btn-icon-danger" title="Cancel"
                      onClick={() => handleStatusChange(t.id, 'cancelled')}>
                      <XCircle size={15} />
                    </button>
                  </>
                )}
              </td>
            </tr>
          ))}
          {paged.length === 0 && (
            <tr><td colSpan={6} className="empty-state">No tasks yet</td></tr>
          )}
        </tbody>
      </table>

      <DashboardPagination page={page} pageCount={pageCount} onPage={setPage} total={filtered.length}
        rangeStart={page * PAGE_SIZE + 1} rangeEnd={Math.min((page + 1) * PAGE_SIZE, filtered.length)} />

      <ModalPresence show={showForm} onClose={() => setShowForm(false)}>
        <TaskForm
          cooperativeId={cooperativeId}
          task={editingTask}
          onSaved={() => { setShowForm(false); loadTasks() }}
          onCancel={() => setShowForm(false)}
        />
      </ModalPresence>
    </div>
  )
}
