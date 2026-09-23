import { useCallback, useEffect, useState } from 'react'
import { CheckSquare, Square } from 'lucide-react'
import { getUserRole } from '../../utils/auth'
import { can } from '../../utils/roles'
import { fetchCooperativeAttendance, recordMeetingAttendance } from '../../api/farmers'
import { formatTransportError } from '../../api/config'
import DashboardPagination from './DashboardPagination'

const PAGE_SIZE = 20

function emptyMap(farmers, value = false) {
  const map = {}
  farmers.forEach((f) => { if (f?.id != null) map[f.id] = value })
  return map
}

/**
 * Meeting attendance for cooperative members (#245).
 *
 * Records one `POST /farmers/{id}/attendance` row per member for a named
 * meeting and lists recent records. Attendance is 15% of the AgroCredit trust
 * score, so `onRecorded` lets the dashboard refresh member data / scores.
 */
export default function CooperativeAttendance({ cooperativeId, farmers = [], onRecorded }) {
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [submitError, setSubmitError] = useState(null)
  const [notice, setNotice] = useState(null)
  const [page, setPage] = useState(0)
  const [submitting, setSubmitting] = useState(false)

  const [eventName, setEventName] = useState('')
  const [eventDate, setEventDate] = useState('')
  const [attendanceMap, setAttendanceMap] = useState({})

  const loadRecords = useCallback(async () => {
    if (!cooperativeId) return
    setLoading(true)
    setError(null)
    try {
      setRecords(await fetchCooperativeAttendance(cooperativeId, farmers.map((f) => f.id)))
    } catch (err) {
      setError(formatTransportError(err))
    } finally {
      setLoading(false)
    }
  }, [cooperativeId, farmers])

  useEffect(() => { loadRecords() }, [loadRecords])

  useEffect(() => {
    if (farmers.length > 0) setAttendanceMap(emptyMap(farmers))
  }, [farmers])

  const pageCount = Math.ceil(records.length / PAGE_SIZE)
  const paged = records.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  function toggleFarmer(id) {
    setAttendanceMap((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  function markAllPresent() { setAttendanceMap(emptyMap(farmers, true)) }
  function markAllAbsent() { setAttendanceMap(emptyMap(farmers, false)) }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!eventDate || !eventName.trim() || farmers.length === 0) return

    setSubmitting(true)
    setSubmitError(null)
    setNotice(null)
    try {
      const { recorded, present } = await recordMeetingAttendance(cooperativeId, attendanceMap, {
        eventName: eventName.trim(),
        eventDate,
      })
      setNotice(`Recorded ${eventName.trim()} on ${eventDate}: ${present} of ${recorded} members present. Trust scores will reflect this on the next recalculation.`)
      setEventName('')
      setEventDate('')
      setAttendanceMap(emptyMap(farmers))
      setPage(0)
      await loadRecords()
      onRecorded?.({ eventName: eventName.trim(), eventDate, recorded, present })
    } catch (err) {
      setSubmitError(formatTransportError(err))
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
        <div className="error-banner" role="alert" style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
          <span>Failed to load attendance records: {error}</span>
          <button type="button" className="btn-nav" style={{ fontSize: 12, padding: '5px 12px' }} onClick={loadRecords}>Retry</button>
        </div>
      )}

      {can('recordMemberAttendance', getUserRole()) && (
      <div className="section-card" style={{ marginBottom: 24 }}>
        <div className="section-header">
          <h2>Log meeting attendance</h2>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: '0 20px 20px' }} aria-label="Log meeting attendance">
          {submitError && <div className="dashboard-form-error" role="alert" style={{ marginBottom: 12 }}>{submitError}</div>}
          {notice && <div role="status" style={{ marginBottom: 12, padding: '10px 12px', background: '#ECFDF5', color: '#047857', borderRadius: 8, fontSize: 13 }}>{notice}</div>}
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

          <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
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

          <button type="submit" className="btn-lg" disabled={submitting || !eventDate || !eventName.trim() || farmers.length === 0}>
            {submitting ? 'Logging…' : 'Log attendance'}
          </button>
        </form>
      </div>
      )}

      <div className="admin-card">
        <div className="section-header">
          <h2>Recent attendance records</h2>
        </div>

        {loading ? (
          <div className="skeleton-box" style={{ height: 200, margin: 20 }} />
        ) : (
          <>
            <div className="table-scroll">
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
            </div>
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
