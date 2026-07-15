import { fireEvent, render, screen } from '@testing-library/react'
import React from 'react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import SubscriptionPage from './SubscriptionPage'

function LoginProbe() {
  const location = useLocation()
  return <div data-testid="login-location">{location.search}</div>
}

describe('SubscriptionPage', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
    globalThis.IntersectionObserver = class {
      observe() { return undefined }
      unobserve() { return undefined }
      disconnect() { return undefined }
    }
    window.scrollTo = () => undefined
  })

  it('preserves Growth plan context through the account-setup handoff', () => {
    render(
      <MemoryRouter initialEntries={['/subscribe/growth']}>
        <Routes>
          <Route path="/subscribe/:plan" element={<SubscriptionPage />} />
          <Route path="/login" element={<LoginProbe />} />
        </Routes>
      </MemoryRouter>,
    )

    fireEvent.change(screen.getByLabelText(/Organisation name/i), { target: { value: 'Ashanti Farmers Cooperative' } })
    fireEvent.change(screen.getByLabelText(/Expected member count/i), { target: { value: '125' } })
    fireEvent.click(screen.getByRole('button', { name: /Review plan and terms/i }))

    expect(screen.getAllByText('GHS 299')).toHaveLength(2)
    expect(screen.getByText('Ashanti Farmers Cooperative')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /Continue to account setup/i }))

    expect(screen.getByTestId('login-location').textContent).toContain('plan=growth')
    const intent = JSON.parse(window.sessionStorage.getItem('agroos-subscription-intent'))
    expect(intent).toMatchObject({
      plan: 'growth',
      organisation: 'Ashanti Farmers Cooperative',
      memberCount: '125',
    })
  })
})
