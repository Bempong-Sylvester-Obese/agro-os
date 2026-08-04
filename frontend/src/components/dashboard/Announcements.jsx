import { useEffect, useState } from 'react'
import { Trash2, Loader2, Megaphone, MessageSquare } from 'lucide-react'
import { fetchAnnouncements, createAnnouncement, deleteAnnouncement } from '../../api/announcements'

export default function Announcements({ cooperativeId }) {
  const [announcements, setAnnouncements] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [deletingId, setDeletingId] = useState(null)

  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [sendSMS, setSendSMS] = useState(false)

  function load() {
    if (!cooperativeId) return
    setLoading(true)
    setError(null)
    fetchAnnouncements(cooperativeId)
      .then(setAnnouncements)
      .catch(setError)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [cooperativeId])

  async function handleCreate(e) {
    e.preventDefault()
    if (!title.trim() || !body.trim()) return
    setSubmitting(true)
    try {
      await createAnnouncement(cooperativeId, {
        title: title.trim(),
        body: body.trim(),
        send_sms: sendSMS,
      })
      setTitle('')
      setBody('')
      setSendSMS(false)
      load()
    } catch (err) {
      alert(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete(id) {
    if (!window.confirm('Delete this announcement?')) return
    setDeletingId(id)
    try {
      await deleteAnnouncement(cooperativeId, id)
      setAnnouncements(prev => prev.filter(a => a.id !== id))
    } catch (err) {
      alert(err.message)
    } finally {
      setDeletingId(null)
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const d = new Date(dateStr)
    return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
  }

  if (loading) return <div className="skeleton-box" style={{ height: 400 }} />
  if (error) return <div className="error-banner">Failed to load announcements</div>

  return (
    <div>
      <div className="section-card" style={{ marginBottom: 24 }}>
        <div className="section-header">
          <h2>Post announcement</h2>
        </div>

        <form onSubmit={handleCreate} style={{ padding: '0 20px 20px' }}>
          <label style={{ display: 'block', fontSize: 13, marginBottom: 12 }}>
            Title
            <input
              type="text"
              placeholder="e.g. Harvest schedule update"
              value={title}
              onChange={e => setTitle(e.target.value)}
              required
              style={{
                display: 'block',
                width: '100%',
                padding: '8px 12px',
                borderRadius: 6,
                border: '1px solid var(--border)',
                fontSize: 13,
                marginTop: 4,
              }}
            />
          </label>

          <label style={{ display: 'block', fontSize: 13, marginBottom: 12 }}>
            Message
            <textarea
              rows={4}
              placeholder="Enter the announcement body..."
              value={body}
              onChange={e => setBody(e.target.value)}
              required
              style={{
                display: 'block',
                width: '100%',
                padding: '8px 12px',
                borderRadius: 6,
                border: '1px solid var(--border)',
                fontSize: 13,
                marginTop: 4,
                resize: 'vertical',
              }}
            />
          </label>

          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, marginBottom: 16, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={sendSMS}
              onChange={e => setSendSMS(e.target.checked)}
            />
            <MessageSquare size={15} />
            Broadcast via SMS to all consenting members
          </label>

          <button type="submit" className="btn-lg" disabled={submitting || !title.trim() || !body.trim()}>
            {submitting ? <><Loader2 size={16} className="spin" /> Posting…</> : 'Post announcement'}
          </button>
          <style>{`.spin { animation: spin 1s linear infinite; } @keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </form>
      </div>

      <div className="admin-card">
        <div className="section-header">
          <h2>Announcements ({announcements.length})</h2>
        </div>

        {announcements.length === 0 ? (
          <div style={{ padding: 56, textAlign: 'center' }}>
            <div style={{
              width: 64, height: 64, borderRadius: '50%',
              background: 'rgba(26,71,49,0.08)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 20px',
            }}>
              <Megaphone size={30} color="var(--g)" />
            </div>
            <div className="serif" style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>No announcements yet</div>
            <div style={{ color: 'var(--muted)', fontSize: 14 }}>
              Post your first announcement to keep members informed.
            </div>
          </div>
        ) : (
          <div style={{ padding: '0 20px 20px' }}>
            {announcements.map(a => (
              <div
                key={a.id}
                style={{
                  padding: '14px 0',
                  borderBottom: '1px solid var(--border)',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 12,
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <h3 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>{a.title}</h3>
                    {a.send_sms && (
                      <span title="SMS broadcast sent" style={{ fontSize: 11, color: 'var(--g)', display: 'flex', alignItems: 'center', gap: 3 }}>
                        <MessageSquare size={12} /> SMS
                      </span>
                    )}
                  </div>
                  <p style={{ margin: 0, fontSize: 13, color: 'var(--muted)', lineHeight: 1.5 }}>
                    {a.body.length > 200 ? `${a.body.slice(0, 200)}…` : a.body}
                  </p>
                  <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 6 }}>
                    {formatDate(a.created_at)}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => handleDelete(a.id)}
                  disabled={deletingId === a.id}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--dgr)',
                    cursor: 'pointer',
                    padding: 4,
                    borderRadius: 4,
                    flexShrink: 0,
                    opacity: deletingId === a.id ? 0.5 : 1,
                  }}
                  title="Delete announcement"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
