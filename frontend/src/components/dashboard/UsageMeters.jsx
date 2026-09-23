// src/components/dashboard/UsageMeters.jsx
import React from 'react'

const METERS = [
  { key: 'members', label: 'Active members' },
  { key: 'workers', label: 'Active workers' },
  { key: 'sms', label: 'SMS sent this month' },
]

// Feature flags worth surfacing on the billing panel, in display order.
const FEATURE_ORDER = ['loans', 'scores', 'ussd', 'commerce', 'sms', 'workers', 'payroll']

function barColor(pct) {
  if (pct >= 100) return '#EF4444'
  if (pct >= 90) return '#F59E0B'
  if (pct >= 70) return '#3B82F6'
  return '#10B981'
}

function Meter({ label, meter }) {
  if (!meter || meter.included === false) return null
  const { used, limit, unlimited, percent } = meter
  const pct = unlimited ? 0 : Math.min(percent ?? 0, 100)
  return (
    <div style={{ marginBottom: 12 }} data-testid={`usage-meter-${label}`}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
        <span>
          {label}: {used.toLocaleString()} of {unlimited ? 'unlimited' : limit.toLocaleString()}
        </span>
        {!unlimited && <span>{pct}%</span>}
      </div>
      <div style={{ height: 8, background: '#E5E7EB', borderRadius: 4, overflow: 'hidden' }}>
        <div
          style={{
            height: '100%',
            width: `${unlimited ? 100 : pct}%`,
            background: unlimited ? '#10B981' : barColor(pct),
            opacity: unlimited ? 0.35 : 1,
            borderRadius: 4,
            transition: 'width .3s ease',
          }}
        />
      </div>
    </div>
  )
}

/**
 * Usage vs plan limits, driven entirely by `GET /cooperatives/{id}/usage`
 * (the same numbers the API enforces). Renders nothing until usage loads.
 */
export default function UsageMeters({ usage, error }) {
  if (error) {
    return (
      <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 16 }}>
        Usage is unavailable right now ({error}).
      </div>
    )
  }
  if (!usage) return null
  const limits = usage.limits || {}
  const features = usage.features || {}
  const labels = usage.feature_labels || {}
  const visibleFeatures = FEATURE_ORDER.filter((key) => key in features)

  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Usage &amp; limits</div>
      {METERS.map(({ key, label }) => (
        <Meter key={key} label={label} meter={limits[key]} />
      ))}
      {visibleFeatures.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }} aria-label="Plan features">
          {visibleFeatures.map((key) => {
            const on = Boolean(features[key])
            return (
              <span
                key={key}
                title={on ? 'Included in your plan' : 'Upgrade to enable'}
                style={{
                  fontSize: 11,
                  padding: '3px 8px',
                  borderRadius: 999,
                  border: '1px solid',
                  borderColor: on ? '#A7F3D0' : 'var(--border)',
                  background: on ? '#ECFDF5' : 'var(--background)',
                  color: on ? '#047857' : 'var(--muted)',
                  textDecoration: on ? 'none' : 'line-through',
                }}
              >
                {labels[key] || key}
              </span>
            )
          })}
        </div>
      )}
    </div>
  )
}
