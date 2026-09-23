// src/components/dashboard/UpgradePrompt.jsx
import React from 'react'
import { isEntitlementError } from '../../api/config'
import { dashboardPath } from '../../constants/routes'

const TITLES = {
  plan_limit_reached: 'Plan limit reached',
  sms_quota_exceeded: 'SMS quota exceeded',
  feature_not_in_plan: 'Not included in your plan',
}

/**
 * Soft-limit UX for entitlement errors (403 with a structured `detail`).
 * Renders the API message plus a link to the billing panel; for any other
 * error it renders the plain message so callers can use it unconditionally.
 */
export default function UpgradePrompt({ error, className = 'dashboard-form-error' }) {
  if (!error) return null
  const message = error.message || String(error)
  if (!isEntitlementError(error)) {
    return <div role="alert" className={className}>{message}</div>
  }
  const { code, used, limit } = error.detail
  return (
    <div role="alert" className={className} data-entitlement-code={code}>
      <div style={{ fontWeight: 700, marginBottom: 2 }}>{TITLES[code] || 'Upgrade required'}</div>
      <div>{message}</div>
      {typeof used === 'number' && typeof limit === 'number' && limit > 0 && (
        <div style={{ fontSize: 12, opacity: 0.85, marginTop: 2 }}>Using {used} of {limit}.</div>
      )}
      <a
        href={dashboardPath('settings')}
        style={{ display: 'inline-block', marginTop: 6, fontWeight: 600, textDecoration: 'underline' }}
      >
        View plans &amp; usage
      </a>
    </div>
  )
}
