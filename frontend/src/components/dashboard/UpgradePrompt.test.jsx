import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import UpgradePrompt from './UpgradePrompt'
import { ApiError, apiErrorFromBody, detailToMessage, isEntitlementError } from '../../api/config'

describe('entitlement error helpers', () => {
  it('extracts the message from a structured detail', () => {
    expect(detailToMessage('plain')).toBe('plain')
    expect(detailToMessage({ code: 'plan_limit_reached', message: 'Member limit of 10 reached.' })).toBe(
      'Member limit of 10 reached.',
    )
    expect(detailToMessage(null, 'fallback')).toBe('fallback')
  })

  it('keeps the structured detail on the ApiError', () => {
    const err = apiErrorFromBody(
      { detail: { code: 'sms_quota_exceeded', message: 'SMS quota of 100 exceeded.', used: 100, limit: 100 } },
      403,
      'Failed',
    )
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(403)
    expect(err.message).toBe('SMS quota of 100 exceeded.')
    expect(isEntitlementError(err)).toBe(true)
    expect(isEntitlementError(new Error('nope'))).toBe(false)
  })
})

describe('UpgradePrompt', () => {
  it('renders an upgrade call-to-action for entitlement errors', () => {
    const err = apiErrorFromBody(
      {
        detail: {
          code: 'plan_limit_reached',
          message: 'Member limit of 10 reached for the starter plan. Upgrade to add more.',
          limit_key: 'max_members',
          limit: 10,
          used: 10,
          plan: 'starter',
        },
      },
      403,
    )
    const { unmount } = render(<UpgradePrompt error={err} />)
    expect(screen.getByRole('alert').dataset.entitlementCode).toBe('plan_limit_reached')
    expect(screen.getByText('Plan limit reached')).toBeTruthy()
    expect(screen.getByText(/Member limit of 10 reached/)).toBeTruthy()
    expect(screen.getByText('Using 10 of 10.')).toBeTruthy()
    expect(screen.getByRole('link', { name: /View plans/ }).getAttribute('href')).toBe('/dashboard/settings')
    unmount()
  })

  it('falls back to the plain message for other errors', () => {
    const { unmount } = render(<UpgradePrompt error={new Error('Phone already registered')} />)
    expect(screen.getByRole('alert').textContent).toBe('Phone already registered')
    expect(screen.queryByRole('link')).toBeNull()
    unmount()
  })

  it('renders nothing without an error', () => {
    const { container } = render(<UpgradePrompt error={null} />)
    expect(container.innerHTML).toBe('')
  })
})
