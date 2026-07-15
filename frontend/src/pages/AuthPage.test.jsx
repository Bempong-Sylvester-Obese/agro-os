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
  login: vi.fn(),
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
})
