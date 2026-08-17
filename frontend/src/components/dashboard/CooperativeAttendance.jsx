import { useEffect, useState } from 'react'
import { CheckSquare, Square } from 'lucide-react'
import { API_URL, authHeaders, fetchJson } from '../../api/config'
import DashboardPagination from './DashboardPagination'

const PAGE_SIZE = 20

export default function CooperativeAttendance({ cooperativeId, farmers = [] }) {
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(0)
  const [submitting, setSubmitting] = useState(false)

  const [eventName, setEventName] = useState('')
  const [eventDate, setEventDate] = useState('')
  const [attendanceMap, setAttendanceMap] = useState({})

  useEffect(() => {
    if (!cooperativeId) return
    setLoading(true)
    setError(null)
    const fetchRecent = async () => {
      try {
        const ids = farmers.map(f => f.id).filter(Boolean)
        if (ids.length === 0) { setRecords([]); return }
        const allRecords = await Promise.all(
          ids.map(id =>
            fetchJson(
              `${API_URL}/farmers/${id}/attendance?cooperative_id=${cooperativeId}&limit=5`,
              { headers: authHeaders() },
            )
          ),
        )
        const merged = allRecords.flat().sort((a, b) => {
          const dateA = a.event_date || a.date || ''
          const dateB = b.event_date || b.date || ''
          return dateB.localeCompare(dateA)
        })
        setRecords(merged)
      } catch (err) {
        setError(err)
      } finally {
        setLoading(false)
      }
    }
    fetchRecent()
  }, [cooperativeId, farmers])

  useEffect(() => {
    if (farmers.length > 0) {
      const map = {}
      farmers.forEach(f => { map[f.id] = false })
      setAttendanceMap(map)
    }
  }, [farmers])

  const pageCount = Math.ceil(records.length / PAGE_SIZE)
  const paged = records.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  function toggleFarmer(id) {
    setAttendanceMap(prev => ({ ...prev, [id]: !prev[id] }))
  }

  function markAllPresent() {
    const map = {}
    farmers.forEach(f => { map[f.id] = true })
    setAttendanceMap(map)
  }

  function markAllAbsent() {
    const map = {}
    farmers.forEach(f => { map[f.id] = false })
    setAttendanceMap(map)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!eventDate || !eventName.trim()) return

    setSubmitting(true)
    const checked = Object.entries(attendanceMap)
      .filter(([, attended]) => attended)
      .map(([id]) => parseInt(id, 10))

    try {
      await Promise.all(farmers.map(async (farmer) => {
        const farmerId = farmer.id
        if (!checked.includes(farmerId) && !Object.prototype.hasOwnProperty.call(attendanceMap, farmerId)) return
        const attended = checked.includes(farmerId)
        await fetchJson(`${API_URL}/farmers/${farmerId}/attendance?cooperative_id=${cooperativeId}`, {
          method: 'POST',
          headers: authHeaders(true),
          body: JSON.stringify({
            cooperative_id: cooperativeId,
            farmer_id: farmerId,
            event_name: eventName.trim(),
            event_date: eventDate,
            attended,
          }),
        })
      }))

      setEventName('')
      setEventDate('')
      const map = {}
      farmers.forEach(f => { map[f.id] = false })
      setAttendanceMap(map)
      setLoading(true)
      try {
        const ids = farmers.map(f => f.id).filter(Boolean)
        if (ids.length > 0) {
          const allRecords = await Promise.all(
            ids.map(id =>
              fetchJson(
                `${API_URL}/farmers/${id}/attendance?cooperative_id=${cooperativeId}&limit=5`,
                { headers: authHeaders() },
              )
            ),
          )
          const merged = allRecords.flat().sort((a, b) => {
            const dateA = a.event_date || a.date || ''
            const dateB = b.event_date || b.date || ''
            return dateB.localeCompare(dateA)
          })
          setRecords(merged)
        }
      } catch (err) {
        setError(err)
      } finally {
        setLoading(false)
      }
    } catch (err) {
      alert(err.message || 'Failed to log attendance')
    } finally {
      setSubmitting(false)
    }
  }

  const farmerMap = Object.fromEntries(farmers.map(f => [f.id, f]))
  const checkedCount = Object.values(attendanceMap).filter(Boolean).length

  if (loading && records.length === 0 && farmers.length === 0) {
    return <div className="skeleton-box" style={{ height: 400 }} />
  }

  return (
    <div>
      {error && (
        <div className="error-banner" role="alert" style={{ marginBottom: 16 }}>
          Failed to load attendance records
        </div>
      )}

      <div className="section-card" style={{ marginBottom: 24 }}>
        <div className="section-header">
          <h2>Log meeting attendance</h2>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: '0 20px 20px' }}>
          <div style={{ display: 'flex', gap: 16, marginBottom: 16, flexWrap: 'wrap' }}>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 13 }}>
              Event date
              <input
                type="date"
                value={eventDate}
                onChange={e => setEventDate(e.target.value)}
                required
                style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid var(--border)', fontSize: 13 }}
              />
            </label>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 13, flex: 1, minWidth: 200 }}>
              Event name
              <input
                type="text"
                placeholder="e.g. Monthly General Meeting"
                value={eventName}
                onChange={e => setEventName(e.target.value)}
                required
                style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid var(--border)', fontSize: 13 }}
              />
            </label>
          </div>

          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <button type="button" className="btn-nav" style={{ fontSize: 12, padding: '5px 12px' }} onClick={markAllPresent}>
              Mark all present
            </button>
            <button type="button" className="btn-nav" style={{ fontSize: 12, padding: '5px 12px' }} onClick={markAllAbsent}>
              Mark all absent
            </button>
            <span style={{ fontSize: 12, color: 'var(--muted)', alignSelf: 'center', marginLeft: 8 }}>
              {checkedCount} of {farmers.length} present
            </span>
          </div>

          <div style={{ maxHeight: 300, overflowY: 'auto', border: '1px solid var(--border)', borderRadius: 8, marginBottom: 16 }}>
            {farmers.length === 0 ? (
              <div style={{ padding: 32, textAlign: 'center', color: 'var(--muted)' }}>
                No members in this cooperative yet.
              </div>
            ) : (
              farmers.map(farmer => (
                <label
                  key={farmer.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '10px 14px',
                    borderBottom: '1px solid var(--border)',
                    cursor: 'pointer',
                    fontSize: 13,
                  }}
                >
                  {attendanceMap[farmer.id]
                    ? <CheckSquare size={18} color="var(--g)" aria-hidden="true" />
                    : <Square size={18} color="var(--muted)" aria-hidden="true" />
                  }
                  <input
                    type="checkbox"
                    checked={attendanceMap[farmer.id] || false}
                    onChange={() => toggleFarmer(farmer.id)}
                    className="sr-only"
                  />
                  <span style={{ flex: 1 }}>
                    <strong>{farmer.name}</strong>
                    {farmer.phone && <span style={{ color: 'var(--muted)', marginLeft: 8 }}>{farmer.phone}</span>}
                  </span>
                </label>
              ))
            )}
          </div>

          <button type="submit" className="btn-lg" disabled={submitting || !eventDate || !eventName.trim()}>
            {submitting ? 'Logging…' : 'Log attendance'}
          </button>
        </form>
      </div>

      <div className="admin-card">
        <div className="section-header">
          <h2>Recent attendance records</h2>
        </div>

        {loading ? (
          <div className="skeleton-box" style={{ height: 200, margin: 20 }} />
        ) : (
          <>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Event</th>
                  <th>Member</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {paged.map((r, i) => {
                  const farmer = farmerMap[r.farmer_id]
                  return (
                    <tr key={r.id || i}>
                      <td>{r.event_date || r.date || '—'}</td>
                      <td>{r.event_name || '—'}</td>
                      <td>{farmer?.name ?? `Member #${r.farmer_id}`}</td>
                      <td>
                        <span className={r.attended ? 'bdg bdg-green' : 'bdg bdg-red'}>
                          {r.attended ? 'Present' : 'Absent'}
                        </span>
                      </td>
                    </tr>
                  )
                })}
                {paged.length === 0 && (
                  <tr>
                    <td colSpan={4} className="empty-state">No attendance records yet</td>
                  </tr>
                )}
              </tbody>
            </table>
            <DashboardPagination
              page={page}
              pageCount={pageCount}
              onPage={setPage}
              total={records.length}
              rangeStart={page * PAGE_SIZE + 1}
              rangeEnd={Math.min((page + 1) * PAGE_SIZE, records.length)}
            />
          </>
        )}
      </div>
    </div>
  )
}
