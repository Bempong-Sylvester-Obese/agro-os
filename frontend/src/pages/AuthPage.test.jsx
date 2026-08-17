import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import AuthPage from './AuthPage'

const authMocks = vi.hoisted(() => ({
  signup: vi.fn(),
  warmAuthBackend: vi.fn(() => Promise.resolve()),
}))

vi.mock('../api/auth', () => ({
  acceptInvite: vi.fn(),
  changePassword: vi.fn(),
  confirmPasswordReset: vi.fn(),
  login: vi.fn(),
  requestPasswordReset: vi.fn(),
  signup: authMocks.signup,
  storeAuthToken: vi.fn(),
  userFromAuthToken: vi.fn(() => null),
  userFromSignupResponse: vi.fn(() => ({})),
  warmAuthBackend: authMocks.warmAuthBackend,
}))

describe('AuthPage subscription signup', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
    authMocks.signup.mockReset()
    window.sessionStorage.setItem('agroos-subscription-intent', JSON.stringify({
      plan: 'growth',
      organisation: 'Test Cooperative',
      location: 'Accra',
      memberCount: '125',
      role: 'Finance or operations lead',
    }))
  })

  afterEach(cleanup)

  function renderSignup() {
    render(
      <MemoryRouter initialEntries={['/login?mode=signup&plan=growth&onboarding=subscription']}>
        <AuthPage onAuth={vi.fn()} />
      </MemoryRouter>,
    )
  }

  function submitSignup() {
    fireEvent.click(screen.getByRole('button', { name: /Continue/i }))
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'admin@example.com' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret123' } })
    fireEvent.click(screen.getByRole('button', { name: /Create Growth account/i }))
  }

  it('keeps the intent when signup fails', async () => {
    authMocks.signup.mockRejectedValue(new Error('Signup failed'))
    renderSignup()
    submitSignup()

    await screen.findByText('Signup failed')
    expect(window.sessionStorage.getItem('agroos-subscription-intent')).not.toBeNull()
  })

  it('submits plan and role together and removes the intent after success', async () => {
    authMocks.signup.mockResolvedValue({ access_token: 'token' })
    renderSignup()
    submitSignup()

    await waitFor(() => expect(authMocks.signup).toHaveBeenCalledWith(expect.objectContaining({
      subscriptionPlan: 'growth',
      onboardingRole: 'Finance or operations lead',
    })))
    await waitFor(() => {
      expect(window.sessionStorage.getItem('agroos-subscription-intent')).toBeNull()
    })
  })

  it('sends checkout_ref and band for a paid subscription signup', async () => {
    window.sessionStorage.setItem('agroos-subscription-intent', JSON.stringify({
      plan: 'growth',
      band: 'plus_50',
      organisation: 'Test Cooperative',
      location: 'Accra',
      memberCount: '125',
      role: 'Finance or operations lead',
      checkout_ref: 'sub_pre_abc123',
    }))
    authMocks.signup.mockResolvedValue({ access_token: 'token' })

    render(
      <MemoryRouter initialEntries={['/login?mode=signup&plan=growth&onboarding=subscription&checkout=sub_pre_abc123']}>
        <AuthPage onAuth={vi.fn()} />
      </MemoryRouter>,
    )
    submitSignup()

    await waitFor(() => expect(authMocks.signup).toHaveBeenCalledWith(expect.objectContaining({
      subscriptionPlan: 'growth',
      subscriptionBand: 'plus_50',
      checkoutRef: 'sub_pre_abc123',
    })))
  })

  it('restores Solo Farm organization type from the paid intent', async () => {
    window.sessionStorage.setItem('agroos-subscription-intent', JSON.stringify({
      plan: 'solo',
      band: 'w20',
      organisation: 'Test Farm',
      memberCount: '25',
      org_type: 'solo_farm',
      checkout_ref: 'sub_pre_solo123',
    }))
    authMocks.signup.mockResolvedValue({ access_token: 'token' })

    render(
      <MemoryRouter initialEntries={['/login?mode=signup&plan=solo&onboarding=subscription&checkout=sub_pre_solo123']}>
        <AuthPage onAuth={vi.fn()} />
      </MemoryRouter>,
    )
    expect(screen.getByLabelText('Organization type').value).toBe('solo_farm')
    fireEvent.click(screen.getByRole('button', { name: /Continue/i }))
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'solo@example.com' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret123' } })
    fireEvent.click(screen.getByRole('button', { name: /Create Solo Farm account/i }))

    await waitFor(() => expect(authMocks.signup).toHaveBeenCalledWith(expect.objectContaining({
      subscriptionPlan: 'solo',
      organizationType: 'solo_farm',
      checkoutRef: 'sub_pre_solo123',
    })))
  })
})
