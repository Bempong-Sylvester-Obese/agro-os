// src/components/dashboard/Loans.jsx
import { useCallback, useEffect, useState } from 'react'
import {
  approveLoan,
  createLoan,
  disburseLoan,
  fetchLoansDashboard,
  rejectLoan,
  repayLoan,
} from '../../api/loans'

const STATUS_CLS = {
  requested: 'bdg-amber',
  approved: 'bdg-amber',
  disbursed: 'bdg-green',
  repaid: 'bdg-green',
  rejected: 'bdg-red',
}

const EMPTY_REQUEST = { farmer_id: '', amount: '', purpose: '' }

function formatAmount(amount, currency = 'GHS') {
  return `${currency} ${Number(amount).toLocaleString()}`
}

function formatStatus(status) {
  return status.charAt(0).toUpperCase() + status.slice(1)
}

export default function Loans({ approverName = 'Cooperative Admin' }) {
  const [loans, setLoans] = useState([])
  const [farmers, setFarmers] = useState([])
  const [source, setSource] = useState('demo')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionId, setActionId] = useState(null)
  const [modal, setModal] = useState(false)
  const [form, setForm] = useState(EMPTY_REQUEST)
  const [formErr, setFormErr] = useState('')

  const farmerMap = Object.fromEntries(farmers.map((f) => [f.id, f]))

  const loadLoans = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await fetchLoansDashboard()
      setLoans(data.loans)
      setFarmers(data.farmers)
      setSource(data.source)
    } catch (err) {
      setError(err.message || 'Failed to load loans')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadLoans()
  }, [loadLoans])

  async function runAction(loanId, action) {
    if (source === 'demo') {
      setError('Connect the backend (VITE_API_URL) to run live loan actions.')
      return
    }

    setActionId(loanId)
    setError('')
    try {
      let updated
      switch (action) {
        case 'approve':
          updated = await approveLoan(loanId, approverName)
          break
        case 'reject':
          updated = await rejectLoan(loanId)
          break
        case 'disburse':
          updated = await disburseLoan(loanId)
          break
        case 'repay':
          updated = await repayLoan(loanId)
          break
        default:
          return
      }
      setLoans((prev) => prev.map((ln) => (ln.id === loanId ? updated : ln)))
    } catch (err) {
      setError(err.message || 'Action failed')
    } finally {
      setActionId(null)
    }
  }

  function openRequestModal() {
    setForm({
      ...EMPTY_REQUEST,
      farmer_id: farmers[0]?.id ? String(farmers[0].id) : '',
    })
    setFormErr('')
    setModal(true)
  }

  async function handleCreateLoan(e) {
    e.preventDefault()
    setFormErr('')

    const farmerId = parseInt(form.farmer_id, 10)
    const amount = parseFloat(form.amount)
    if (!farmerId) { setFormErr('Select a farmer.'); return }
    if (!amount || amount <= 0) { setFormErr('Enter a valid loan amount.'); return }

    if (source === 'demo') {
      setFormErr('Connect the backend to submit live loan requests.')
      return
    }

    setActionId('create')
    try {
      const created = await createLoan({
        farmer_id: farmerId,
        amount,
        currency: 'GHS',
        purpose: form.purpose.trim() || null,
      })
      setLoans((prev) => [created, ...prev])
      setModal(false)
    } catch (err) {
      setFormErr(err.message || 'Could not create loan request')
    } finally {
      setActionId(null)
    }
  }

  const pending = loans.filter((ln) => ln.status === 'requested').length
  const awaitingDisburse = loans.filter((ln) => ln.status === 'approved').length
  const outstanding = loans.filter((ln) => ln.status === 'disbursed').length
  const totalRequested = loans
    .filter((ln) => ln.status === 'requested' || ln.status === 'approved')
    .reduce((sum, ln) => sum + ln.amount, 0)

  return (
    <>
      <div className="pay-stats">
        {[
          ['Pending requests', String(pending), 'Awaiting admin review'],
          ['Approved', String(awaitingDisburse), 'Ready for Moolre payout'],
          ['Outstanding', String(outstanding), 'Disbursed, not repaid'],
          ['Pipeline value', formatAmount(totalRequested), source === 'api' ? 'Live API' : 'Demo data'],
        ].map(([lbl, val, sub]) => (
          <div key={lbl} className="stat-card">
            <div className="stat-lbl">{lbl}</div>
            <div className="stat-val serif">{val}</div>
            <div className="stat-sub">{sub}</div>
          </div>
        ))}
      </div>

      <div className="toolbar">
        <div className="toolbar-note">
          Golden Path steps 6–7: approve input loans and disburse via Moolre.
        </div>
        <div className="toolbar-actions">
          <button className="btn-nav" style={{ fontSize: 12, padding: '7px 14px' }} onClick={openRequestModal}>
            + Request loan
          </button>
        </div>
      </div>

      {error && <div className="auth-error" style={{ marginBottom: 16 }}>{error}</div>}

      <div className="admin-card table-cards">
        <div className="admin-card-head">
          <span className="admin-card-title serif">Loan requests</span>
          <span className="admin-card-action">{source === 'api' ? 'Live API' : 'Demo fallback'}</span>
        </div>

        <div className="loan-head">
          {['Farmer', 'Amount', 'Purpose', 'Status', 'Moolre ref', 'Actions'].map((h) => (
            <span key={h} className="pt-lbl">{h}</span>
          ))}
        </div>

        {loading && (
          <div style={{ padding: '28px 22px', textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>
            Loading loans…
          </div>
        )}

        {!loading && loans.length === 0 && (
          <div style={{ padding: '28px 22px', textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>
            No loan requests yet. Create one to start the Golden Path flow.
          </div>
        )}

        {!loading && loans.map((loan) => {
          const farmer = farmerMap[loan.farmer_id]
          const busy = actionId === loan.id

          return (
            <div key={loan.id} className="loan-row">
              <div data-label="Farmer">
                <div className="pt-name">{farmer?.name ?? `Farmer #${loan.farmer_id}`}</div>
                <div className="pt-id">Loan #{loan.id}{farmer?.phone ? ` · ${farmer.phone}` : ''}</div>
              </div>
              <span className="pt-v" data-label="Amount">{formatAmount(loan.amount, loan.currency)}</span>
              <span className="pt-m" data-label="Purpose">{loan.purpose || '—'}</span>
              <span className={`bdg ${STATUS_CLS[loan.status] ?? 'bdg-amber'}`} data-label="Status">
                {formatStatus(loan.status)}
              </span>
              <span className="pt-m mono" style={{ fontSize: 11 }} data-label="Moolre ref">
                {loan.moolre_transfer_ref || '—'}
              </span>
              <div className="loan-actions" data-label="Actions">
                {loan.status === 'requested' && (
                  <>
                    <button
                      className="btn-nav loan-btn"
                      disabled={busy}
                      onClick={() => runAction(loan.id, 'approve')}
                    >
                      {busy ? '…' : 'Approve'}
                    </button>
                    <button
                      className="loan-btn loan-btn-muted"
                      disabled={busy}
                      onClick={() => runAction(loan.id, 'reject')}
                    >
                      Reject
                    </button>
                  </>
                )}
                {loan.status === 'approved' && (
                  <button
                    className="btn-nav loan-btn"
                    disabled={busy}
                    onClick={() => runAction(loan.id, 'disburse')}
                  >
                    {busy ? '…' : 'Disburse →'}
                  </button>
                )}
                {loan.status === 'disbursed' && (
                  <button
                    className="btn-nav loan-btn"
                    disabled={busy}
                    onClick={() => runAction(loan.id, 'repay')}
                  >
                    {busy ? '…' : 'Record repay'}
                  </button>
                )}
                {(loan.status === 'repaid' || loan.status === 'rejected') && (
                  <span className="pt-m" style={{ fontSize: 11 }}>—</span>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {modal && (
        <div className="modal-overlay" onClick={() => setModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <div>
                <div className="modal-title serif">Request input loan</div>
                <div className="modal-sub">Submit a farmer loan request for cooperative review.</div>
              </div>
              <button className="modal-close" onClick={() => setModal(false)}>✕</button>
            </div>

            {formErr && <div className="auth-error" style={{ margin: '0 0 16px' }}>{formErr}</div>}

            <form onSubmit={handleCreateLoan} className="modal-form">
              <div className="auth-field">
                <label className="auth-label">Farmer *</label>
                <select
                  className="auth-input auth-select"
                  name="farmer_id"
                  value={form.farmer_id}
                  onChange={(e) => setForm((f) => ({ ...f, farmer_id: e.target.value }))}
                  required
                >
                  <option value="">Select farmer…</option>
                  {farmers.map((f) => (
                    <option key={f.id} value={f.id}>{f.name}{f.location ? ` · ${f.location}` : ''}</option>
                  ))}
                </select>
              </div>

              <div className="modal-row">
                <div className="auth-field">
                  <label className="auth-label">Amount (GHS) *</label>
                  <input
                    className="auth-input"
                    name="amount"
                    type="number"
                    min="1"
                    step="0.01"
                    placeholder="e.g. 500"
                    value={form.amount}
                    onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
                    required
                  />
                </div>
                <div className="auth-field">
                  <label className="auth-label">Purpose</label>
                  <input
                    className="auth-input"
                    name="purpose"
                    placeholder="e.g. Fertiliser for cocoa"
                    value={form.purpose}
                    onChange={(e) => setForm((f) => ({ ...f, purpose: e.target.value }))}
                  />
                </div>
              </div>

              <div className="modal-actions">
                <button type="button" className="btn-out-lg" style={{ fontSize: 13, padding: '10px 22px' }} onClick={() => setModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-lg" style={{ fontSize: 13, padding: '10px 22px' }} disabled={actionId === 'create'}>
                  {actionId === 'create' ? 'Submitting…' : 'Submit request →'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}
