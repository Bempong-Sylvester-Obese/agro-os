// src/components/dashboard/Members.jsx
import React, { useCallback, useState } from 'react'
import { Edit3, UserPlus, Loader2 } from 'lucide-react'
import { createFarmer, deactivateFarmer, updateFarmer } from '../../api/farmers'
import { exportDashboardReport } from '../../api/reports'
import { MembersSkeleton } from './DashboardSkeleton'
import DashboardModal, { ModalField } from './DashboardModal'
import { DashboardPagination, DashboardTableToolbar, useDashboardTable } from './DashboardTableTools'
import { ModalPresence } from '../Motion'
import {
  memberProductionDescription,
  productionFocus,
  productionFocusLabel,
  PRODUCTION_FOCUS_OPTIONS,
} from '../../utils/production'

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

const emptyProductionProfile = {
  production_focus: 'crop',
  crop_type: '',
  acreage: '',
  animal_type: '',
  animal_scale: '',
}

function productionProfilePayload(form) {
  const focus = form.production_focus
  return {
    production_focus: focus,
    ...(focus !== 'animal' && {
      crop_type: form.crop_type.trim() || null,
      acreage: form.acreage === '' ? null : Number(form.acreage),
    }),
    ...(focus !== 'crop' && {
      animal_type: form.animal_type.trim() || null,
      animal_scale: form.animal_scale === '' ? null : Number(form.animal_scale),
    }),
  }
}

function ProductionProfileFields({ form, set, idPrefix }) {
  const showCrop = form.production_focus !== 'animal'
  const showAnimal = form.production_focus !== 'crop'

  return (
    <>
      <ModalField
        htmlFor={`${idPrefix}-focus`}
        label="Production focus"
        hint="Crop, animal, or both — this controls which production logs the member can record."
      >
        <select
          id={`${idPrefix}-focus`}
          className="dashboard-modal-select"
          value={form.production_focus}
          onChange={set('production_focus')}
          required
        >
          {PRODUCTION_FOCUS_OPTIONS.map(option => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </ModalField>
      {showCrop && (
        <div className="modal-row">
          <ModalField htmlFor={`${idPrefix}-crop`} label="Crop type" optional>
            <input
              id={`${idPrefix}-crop`}
              className="dashboard-modal-input"
              value={form.crop_type}
              onChange={set('crop_type')}
              placeholder="e.g. Maize, Cocoa, Rice"
            />
          </ModalField>
          <ModalField htmlFor={`${idPrefix}-acreage`} label="Farm size (acres)" optional>
            <input
              id={`${idPrefix}-acreage`}
              className="dashboard-modal-input"
              type="number"
              min="0"
              step="0.1"
              value={form.acreage}
              onChange={set('acreage')}
              placeholder="e.g. 3.5"
            />
          </ModalField>
        </div>
      )}
      {showAnimal && (
        <div className="modal-row">
          <ModalField htmlFor={`${idPrefix}-animal`} label="Animal type" optional>
            <input
              id={`${idPrefix}-animal`}
              className="dashboard-modal-input"
              value={form.animal_type}
              onChange={set('animal_type')}
              placeholder="e.g. Poultry, Cattle, Goats"
            />
          </ModalField>
          <ModalField htmlFor={`${idPrefix}-scale`} label="Number of animals" optional>
            <input
              id={`${idPrefix}-scale`}
              className="dashboard-modal-input"
              type="number"
              min="0"
              step="1"
              value={form.animal_scale}
              onChange={set('animal_scale')}
              placeholder="e.g. 250"
            />
          </ModalField>
        </div>
      )}
    </>
  )
}

function AddMemberModal({ cooperativeId, onClose, onSuccess }) {
  const [form, setForm] = useState({
    name: '', phone: '', email: '', location: '', ...emptyProductionProfile,
  })
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const set = (key) => (e) => setForm(prev => ({ ...prev, [key]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    if (!form.name.trim() || !form.phone.trim()) {
      setError('Enter the member’s full name and phone number.')
      return
    }
    setLoading(true)
    try {
      const created = await createFarmer({
        name: form.name.trim(),
        phone: form.phone.trim(),
        cooperative_id: cooperativeId,
        email: form.email.trim() || null,
        location: form.location.trim() || null,
        ...productionProfilePayload(form),
      })
      onSuccess(created)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <DashboardModal
      title="Add member"
      subtitle="Register a farmer in this cooperative and set their production focus."
      onClose={onClose}
      closeDisabled={loading}
      closeOnBackdrop={!loading}
      label="add member dialog"
      wide
      as="form"
      bodyProps={{ onSubmit: handleSubmit }}
    >
      <div className="dashboard-modal-body">
        {error && <div role="alert" className="dashboard-form-error">{error}</div>}

        <div className="modal-row">
          <ModalField htmlFor="member-name" label="Full name">
            <input
              id="member-name"
              className="dashboard-modal-input"
              value={form.name}
              onChange={set('name')}
              placeholder="e.g. Kofi Asante"
              required
            />
          </ModalField>
          <ModalField htmlFor="member-phone" label="Phone number">
            <input
              id="member-phone"
              className="dashboard-modal-input"
              value={form.phone}
              onChange={set('phone')}
              placeholder="e.g. 024 123 4567"
              required
            />
          </ModalField>
        </div>

        <div className="modal-row">
          <ModalField htmlFor="member-email" label="Email" optional>
            <input
              id="member-email"
              className="dashboard-modal-input"
              type="email"
              value={form.email}
              onChange={set('email')}
              placeholder="farmer@example.com"
            />
          </ModalField>
          <ModalField htmlFor="member-location" label="Location" optional>
            <input
              id="member-location"
              className="dashboard-modal-input"
              value={form.location}
              onChange={set('location')}
              placeholder="e.g. Kumasi, Ashanti"
            />
          </ModalField>
        </div>

        <ProductionProfileFields form={form} set={set} idPrefix="member" />

        <div className="dashboard-modal-actions">
          <button type="button" className="dashboard-modal-btn-secondary" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button type="submit" className="btn-lg" disabled={loading}>
            {loading
              ? <><Loader2 size={16} className="spin" /> Saving…</>
              : 'Save member'}
          </button>
        </div>
      </div>
      <style>{`.spin { animation: spin 1s linear infinite; } @keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </DashboardModal>
  )
}

function EditMemberModal({ farmer, onClose, onSuccess }) {
  const [form, setForm] = useState({
    name: farmer.name || '',
    phone: farmer.phone || '',
    email: farmer.email || '',
    location: farmer.location || '',
    production_focus: productionFocus(farmer),
    crop_type: farmer.crop_type || '',
    acreage: farmer.acreage ?? '',
    animal_type: farmer.animal_type || '',
    animal_scale: farmer.animal_scale || '',
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
          name: form.name,
          phone: form.phone,
          email: form.email,
          location: form.location,
          ...productionProfilePayload(form),
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
    <DashboardModal
      title="Edit member"
      subtitle={`Update profile details for membership #${farmer.id}.`}
      onClose={onClose}
      closeDisabled={loading}
      closeOnBackdrop={!loading}
      label="edit member dialog"
      wide
      as="form"
      bodyProps={{ onSubmit: event => { event.preventDefault(); run('save') } }}
    >
      <div className="dashboard-modal-body">
        {error && <div role="alert" className="dashboard-form-error">{error}</div>}

        <div className="modal-row">
          <ModalField htmlFor="edit-member-name" label="Full name">
            <input id="edit-member-name" className="dashboard-modal-input" value={form.name} onChange={set('name')} required />
          </ModalField>
          <ModalField htmlFor="edit-member-phone" label="Phone number">
            <input id="edit-member-phone" className="dashboard-modal-input" value={form.phone} onChange={set('phone')} required />
          </ModalField>
        </div>

        <div className="modal-row">
          <ModalField htmlFor="edit-member-email" label="Email" optional>
            <input id="edit-member-email" className="dashboard-modal-input" type="email" value={form.email} onChange={set('email')} />
          </ModalField>
          <ModalField htmlFor="edit-member-location" label="Location" optional>
            <input id="edit-member-location" className="dashboard-modal-input" value={form.location} onChange={set('location')} />
          </ModalField>
        </div>

        <ProductionProfileFields form={form} set={set} idPrefix="edit-member" />

        <div className="dashboard-modal-actions dashboard-modal-actions--edit">
          <div className="dashboard-modal-side-actions">
            <button
              type="button"
              onClick={() => run('deactivate')}
              disabled={loading || farmer.membership_status === 'inactive'}
              className="danger-text-btn"
            >
              Deactivate
            </button>
            <button
              type="button"
              onClick={() => run('suspend')}
              disabled={loading || farmer.membership_status === 'suspended'}
              className="warning-text-btn"
            >
              Suspend
            </button>
          </div>
          <button type="submit" disabled={loading} className="btn-lg">
            {loading ? 'Saving…' : 'Save changes'}
          </button>
        </div>
      </div>
    </DashboardModal>
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
    farmer => `${farmer.name} ${farmer.phone} ${farmer.location || ''} ${productionFocusLabel(productionFocus(farmer))} ${farmer.crop_type || ''} ${farmer.animal_type || ''} ${farmer.animal_scale || ''}`,
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
              {['Member', 'Phone', 'Location', 'Production', 'Status', 'Trust Score', 'Actions'].map(h => (
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
                    <div className="pt-id">#{farmer.id} • Code: {farmer.farmer_code || 'N/A'}</div>
                  </div>
                  <span className="pt-m" style={{ fontSize: 12 }}>{farmer.phone}</span>
                  <span className="pt-m">{farmer.location || '—'}</span>
                  <span className="pt-m">
                    <strong>{productionFocusLabel(productionFocus(farmer))}</strong>
                    <span style={{ display: 'block', fontSize: 11 }}>{memberProductionDescription(farmer)}</span>
                  </span>
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
