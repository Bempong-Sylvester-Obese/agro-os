// src/pages/BookDemoPage.jsx
import { useState } from 'react'
import Footer from '../components/Footer'
import { useAppNavigate } from '../hooks/useAppNavigate'

const TIMES = ['9:00 AM', '10:00 AM', '11:00 AM', '12:00 PM', '2:00 PM', '3:00 PM', '4:00 PM']
const TOPICS = ['Full platform walkthrough', 'Payment & MoMo setup', 'AgroCredit Trust Scores', 'USSD integration', 'Member management', 'Custom enterprise setup']

function getDates() {
  const dates = []
  const d = new Date()
  for (let i = 0; i < 10; i++) {
    if (d.getDay() !== 0 && d.getDay() !== 6) dates.push(new Date(d))
    d.setDate(d.getDate() + 1)
    if (dates.length >= 6) break
  }
  return dates
}

const FMT = { weekday: 'short', month: 'short', day: 'numeric' }

function toLocalDateString(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function formatLocalDate(iso, options) {
  const [y, m, day] = iso.split('-').map(Number)
  return new Date(y, m - 1, day).toLocaleDateString('en-GB', options)
}

export default function BookDemoPage() {
  const setPage = useAppNavigate()
  const [step, setStep] = useState(0)
  const [selectedDate, setSelectedDate] = useState(null)
  const [selectedTime, setSelectedTime] = useState(null)
  const [form, setForm] = useState({ name: '', email: '', phone: '', cooperative: '', size: '1-50', topic: TOPICS[0], notes: '' })
  const [err, setErr] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const dates = getDates()

  function handleField(e) { setForm((f) => ({ ...f, [e.target.name]: e.target.value })); setErr('') }

  function goToDetails() {
    if (!selectedDate || !selectedTime) { setErr('Please select a date and time.'); return }
    setErr('')
    setStep(1)
  }

  function submitDemo() {
    if (submitting) return
    if (!form.name.trim() || !form.email.trim()) { setErr('Name and email are required.'); return }
    if (!form.email.includes('@')) { setErr('Enter a valid email address.'); return }
    setErr('')
    setSubmitting(true)
    window.setTimeout(() => {
      setStep(2)
      setSubmitting(false)
    }, 400)
  }

  return (
    <>
      <div className="sol-hero" style={{ paddingBottom: 48 }}>
        <h1 className="sol-hero-h1 serif">Book a demo</h1>
        <p className="sol-hero-sub">
          Get a personalized walkthrough of AgroOS with one of our specialists.<br />
          We'll tailor it to your cooperative's specific needs.
        </p>
      </div>

      <section className="sec" style={{ paddingTop: 0 }}>
        <div className="sec-inner" style={{ maxWidth: 900 }}>
          {step < 2 ? (
            <div className="book-demo-grid">
              <div>
                <div style={{
                  background: '#fff', border: '1px solid var(--border)', borderRadius: 16,
                  padding: 28, boxShadow: '0 2px 16px rgba(0,0,0,.04)',
                }}>
                  <div style={{ display: 'flex', gap: 0, marginBottom: 28 }}>
                    {['Pick a slot', 'Your details'].map((s, i) => (
                      <div key={s} style={{ flex: 1, position: 'relative' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <div style={{
                            width: 24, height: 24, borderRadius: '50%', fontSize: 11, fontWeight: 700,
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            background: i <= step ? 'var(--g)' : 'var(--border)',
                            color: i <= step ? '#fff' : 'var(--muted)',
                            flexShrink: 0,
                          }}>{i + 1}</div>
                          <div style={{ fontSize: 12, fontWeight: 600, color: i <= step ? 'var(--g)' : 'var(--muted)' }}>{s}</div>
                        </div>
                        {i < 1 && <div style={{ position: 'absolute', top: 12, left: 28, right: -16, height: 1, background: step > 0 ? 'var(--g)' : 'var(--border)' }} />}
                      </div>
                    ))}
                  </div>

                  {err && <div className="auth-error" style={{ marginBottom: 14 }}>{err}</div>}

                  {step === 0 && (
                    <>
                      <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10, color: 'var(--text)' }}>Select a date</div>
                      <div className="book-demo-dates">
                        {dates.map((d) => {
                          const iso = toLocalDateString(d)
                          const active = selectedDate === iso
                          return (
                            <button
                              key={iso}
                              type="button"
                              onClick={() => { setSelectedDate(iso); setSelectedTime(null); setErr('') }}
                              style={{
                                padding: '10px 6px', border: `1.5px solid ${active ? 'var(--g)' : 'var(--border)'}`,
                                borderRadius: 8, background: active ? 'var(--sage)' : '#fff',
                                cursor: 'pointer', fontSize: 11, fontWeight: 600,
                                color: active ? 'var(--g)' : 'var(--text)',
                              }}
                            >{d.toLocaleDateString('en-GB', FMT)}</button>
                          )
                        })}
                      </div>

                      <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10, color: 'var(--text)' }}>Select a time (GMT)</div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 8, marginBottom: 24 }}>
                        {TIMES.map((t) => {
                          const active = selectedTime === t
                          return (
                            <button
                              key={t}
                              type="button"
                              onClick={() => { setSelectedTime(t); setErr('') }}
                              disabled={!selectedDate}
                              style={{
                                padding: '9px 8px', border: `1.5px solid ${active ? 'var(--g)' : 'var(--border)'}`,
                                borderRadius: 8, background: active ? 'var(--sage)' : '#fff',
                                cursor: selectedDate ? 'pointer' : 'not-allowed',
                                opacity: selectedDate ? 1 : 0.45,
                                fontSize: 12, fontWeight: 600,
                                color: active ? 'var(--g)' : 'var(--text)',
                              }}
                            >{t}</button>
                          )
                        })}
                      </div>

                      <button type="button" className="btn-lg" style={{ width: '100%' }} onClick={goToDetails}>Continue →</button>
                    </>
                  )}

                  {step === 1 && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                      <div className="book-demo-fields">
                        <div className="auth-field">
                          <label className="auth-label">Full name *</label>
                          <input className="auth-input" name="name" placeholder="Kwame Boateng" value={form.name} onChange={handleField} />
                        </div>
                        <div className="auth-field">
                          <label className="auth-label">Work email *</label>
                          <input className="auth-input" name="email" type="email" placeholder="you@co-op.gh" value={form.email} onChange={handleField} />
                        </div>
                      </div>
                      <div className="auth-field">
                        <label className="auth-label">Cooperative name</label>
                        <input className="auth-input" name="cooperative" placeholder="Ashanti Farmers Co-op" value={form.cooperative} onChange={handleField} />
                      </div>
                      <div className="book-demo-fields">
                        <div className="auth-field">
                          <label className="auth-label">Phone</label>
                          <input className="auth-input" name="phone" placeholder="024 xxx xxxx" value={form.phone} onChange={handleField} />
                        </div>
                        <div className="auth-field">
                          <label className="auth-label">Cooperative size</label>
                          <select className="auth-input auth-select" name="size" value={form.size} onChange={handleField}>
                            {['1-50', '51-200', '201-500', '500+'].map((s) => <option key={s}>{s} members</option>)}
                          </select>
                        </div>
                      </div>
                      <div className="auth-field">
                        <label className="auth-label">What would you like to focus on?</label>
                        <select className="auth-input auth-select" name="topic" value={form.topic} onChange={handleField}>
                          {TOPICS.map((t) => <option key={t}>{t}</option>)}
                        </select>
                      </div>
                      <div className="auth-field">
                        <label className="auth-label">Anything else we should know?</label>
                        <textarea
                          className="auth-input"
                          name="notes"
                          placeholder="e.g. We currently use Excel and need help migrating member data..."
                          value={form.notes}
                          onChange={handleField}
                          rows={3}
                          style={{ resize: 'vertical', lineHeight: 1.5 }}
                        />
                      </div>
                      <div style={{ display: 'flex', gap: 10 }}>
                        <button type="button" className="btn-out-lg" style={{ fontSize: 13, padding: '10px 18px', flex: 1 }} onClick={() => { setStep(0); setErr('') }} disabled={submitting}>← Back</button>
                        <button type="button" className="btn-lg" style={{ fontSize: 13, padding: '10px 18px', flex: 2 }} onClick={submitDemo} disabled={submitting}>
                          {submitting ? 'Submitting…' : 'Confirm booking →'}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                {(selectedDate || selectedTime) && (
                  <div style={{
                    background: 'var(--g)', borderRadius: 14, padding: '20px 22px', color: '#fff',
                  }}>
                    <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.06em', opacity: .65, marginBottom: 10, textTransform: 'uppercase' }}>Your booking</div>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 6 }}>
                      <span>📅</span>
                      <span style={{ fontSize: 14, fontWeight: 600 }}>
                        {selectedDate ? formatLocalDate(selectedDate, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }) : 'No date selected'}
                      </span>
                    </div>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                      <span>🕙</span>
                      <span style={{ fontSize: 14, fontWeight: 600 }}>{selectedTime || 'No time selected'} · GMT</span>
                    </div>
                    <div style={{ marginTop: 12, fontSize: 12, opacity: .65 }}>30-minute video call · Google Meet or Zoom</div>
                  </div>
                )}

                <div style={{
                  background: '#fff', border: '1px solid var(--border)', borderRadius: 14, padding: '20px 22px',
                }}>
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 14, color: 'var(--text)' }}>What to expect</div>
                  {[
                    ['🎯', 'Personalized walkthrough', "We tailor the demo to your cooperative's size and needs."],
                    ['❓', 'Q&A time', 'Ask anything — pricing, migration, integrations, USSD setup.'],
                    ['🚀', 'Free setup help', "We'll help you get started with a free plan right after the call."],
                    ['⏱️', '30 minutes', 'Focused, no-fluff session. No sales pressure.'],
                  ].map(([icon, title, desc]) => (
                    <div key={title} style={{ display: 'flex', gap: 12, marginBottom: 14 }}>
                      <span style={{ fontSize: 18, flexShrink: 0 }}>{icon}</span>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 2 }}>{title}</div>
                        <div style={{ fontSize: 11, color: 'var(--muted)', lineHeight: 1.5 }}>{desc}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div style={{ maxWidth: 500, margin: '0 auto', textAlign: 'center' }}>
              <div style={{ fontSize: 64, marginBottom: 16 }}>🎉</div>
              <h2 className="serif" style={{ fontSize: 28, fontWeight: 900, color: 'var(--g)', marginBottom: 10 }}>Request received</h2>
              <p style={{ fontSize: 14, color: 'var(--muted)', lineHeight: 1.7, marginBottom: 28 }}>
                We've received your demo request for <strong>{selectedDate && formatLocalDate(selectedDate, { weekday: 'long', month: 'long', day: 'numeric' })}</strong> at <strong>{selectedTime} GMT</strong>.<br />
                We'll email you at <strong>{form.email}</strong> within 24 hours to confirm your booking.
              </p>
              <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
                <button type="button" className="btn-out-lg" style={{ fontSize: 13, padding: '10px 22px' }} onClick={() => setPage('home')}>Back to home</button>
                <button type="button" className="btn-lg" style={{ fontSize: 13, padding: '10px 22px' }} onClick={() => setPage('login', { loginMode: 'signup' })}>Get started →</button>
              </div>
            </div>
          )}
        </div>
      </section>

      <Footer />
    </>
  )
}
