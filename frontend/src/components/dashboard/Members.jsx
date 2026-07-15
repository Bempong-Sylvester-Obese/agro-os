// src/components/dashboard/Members.jsx
import { useState } from 'react'
import { Search, UserPlus, X, Loader2 } from 'lucide-react'
import { createFarmer } from '../../api/farmers'
import { MembersSkeleton } from './DashboardSkeleton'
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

// ── Members table ─────────────────────────────────────────────────────────────
export default function Members({ farmers = [], cooperativeId, onMemberAdded, loading }) {
  const [search, setSearch]       = useState('')
  const [statusFilter, setStatus] = useState('all')
  const [showModal, setShowModal] = useState(false)
  const [success, setSuccess] = useState(null)

  const filtered = farmers.filter(f => {
    const q = search.toLowerCase()
    const matchSearch = !q || f.name.toLowerCase().includes(q) || f.phone.includes(q)
    const matchStatus = statusFilter === 'all' || f.membership_status === statusFilter
    return matchSearch && matchStatus
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

      {/* ── Toolbar ── */}
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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flex: 1, minWidth: 0 }}>
          <div className="search-bar" style={{ flex: 1, maxWidth: 380 }}>
            <Search size={16} />
            <input
              type="text"
              placeholder="Search by name or phone…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <select
            value={statusFilter}
            onChange={e => setStatus(e.target.value)}
            style={{
              border: '1px solid var(--border)', borderRadius: 7, fontSize: 13,
              padding: '7px 10px', fontFamily: "'DM Sans', sans-serif",
              background: '#fff', cursor: 'pointer', outline: 'none',
            }}
          >
            <option value="all">All</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="suspended">Suspended</option>
          </select>
        </div>
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
      </div>

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
            Showing {filtered.length} of {farmers.length} member{farmers.length !== 1 ? 's' : ''}
          </div>
          <div className="table-scroll">
            <div className="mt-head">
              {['Member', 'Phone', 'Location', 'Crop', 'Status', 'Trust Score'].map(h => (
                <span key={h} className="pt-lbl">{h}</span>
              ))}
            </div>

            {filtered.length === 0 ? (
              <div style={{ padding: '24px 20px', color: 'var(--muted)', fontSize: 14 }}>
                No members match your search.
              </div>
            ) : (
              filtered.map(farmer => (
                <div key={farmer.id} className="mt-row">
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
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </>
  )
}
