// src/components/dashboard/Members.jsx
import React, { useCallback, useState } from 'react'
import { Edit3, UserPlus, X, Loader2 } from 'lucide-react'
import { createFarmer, deactivateFarmer, updateFarmer } from '../../api/farmers'
import { exportDashboardReport } from '../../api/reports'
import { MembersSkeleton } from './DashboardSkeleton'
import { DashboardPagination, DashboardTableToolbar, useDashboardTable } from './DashboardTableTools'
import { useModal } from '../../hooks/useModal'
import { ModalPresence } from '../Motion'

const STATUS_CLS = {
  active:    'bdg-green',
  inactive:  'bdg-amber',
  suspended: 'bdg-red',
}

const scoreTier = (score) => {
  if (score >= 82) return 'sh'
  if (score >= 60) return 'sm'
  return 'sl'
}

// ── Add Member Modal ──────────────────────────────────────────────────────────
function AddMemberModal({ cooperativeId, onClose, onSuccess }) {
  const { onBackdropClick, dialogProps, titleId, closeButtonProps } = useModal(onClose, { label: 'add member dialog' })
  const [form, setForm] = useState({
    name: '', phone: '', email: '', location: '', crop_type: '', acreage: '',
  })
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const set = (key) => (e) => setForm(prev => ({ ...prev, [key]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    if (!form.name.trim() || !form.phone.trim()) {
      setError('Full name and phone number are required.')
      return
    }
    setLoading(true)
    try {
      const created = await createFarmer({
        name:         form.name.trim(),
        phone:        form.phone.trim(),
        cooperative_id: cooperativeId,
        email:        form.email.trim()   || null,
        location:     form.location.trim() || null,
        crop_type:    form.crop_type.trim() || null,
        acreage:      form.acreage ? parseFloat(form.acreage) : null,
      })
      onSuccess(created)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const input = {
    width: '100%', padding: '10px 12px', border: '1.5px solid var(--border)',
    borderRadius: 8, fontSize: 14, fontFamily: "'DM Sans', sans-serif",
    outline: 'none', background: '#fff', color: 'var(--text)', boxSizing: 'border-box',
  }
  const lbl = { display: 'block', marginBottom: 6, fontSize: 13, fontWeight: 600 }

  return (
    <div
      className="dashboard-modal-overlay"
      onClick={onBackdropClick}
      style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.48)',
      backdropFilter: 'blur(4px)', zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
    }}>
      <div
        className="dashboard-modal"
        {...dialogProps}
        style={{
        background: '#fff', borderRadius: 16, width: '100%', maxWidth: 500,
        maxHeight: '92vh', overflow: 'auto',
        boxShadow: '0 32px 80px rgba(0,0,0,0.22)',
      }}>
        {/* Header */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
          padding: '24px 28px 0',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{
              width: 44, height: 44, borderRadius: 12,
              background: 'rgba(26,71,49,0.1)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <UserPlus size={22} color="var(--g)" />
            </div>
            <div>
              <div id={titleId} className="serif" style={{ fontWeight: 700, fontSize: 19, lineHeight: 1.2 }}>
                Add new member
              </div>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>
                Register a farmer to your cooperative
              </div>
            </div>
          </div>
          <button
            {...closeButtonProps}
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', padding: 4, marginTop: -2 }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Divider */}
        <div style={{ height: 1, background: 'var(--border)', margin: '20px 0 0' }} />

        <form onSubmit={handleSubmit} style={{ padding: '20px 28px 28px' }}>
          {error && (
            <div style={{
              padding: '10px 14px', background: '#FEF2F2', color: '#991B1B',
              borderRadius: 8, marginBottom: 18, fontSize: 13, borderLeft: '3px solid #F87171',
            }}>
              {error}
            </div>
          )}

          <div className="modal-row">
            <div>
              <label htmlFor="member-name" style={lbl}>Full name *</label>
              <input id="member-name" style={input} value={form.name} onChange={set('name')} placeholder="e.g. Kofi Asante" required />
            </div>
            <div>
              <label htmlFor="member-phone" style={lbl}>Phone number *</label>
              <input id="member-phone" style={input} value={form.phone} onChange={set('phone')} placeholder="e.g. 024 123 4567" required />
            </div>
            <div>
              <label htmlFor="member-email" style={lbl}>Email <span style={{ color: 'var(--muted)', fontWeight: 400 }}>(optional)</span></label>
              <input id="member-email" style={input} type="email" value={form.email} onChange={set('email')} placeholder="farmer@example.com" />
            </div>
            <div>
              <label htmlFor="member-location" style={lbl}>Location <span style={{ color: 'var(--muted)', fontWeight: 400 }}>(optional)</span></label>
              <input id="member-location" style={input} value={form.location} onChange={set('location')} placeholder="e.g. Kumasi, Ashanti" />
            </div>
            <div>
              <label htmlFor="member-crop" style={lbl}>Crop type <span style={{ color: 'var(--muted)', fontWeight: 400 }}>(optional)</span></label>
              <input id="member-crop" style={input} value={form.crop_type} onChange={set('crop_type')} placeholder="e.g. Maize, Cocoa, Rice" />
            </div>
            <div>
              <label htmlFor="member-acreage" style={lbl}>Farm size (acres) <span style={{ color: 'var(--muted)', fontWeight: 400 }}>(optional)</span></label>
              <input id="member-acreage" style={input} type="number" min="0" step="0.1" value={form.acreage} onChange={set('acreage')} placeholder="e.g. 3.5" />
            </div>
          </div>

          <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
            <button
              type="button" onClick={onClose}
              style={{
                flex: 1, padding: 12, borderRadius: 8, border: '1.5px solid var(--border)',
                background: 'none', color: 'var(--text)', fontFamily: "'DM Sans', sans-serif",
                fontSize: 14, fontWeight: 600, cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              type="submit" className="btn-lg" disabled={loading}
              style={{ flex: 2, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 8 }}
            >
              {loading
                ? <><Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> Adding...</>
                : 'Add member →'}
            </button>
          </div>
        </form>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}

function EditMemberModal({ farmer, onClose, onSuccess }) {
  const { onBackdropClick, dialogProps, titleId, closeButtonProps } = useModal(onClose, { label: 'edit member dialog' })
  const [form, setForm] = useState({
    name: farmer.name || '',
    phone: farmer.phone || '',
    email: farmer.email || '',
    location: farmer.location || '',
    crop_type: farmer.crop_type || '',
    acreage: farmer.acreage ?? '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const set = key => event => setForm(previous => ({ ...previous, [key]: event.target.value }))

  const run = async action => {
    setLoading(true)
    setError(null)
    try {
      if (action === 'save') {
        await updateFarmer(farmer.id, {
          ...form,
          acreage: form.acreage === '' ? null : Number(form.acreage),
        })
      } else if (action === 'suspend') {
        await updateFarmer(farmer.id, { membership_status: 'suspended' })
      } else {
        await deactivateFarmer(farmer.id)
      }
      onSuccess(action)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="dashboard-modal-overlay" onClick={onBackdropClick}>
      <div className="dashboard-modal member-edit-modal" {...dialogProps}>
        <div className="dashboard-modal-head">
          <div>
            <div id={titleId} className="serif">Member details</div>
            <div className="pt-id">Membership #{farmer.id}</div>
          </div>
          <button {...closeButtonProps} onClick={onClose} className="dashboard-icon-close"><X size={20} /></button>
        </div>
        <form onSubmit={event => { event.preventDefault(); run('save') }} className="dashboard-modal-body">
          {error && <div role="alert" className="dashboard-form-error">{error}</div>}
          <div className="modal-row">
            <label>Full name<input className="auth-input" value={form.name} onChange={set('name')} required /></label>
            <label>Phone<input className="auth-input" value={form.phone} onChange={set('phone')} required /></label>
            <label>Email<input className="auth-input" type="email" value={form.email} onChange={set('email')} /></label>
            <label>Location<input className="auth-input" value={form.location} onChange={set('location')} /></label>
            <label>Crop type<input className="auth-input" value={form.crop_type} onChange={set('crop_type')} /></label>
            <label>Farm size (acres)<input className="auth-input" type="number" min="0" step="0.1" value={form.acreage} onChange={set('acreage')} /></label>
          </div>
          <div className="member-edit-actions">
            <button type="button" onClick={() => run('deactivate')} disabled={loading || farmer.membership_status === 'inactive'} className="danger-text-btn">Deactivate</button>
            <button type="button" onClick={() => run('suspend')} disabled={loading || farmer.membership_status === 'suspended'} className="warning-text-btn">Suspend</button>
            <button type="submit" disabled={loading} className="btn-nav">{loading ? 'Saving…' : 'Save changes'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Members table ─────────────────────────────────────────────────────────────
export default function Members({ farmers = [], cooperativeId, onMemberAdded, loading }) {
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState(null)
  const [success, setSuccess] = useState(null)
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState('')
  const searchableText = useCallback(
    farmer => `${farmer.name} ${farmer.phone} ${farmer.location || ''} ${farmer.crop_type || ''}`,
    [],
  )
  const statusValue = useCallback(farmer => farmer.membership_status, [])
  const dateValue = useCallback(farmer => farmer.created_at, [])
  const table = useDashboardTable({
    rows: farmers,
    searchableText,
    statusValue,
    dateValue,
  })

  const handleSuccess = (membership) => {
    setShowModal(false)
    setSuccess(
      membership.existing_farmer
        ? `${membership.name} was linked to this cooperative.`
        : `${membership.name} was added to this cooperative.`,
    )
    onMemberAdded()
  }

  const handleMemberChanged = action => {
    setEditing(null)
    setSuccess(action === 'save' ? 'Member details updated.' : `Member ${action === 'suspend' ? 'suspended' : 'deactivated'}.`)
    onMemberAdded()
  }

  const handleExport = async () => {
    setExporting(true)
    setExportError('')
    try {
      await exportDashboardReport('members', cooperativeId, table.exportFilters)
    } catch (error) {
      setExportError(error.message || 'Could not export members. Please try again.')
    } finally {
      setExporting(false)
    }
  }

  if (loading) return <MembersSkeleton />

  return (
    <>
      <ModalPresence show={showModal}>
        <AddMemberModal
          cooperativeId={cooperativeId}
          onClose={() => setShowModal(false)}
          onSuccess={handleSuccess}
        />
      </ModalPresence>
      <ModalPresence show={Boolean(editing)}>
        {editing && <EditMemberModal farmer={editing} onClose={() => setEditing(null)} onSuccess={handleMemberChanged} />}
      </ModalPresence>

      {success && (
        <div
          role="status"
          style={{
            padding: '10px 14px', background: '#ECFDF5', color: '#166534',
            borderRadius: 8, marginBottom: 16, fontSize: 13, borderLeft: '3px solid #22C55E',
          }}
        >
          {success}
        </div>
      )}
      <DashboardTableToolbar
        label="Members"
        table={table}
        statuses={[
          { value: 'active', label: 'Active' },
          { value: 'inactive', label: 'Inactive' },
          { value: 'suspended', label: 'Suspended' },
        ]}
        onExport={handleExport}
        exporting={exporting}
        exportError={exportError}
      >
        <button
          className="btn-nav"
          onClick={() => cooperativeId && setShowModal(true)}
          disabled={!cooperativeId}
          title={!cooperativeId ? 'Link a cooperative before adding members' : undefined}
          style={{
            fontSize: 13, padding: '8px 16px', display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0,
            opacity: cooperativeId ? 1 : 0.5, cursor: cooperativeId ? 'pointer' : 'not-allowed',
          }}
        >
          <UserPlus size={15} /> Add member
        </button>
      </DashboardTableToolbar>

      {/* ── Empty state ── */}
      {farmers.length === 0 ? (
        <div className="admin-card" style={{ padding: 56, textAlign: 'center' }}>
          <div style={{
            width: 64, height: 64, borderRadius: '50%',
            background: 'rgba(26,71,49,0.08)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 20px',
          }}>
            <UserPlus size={30} color="var(--g)" />
          </div>
          <div className="serif" style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>No members yet</div>
          <div style={{ color: 'var(--muted)', fontSize: 14, marginBottom: 28, maxWidth: 320, margin: '0 auto 28px' }}>
            Register your first farmer to start tracking dues, production, and trust scores.
          </div>
          <button
            className="btn-lg"
            onClick={() => cooperativeId && setShowModal(true)}
            disabled={!cooperativeId}
            title={!cooperativeId ? 'Link a cooperative before adding members' : undefined}
            style={{ opacity: cooperativeId ? 1 : 0.5, cursor: cooperativeId ? 'pointer' : 'not-allowed' }}
          >
            Add first member →
          </button>
        </div>
      ) : (
        <div className="admin-card">
          <div style={{ padding: '10px 20px', borderBottom: '1px solid var(--border)', fontSize: 12, color: 'var(--muted)' }}>
            {table.filteredRows.length} of {farmers.length} member{farmers.length !== 1 ? 's' : ''} match
          </div>
          <div className="table-scroll">
            <div className="mt-head members-admin-head">
              {['Member', 'Phone', 'Location', 'Crop', 'Status', 'Trust Score', 'Actions'].map(h => (
                <span key={h} className="pt-lbl">{h}</span>
              ))}
            </div>

            {table.filteredRows.length === 0 ? (
              <div style={{ padding: '24px 20px', color: 'var(--muted)', fontSize: 14 }}>
                No members match the current filters.
              </div>
            ) : (
              table.pageRows.map(farmer => (
                <div key={farmer.id} className="mt-row members-admin-row">
                  <div>
                    <div className="pt-name">{farmer.name}</div>
                    <div className="pt-id">#{farmer.id}</div>
                  </div>
                  <span className="pt-m" style={{ fontSize: 12 }}>{farmer.phone}</span>
                  <span className="pt-m">{farmer.location || '—'}</span>
                  <span className="pt-m">{farmer.crop_type || '—'}</span>
                  <span className={`bdg ${STATUS_CLS[farmer.membership_status] || 'bdg-amber'}`}>
                    {farmer.membership_status}
                  </span>
                  <span className={`score-bdg ${scoreTier(farmer.trust_score)}`}>
                    {farmer.trust_score > 0 ? Math.round(farmer.trust_score) : '—'}
                  </span>
                  <button type="button" className="table-row-action" onClick={() => setEditing(farmer)} aria-label={`Edit ${farmer.name}`}>
                    <Edit3 size={14} aria-hidden="true" /> Edit
                  </button>
                </div>
              ))
            )}
          </div>
          <DashboardPagination label="Members" table={table} />
        </div>
      )}
    </>
  )
}
