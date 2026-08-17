import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import React from 'react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SubscriptionPage from './SubscriptionPage'

const apiMocks = vi.hoisted(() => ({
  fetchPlans: vi.fn(),
  createPreCheckout: vi.fn(),
}))

vi.mock('../api/plans', () => ({
  fetchPlans: apiMocks.fetchPlans,
  createPreCheckout: apiMocks.createPreCheckout,
}))

const PLANS = [
  { key: 'growth', track: 'cooperative', name: 'Growth', price: 'GHS 299', cadence: 'per organisation / month', description: 'x', features: [], cta: 'Start Growth onboarding', bands: [
    { key: 'base', label: 'Up to 50 members', price: 299 },
    { key: 'plus_50', label: 'Up to 100 members', price: 449 },
  ] },
  { key: 'starter', track: 'cooperative', name: 'Starter', price: 'Free', cadence: 'No card required', description: 'x', features: [], cta: 'Create free workspace', bands: null },
]

function LoginProbe() {
  const location = useLocation()
  return <div data-testid="login-location">{location.search}</div>
}

describe('SubscriptionPage', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
    globalThis.IntersectionObserver = class { observe() {} unobserve() {} disconnect() {} }
    window.scrollTo = () => undefined
    apiMocks.fetchPlans.mockResolvedValue(PLANS)
    apiMocks.createPreCheckout.mockReset()
  })

  it('shows the real band total and creates a checkout for paid plans', async () => {
    apiMocks.createPreCheckout.mockResolvedValue({ authorization_url: 'https://pay/moolre', reference: 'sub_pre_x' })
    render(
      <MemoryRouter initialEntries={['/subscribe/growth?band=plus_50']}>
        <Routes>
          <Route path="/subscribe/:plan" element={<SubscriptionPage />} />
          <Route path="/login" element={<LoginProbe />} />
        </Routes>
      </MemoryRouter>,
    )

    fireEvent.change(await screen.findByLabelText(/Organisation name/i), { target: { value: 'Ashanti Farmers Cooperative' } })
    fireEvent.change(screen.getByLabelText(/Expected member count/i), { target: { value: '125' } })
    fireEvent.click(screen.getByRole('button', { name: /Review plan and terms/i }))

    expect(screen.getAllByText('GHS 449').length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole('button', { name: /Pay GHS 449/i }))

    await waitFor(() => expect(apiMocks.createPreCheckout).toHaveBeenCalledWith(expect.objectContaining({
      plan_key: 'growth',
      band: 'plus_50',
      organisation: 'Ashanti Farmers Cooperative',
    })))
  })
})
