// src/components/dashboard/Settings.jsx
import { useState, useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { updateCooperative } from '../../api/cooperatives'

export default function Settings({ cooperative, onRefresh }) {
  const [form, setForm] = useState({
    name: '',
    location: '',
    description: '',
    default_currency: 'GHS',
    moolre_account_number: ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [successMsg, setSuccessMsg] = useState(null)

  useEffect(() => {
    if (cooperative) {
      setForm({
        name: cooperative.name || '',
        location: cooperative.location || '',
        description: cooperative.description || '',
        default_currency: cooperative.default_currency || 'GHS',
        moolre_account_number: cooperative.moolre_account_number || ''
      })
    }
  }, [cooperative])

  if (!cooperative) {
    return <div style={{ padding: 32, color: 'var(--muted)', fontSize: 14 }}>Loading settings…</div>
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccessMsg(null)
    
    try {
      await updateCooperative(cooperative.id, form)
      setSuccessMsg('Settings updated successfully.')
      if (onRefresh) onRefresh()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = {
    width: '100%', padding: '10px 12px', border: '1.5px solid var(--border)',
    borderRadius: 8, fontSize: 14, fontFamily: "'DM Sans', sans-serif",
    outline: 'none', background: '#fff', color: 'var(--text)', boxSizing: 'border-box',
    marginTop: 6
  }

  const labelStyle = { fontSize: 13, fontWeight: 600 }

  return (
    <div style={{ maxWidth: 800 }}>
      <div className="admin-card">
        <div className="admin-card-head" style={{ borderBottom: '1px solid var(--border)', padding: '24px 28px' }}>
          <div>
            <div className="serif" style={{ fontWeight: 700, fontSize: 20 }}>Cooperative Settings</div>
            <div style={{ fontSize: 13, color: 'var(--muted)', marginTop: 4 }}>Update your organization's profile and payment configurations</div>
          </div>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: '28px' }}>
          {error && <div style={{ padding: 12, background: '#FEF2F2', color: '#991B1B', borderRadius: 8, fontSize: 13, marginBottom: 20 }}>{error}</div>}
          {successMsg && <div style={{ padding: 12, background: '#ecfdf5', color: '#047857', borderRadius: 8, fontSize: 13, marginBottom: 20 }}>{successMsg}</div>}
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* General Profile */}
            <div>
              <h3 className="serif" style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>General Profile</h3>
              <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
                <div style={{ flex: 2 }}>
                  <label style={labelStyle}>Cooperative Name</label>
                  <input style={inputStyle} type="text" value={form.name} onChange={e => setForm({...form, name: e.target.value})} required disabled={loading}/>
                </div>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Location / Region</label>
                  <input style={inputStyle} type="text" value={form.location} onChange={e => setForm({...form, location: e.target.value})} disabled={loading}/>
                </div>
              </div>
              <div>
                <label style={labelStyle}>Description</label>
                <textarea 
                  style={{ ...inputStyle, minHeight: 80, resize: 'vertical' }} 
                  value={form.description} 
                  onChange={e => setForm({...form, description: e.target.value})} 
                  disabled={loading}
                />
              </div>
            </div>

            <div style={{ height: 1, background: 'var(--border)', margin: '12px 0' }} />

            {/* Financial Configuration */}
            <div>
              <h3 className="serif" style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Financial Configuration</h3>
              <p style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 16 }}>This Moolre account number will be used as the funding source for loan disbursements to your members.</p>
              
              <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Default Currency</label>
                  <select style={inputStyle} value={form.default_currency} onChange={e => setForm({...form, default_currency: e.target.value})} disabled={loading}>
                    <option value="GHS">Ghana Cedi (GHS)</option>
                    <option value="USD">US Dollar (USD)</option>
                  </select>
                </div>
                <div style={{ flex: 2 }}>
                  <label style={labelStyle}>Moolre Account Number</label>
                  <input style={inputStyle} type="text" value={form.moolre_account_number} onChange={e => setForm({...form, moolre_account_number: e.target.value})} placeholder="e.g. 1089700..." required disabled={loading}/>
                </div>
              </div>
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 12 }}>
              <button type="submit" className="btn-lg" disabled={loading} style={{ padding: '12px 24px', display: 'flex', alignItems: 'center', gap: 8 }}>
                {loading ? <><Loader2 size={16} className="spin" /> Saving...</> : 'Save Settings'}
              </button>
            </div>
          </div>
        </form>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } } .spin { animation: spin 1s linear infinite; }`}</style>
    </div>
  )
}
