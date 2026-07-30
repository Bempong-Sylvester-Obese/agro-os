import { useEffect, useState } from 'react'
import { Plus, UserMinus, UserCheck, Pencil } from 'lucide-react'
import { fetchWorkers, deleteWorker } from '../../api/workers'
import DashboardTableToolbar from './DashboardTableToolbar'
import DashboardPagination from './DashboardPagination'
import WorkerForm from './WorkerForm'
import ModalPresence from './ModalPresence'

const PAGE_SIZE = 20

export default function Workers({ cooperativeId }) {
  const [workers, setWorkers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [editingWorker, setEditingWorker] = useState(null)
  const [page, setPage] = useState(0)
  const [search, setSearch] = useState('')

  function loadWorkers() {
    if (!cooperativeId) return
    setLoading(true)
    fetchWorkers(cooperativeId)
      .then(setWorkers)
      .catch(setError)
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadWorkers() }, [cooperativeId])

  const filtered = workers.filter(w =>
    !search || w.name.toLowerCase().includes(search.toLowerCase()) || w.phone.includes(search)
  )
  const pageCount = Math.ceil(filtered.length / PAGE_SIZE)
  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  async function handleDelete(workerId) {
    if (!confirm('Deactivate this worker?')) return
    try {
      await deleteWorker(cooperativeId, workerId)
      loadWorkers()
    } catch (e) { alert(e.message) }
  }

  if (loading) return <div className="skeleton-box" style={{height:400}}/>
  if (error) return <div className="error-banner">Failed to load workers</div>

  return (
    <div className="section-card">
      <div className="section-header">
        <h2>Workers ({workers.length})</h2>
        <button className="btn btn-primary" onClick={() => { setEditingWorker(null); setShowForm(true) }}>
          <Plus size={16} /> Add worker
        </button>
      </div>

      <DashboardTableToolbar search={search} onSearch={setSearch} />

      <table className="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Phone</th>
            <th>Wage rate</th>
            <th>Role</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {paged.map(w => (
            <tr key={w.id}>
              <td>{w.name}</td>
              <td>{w.phone}</td>
              <td>GHS {w.wage_rate?.toFixed(2)}</td>
              <td><span className="badge">{w.role}</span></td>
              <td>{w.status === 'active'
                ? <span className="status-active"><UserCheck size={14} /> Active</span>
                : <span className="status-inactive"><UserMinus size={14} /> Inactive</span>}
              </td>
              <td className="actions-cell">
                <button className="btn-icon" title="Edit" onClick={() => { setEditingWorker(w); setShowForm(true) }}>
                  <Pencil size={15} />
                </button>
                <button className="btn-icon btn-icon-danger" title="Deactivate"
                  onClick={() => handleDelete(w.id)} disabled={w.status === 'inactive'}>
                  <UserMinus size={15} />
                </button>
              </td>
            </tr>
          ))}
          {paged.length === 0 && (
            <tr><td colSpan={6} className="empty-state">No workers yet</td></tr>
          )}
        </tbody>
      </table>

      <DashboardPagination page={page} pageCount={pageCount} onPage={setPage} total={filtered.length}
        rangeStart={page * PAGE_SIZE + 1} rangeEnd={Math.min((page + 1) * PAGE_SIZE, filtered.length)} />

      <ModalPresence show={showForm} onClose={() => setShowForm(false)}>
        <WorkerForm
          cooperativeId={cooperativeId}
          worker={editingWorker}
          onSaved={() => { setShowForm(false); loadWorkers() }}
          onCancel={() => setShowForm(false)}
        />
      </ModalPresence>
    </div>
  )
}
