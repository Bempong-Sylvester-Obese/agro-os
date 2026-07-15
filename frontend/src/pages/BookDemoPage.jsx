import { useState } from 'react'
import {
  ArrowRight,
  Building2,
  CalendarDays,
  Check,
  CheckCircle2,
  Clock3,
  Download,
  Mail,
  Phone,
  ShieldCheck,
  UserRound,
  Users,
  Video,
} from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import Footer from '../components/Footer'
import { Reveal } from '../components/Motion'
import { useAppNavigate } from '../hooks/useAppNavigate'

const TIMES = ['09:00', '10:00', '11:00', '12:00', '14:00', '15:00', '16:00']
const TOPICS = [
  'Full platform evaluation',
  'Payments and MoMo operations',
  'AgroCredit Trust Scores',
  'USSD and field access',
  'Member and production management',
  'Enterprise implementation',
]
const SIZES = ['1–50 members', '51–200 members', '201–500 members', '500+ members']

function toIsoDate(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function formatDate(iso, options = {}) {
  const [year, month, day] = iso.split('-').map(Number)
  return new Date(year, month - 1, day).toLocaleDateString('en-GB', options)
}

function formatTime(time) {
  const [hour, minute] = time.split(':').map(Number)
  return new Date(2026, 0, 1, hour, minute).toLocaleTimeString('en-GB', {
    hour: 'numeric',
    minute: '2-digit',
  })
}

function calendarStamp(date) {
  return date.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '')
}

export default function BookDemoPage() {
  const setPage = useAppNavigate()
  const [searchParams] = useSearchParams()
  const enterpriseEnquiry = searchParams.get('plan') === 'enterprise'
  const requestedTopic = searchParams.get('topic')
  const [minimumDate] = useState(() => {
    const date = new Date()
    date.setDate(date.getDate() + 1)
    return toIsoDate(date)
  })
  const [selectedDate, setSelectedDate] = useState('')
  const [selectedTime, setSelectedTime] = useState('')
  const [form, setForm] = useState({
    name: '',
    email: '',
    phone: '',
    cooperative: '',
    size: SIZES[0],
    topic: TOPICS.includes(requestedTopic) ? requestedTopic : enterpriseEnquiry ? 'Enterprise implementation' : TOPICS[0],
    notes: '',
  })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [confirmation, setConfirmation] = useState(null)

  function updateField(event) {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
    setError('')
  }

  function chooseDate(event) {
    setSelectedDate(event.target.value)
    setSelectedTime('')
    setError('')
  }

  function submitRequest(event) {
    event.preventDefault()
    if (submitting) return
    if (!form.name.trim() || !form.email.trim() || !form.cooperative.trim()) {
      setError('Add your name, work email, and organisation before continuing.')
      return
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      setError('Enter a valid work email address.')
      return
    }
    if (!selectedDate || !selectedTime) {
      setError('Select an available date and time for the session.')
      return
    }
    if (selectedDate < minimumDate) {
      setError('Select a future date for the consultation.')
      return
    }

    setSubmitting(true)
    const reference = `AGO-${selectedDate.replaceAll('-', '').slice(2)}-${selectedTime.replace(':', '')}`
    const request = { ...form, selectedDate, selectedTime, reference }

    window.setTimeout(() => {
      setConfirmation(request)
      setSubmitting(false)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }, 500)
  }

  function downloadCalendarInvite() {
    if (!confirmation) return
    const [year, month, day] = confirmation.selectedDate.split('-').map(Number)
    const [hour, minute] = confirmation.selectedTime.split(':').map(Number)
    const start = new Date(Date.UTC(year, month - 1, day, hour, minute))
    const finish = new Date(start.getTime() + 30 * 60 * 1000)
    const description = `AgroOS platform consultation for ${confirmation.cooperative}. Focus: ${confirmation.topic}.`
    const invite = [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//AgroOS//Demo Consultation//EN',
      'BEGIN:VEVENT',
      `UID:${confirmation.reference}@agroos`,
      `DTSTAMP:${calendarStamp(new Date())}`,
      `DTSTART:${calendarStamp(start)}`,
      `DTEND:${calendarStamp(finish)}`,
      'SUMMARY:AgroOS platform consultation',
      `DESCRIPTION:${description}`,
      'LOCATION:Video conference',
      'END:VEVENT',
      'END:VCALENDAR',
    ].join('\r\n')
    const url = window.URL.createObjectURL(new window.Blob([invite], { type: 'text/calendar;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `agroos-demo-${confirmation.selectedDate}.ics`
    link.click()
    window.URL.revokeObjectURL(url)
  }

  if (confirmation) {
    return (
      <>
        <main className="demo-success-shell">
          <Reveal className="demo-success-card">
            <div className="demo-success-mark"><CheckCircle2 size={30} /></div>
            <div className="demo-kicker">{enterpriseEnquiry ? 'Enterprise enquiry received' : 'Request received'}</div>
            <h1 className="demo-success-title serif">
              {enterpriseEnquiry ? 'Your enterprise consultation is reserved.' : 'Your consultation is reserved.'}
            </h1>
            <p className="demo-success-copy">
              We have recorded your preferred time. A product specialist will contact you at
              {' '}<strong>{confirmation.email}</strong> to confirm the meeting link.
            </p>

            <div className="demo-confirmation">
              <div>
                <span>Date</span>
                <strong>{formatDate(confirmation.selectedDate, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}</strong>
              </div>
              <div>
                <span>Time</span>
                <strong>{formatTime(confirmation.selectedTime)} GMT</strong>
              </div>
              <div>
                <span>Reference</span>
                <strong className="mono">{confirmation.reference}</strong>
              </div>
            </div>

            <div className="demo-success-actions">
              <button type="button" className="btn-lg" onClick={downloadCalendarInvite}>
                <Download size={16} /> Add to calendar
              </button>
              <button type="button" className="btn-out-lg" onClick={() => setPage('home')}>
                Return to website
              </button>
            </div>
          </Reveal>
        </main>
        <Footer />
      </>
    )
  }

  return (
    <>
      <main className="demo-page">
        <section className="demo-intro">
          <Reveal>
            <div className="demo-kicker">{enterpriseEnquiry ? 'Enterprise sales consultation' : 'Talk to our product team'}</div>
            <h1 className="demo-title serif">
              {enterpriseEnquiry ? 'Plan a governed AgroOS rollout.' : 'See how AgroOS fits your operation.'}
            </h1>
            <p className="demo-lead">
              {enterpriseEnquiry
                ? 'A working session for unions, lenders, NGOs, and programme teams evaluating a multi-cooperative deployment.'
                : 'A focused consultation for cooperative leaders, programme teams, and financial partners evaluating AgroOS.'}
            </p>

            <div className="demo-value-list">
              {[
                [Video, enterpriseEnquiry ? 'A focused enterprise discovery session' : 'A tailored 30-minute walkthrough'],
                [Users, enterpriseEnquiry ? 'Rollout scope, migration, and governance' : 'Your workflows, scale, and implementation needs'],
                [ShieldCheck, enterpriseEnquiry ? 'Security, API, SLA, and compliance review' : 'Security, payments, and compliance questions'],
              ].map(([Icon, label]) => (
                <div className="demo-value" key={label}>
                  <span><Icon size={18} /></span>
                  <p>{label}</p>
                </div>
              ))}
            </div>

            <div className="demo-assurance">
              <strong>What happens next</strong>
              <p>Choose a preferred slot. Our team will verify availability and send the video-call details to your work email.</p>
            </div>
          </Reveal>
        </section>

        <section className="demo-form-section">
          <Reveal className="demo-form-wrap" delay={0.05}>
            <div className="demo-form-heading">
              <div>
                <div className="demo-kicker">Schedule a consultation</div>
                <h2 className="serif">Tell us about your organisation</h2>
              </div>
              <div className="demo-duration"><Clock3 size={15} /> 30 min · GMT</div>
            </div>

            <form onSubmit={submitRequest} noValidate>
              {error && <div className="auth-error demo-error" role="alert">{error}</div>}

              <div className="demo-fields">
                <label className="demo-field">
                  <span><UserRound size={14} /> Full name *</span>
                  <input className="auth-input" name="name" autoComplete="name" value={form.name} onChange={updateField} placeholder="Kwame Boateng" required />
                </label>
                <label className="demo-field">
                  <span><Mail size={14} /> Work email *</span>
                  <input className="auth-input" name="email" type="email" autoComplete="email" value={form.email} onChange={updateField} placeholder="you@organisation.com" required />
                </label>
                <label className="demo-field">
                  <span><Building2 size={14} /> Organisation *</span>
                  <input className="auth-input" name="cooperative" autoComplete="organization" value={form.cooperative} onChange={updateField} placeholder="Ashanti Farmers Cooperative" required />
                </label>
                <label className="demo-field">
                  <span><Phone size={14} /> Phone number</span>
                  <input className="auth-input" name="phone" type="tel" autoComplete="tel" value={form.phone} onChange={updateField} placeholder="+233 24 000 0000" />
                </label>
                <label className="demo-field">
                  <span><Users size={14} /> Organisation size</span>
                  <select className="auth-input auth-select" name="size" value={form.size} onChange={updateField}>
                    {SIZES.map((size) => <option key={size}>{size}</option>)}
                  </select>
                </label>
                <label className="demo-field">
                  <span>Primary area of interest</span>
                  <select className="auth-input auth-select" name="topic" value={form.topic} onChange={updateField}>
                    {TOPICS.map((topic) => <option key={topic}>{topic}</option>)}
                  </select>
                </label>
              </div>

              <div className="demo-schedule">
                <div className="demo-section-label"><CalendarDays size={16} /> Preferred date</div>
                <div className="demo-date-picker">
                  <input
                    className="auth-input"
                    type="date"
                    min={minimumDate}
                    value={selectedDate}
                    onChange={chooseDate}
                    aria-label="Preferred consultation date"
                  />
                  <p>Select any future date. Our team will confirm availability by email.</p>
                </div>

                <div className="demo-section-label"><Clock3 size={16} /> Preferred time <span>GMT</span></div>
                <div className="demo-time-grid">
                  {TIMES.map((time) => {
                    const active = selectedTime === time
                    return (
                      <button type="button" className={`demo-time${active ? ' active' : ''}`} key={time} disabled={!selectedDate} onClick={() => { setSelectedTime(time); setError('') }} aria-pressed={active}>
                        {active && <Check size={14} />} {formatTime(time)}
                      </button>
                    )
                  })}
                </div>
              </div>

              <label className="demo-field demo-notes">
                <span>Context for the conversation</span>
                <textarea className="auth-input" name="notes" value={form.notes} onChange={updateField} rows={3} placeholder="Tell us about your current process, priorities, or implementation timeline." />
              </label>

              <div className="demo-submit-row">
                <p><ShieldCheck size={14} /> Your information is used only to arrange this consultation.</p>
                <button type="submit" className="btn-lg" disabled={submitting}>
                  {submitting ? 'Saving request…' : <>Request consultation <ArrowRight size={16} /></>}
                </button>
              </div>
            </form>
          </Reveal>
        </section>
      </main>
      <Footer />
    </>
  )
}
