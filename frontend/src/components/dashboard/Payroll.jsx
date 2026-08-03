import { useEffect, useState } from 'react'
import { CheckCircle, XCircle, Clock, AlertTriangle } from 'lucide-react'
import { fetchPayrollSummary, approvePayroll, disbursePayroll, fetchPayrollHistory } from '../../api/payroll'
import { fetchWorkers } from '../../api/workers'
import DashboardTableToolbar from './DashboardTableToolbar'
import DashboardPagination from './DashboardPagination'

const PAGE_SIZE = 20

function getTodayString() {
  return new Date().toISOString().slice(0, 10)
}

function getMonthStart() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`
}

const STATUS_BADGE = {
  pending:  { className: 'badge badge-pending', icon: Clock },
  approved: { className: 'badge badge-approved', icon: AlertTriangle },
  paid:     { className: 'badge badge-paid', icon: CheckCircle },
  failed:   { className: 'badge badge-failed', icon: XCircle },
}

export default function Payroll({ cooperativeId }) {
  const [tab, setTab] = useState('summary')
  const [periodStart, setPeriodStart] = useState(getMonthStart)
  const [periodEnd, setPeriodEnd] = useState(getTodayString)

  const [summary, setSummary] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [approving, setApproving] = useState(false)
  const [disbursing, setDisbursing] = useState(false)

  const [expandedPeriod, setExpandedPeriod] = useState(null)
  const [page, setPage] = useState(0)

  function loadSummary() {
    if (!cooperativeId || !periodStart || !periodEnd) return
    setLoading(true)
    setError(null)
    fetchPayrollSummary(cooperativeId, periodStart, periodEnd)
      .then(setSummary)
      .catch(setError)
      .finally(() => setLoading(false))
  }

  function loadHistory() {
    if (!cooperativeId) return
    fetchPayrollHistory(cooperativeId)
      .then(setHistory)
      .catch(() => {})
  }

  useEffect(() => { loadSummary() }, [cooperativeId, periodStart, periodEnd])
  useEffect(() => { if (tab === 'history') loadHistory() }, [cooperativeId, tab])

  const pageCount = summary ? Math.ceil(summary.items.length / PAGE_SIZE) : 0
  const paged = summary ? summary.items.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE) : []

  async function handleApprove() {
    if (!confirm('Approve payroll for this period?')) return
    setApproving(true)
    try {
      await approvePayroll(cooperativeId, periodStart, periodEnd)
      alert('Payroll approved successfully')
      loadSummary()
    } catch (e) { alert(e.message) }
    finally { setApproving(false) }
  }

  async function handleDisburse(ps, pe) {
    if (!confirm('Disburse payments for this period?')) return
    setDisbursing(true)
    try {
      const results = await disbursePayroll(cooperativeId, ps, pe)
      const paid = results.filter(r => r.status === 'paid').length
      const failed = results.filter(r => r.status === 'failed').length
      alert(`Disbursement complete: ${paid} paid, ${failed} failed`)
      loadHistory()
    } catch (e) { alert(e.message) }
    finally { setDisbursing(false) }
  }

  return (
    <div className="section-card">
      <div className="section-header">
        <h2>Payroll</h2>
        <div className="tab-bar">
          <button className={`tab ${tab === 'summary' ? 'active' : ''}`} onClick={() => setTab('summary')}>Summary</button>
          <button className={`tab ${tab === 'history' ? 'active' : ''}`} onClick={() => { setTab('history'); loadHistory() }}>History</button>
        </div>
      </div>

      {tab === 'summary' && (
        <>
          <DashboardTableToolbar>
            <label>
              Period start
              <input type="date" value={periodStart}
                onChange={e => { setPage(0); setPeriodStart(e.target.value) }} />
            </label>
            <label>
              Period end
              <input type="date" value={periodEnd}
                onChange={e => { setPage(0); setPeriodEnd(e.target.value) }} />
            </label>
          </DashboardTableToolbar>

          {loading && <div className="skeleton-box" style={{ height: 300 }} />}
          {error && <div className="error-banner">Failed to load payroll summary</div>}
          {!loading && !error && summary && (
            <>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Worker Name</th>
                    <th>Phone</th>
                    <th>Wage Rate</th>
                    <th>Total Hours</th>
                    <th>Shifts</th>
                    <th>Gross Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {paged.map((item, i) => (
                    <tr key={item.worker_id}>
                      <td>{item.worker_name}</td>
                      <td>{item.phone}</td>
                      <td>GHS {item.wage_rate.toFixed(2)}</td>
                      <td>{item.total_hours}</td>
                      <td>{item.total_shifts}</td>
                      <td><strong>GHS {item.gross_amount.toFixed(2)}</strong></td>
                    </tr>
                  ))}
                  {summary.items.length > 0 && (
                    <tr className="total-row">
                      <td colSpan={4} /><td><strong>Total</strong></td>
                      <td><strong>GHS {summary.total_gross.toFixed(2)}</strong></td>
                    </tr>
                  )}
                  {paged.length === 0 && (
                    <tr><td colSpan={6} className="empty-state">No attendance data for this period</td></tr>
                  )}
                </tbody>
              </table>

              <DashboardPagination page={page} pageCount={pageCount} onPage={setPage}
                total={summary.items.length}
                rangeStart={page * PAGE_SIZE + 1}
                rangeEnd={Math.min((page + 1) * PAGE_SIZE, summary.items.length)} />

              <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
                <button className="btn btn-primary" onClick={handleApprove} disabled={approving || summary.items.length === 0}>
                  {approving ? 'Approving…' : 'Approve Payroll'}
                </button>
              </div>
            </>
          )}
        </>
      )}

      {tab === 'history' && (
        <>
          <table className="data-table">
            <thead>
              <tr>
                <th>Period</th>
                <th>Status</th>
                <th>Workers</th>
                <th>Total Gross</th>
                <th>Paid At</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {history.map((period, idx) => {
                const BadgeConfig = STATUS_BADGE[period.status] || STATUS_BADGE.pending
                const BadgeIcon = BadgeConfig.icon
                const isExpanded = expandedPeriod === idx
                return (
                  <>
                    <tr key={idx} className={isExpanded ? 'row-expanded' : ''}>
                      <td>{period.period_start} &mdash; {period.period_end}</td>
                      <td>
                        <span className={BadgeConfig.className}>
                          <BadgeIcon size={14} /> {period.status}
                        </span>
                      </td>
                      <td>{period.total_workers}</td>
                      <td>GHS {period.total_gross.toFixed(2)}</td>
                      <td>{period.paid_at ? new Date(period.paid_at).toLocaleDateString() : '—'}</td>
                      <td>
                        <button className="btn btn-sm" onClick={() => setExpandedPeriod(isExpanded ? null : idx)}>
                          {isExpanded ? 'Collapse' : 'Details'}
                        </button>
                        {period.status === 'approved' && (
                          <button className="btn btn-primary btn-sm" style={{ marginLeft: 4 }}
                            onClick={() => handleDisburse(period.period_start, period.period_end)}
                            disabled={disbursing}>
                            {disbursing ? '…' : 'Disburse'}
                          </button>
                        )}
                      </td>
                    </tr>
                    {isExpanded && period.payouts.map(p => (
                      <tr key={p.id} className="detail-row">
                        <td colSpan={2} style={{ paddingLeft: 32 }}>
                          Worker #{p.worker_id} &mdash; GHS {p.gross_amount.toFixed(2)}
                        </td>
                        <td colSpan={2}>
                          {p.moolre_reference ? `Ref: ${p.moolre_reference}` : ''}
                        </td>
                        <td colSpan={2}>
                          {p.failure_reason && <span className="text-danger">{p.failure_reason}</span>}
                        </td>
                      </tr>
                    ))}
                  </>
                )
              })}
              {history.length === 0 && (
                <tr><td colSpan={6} className="empty-state">No payroll history yet</td></tr>
              )}
            </tbody>
          </table>
        </>
      )}
    </div>
  )
}
