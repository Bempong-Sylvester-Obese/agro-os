import React from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/plans', () => ({
  fetchPlans: vi.fn(),
}))

import PricingPage from './PricingPage'
import { fetchPlans } from '../api/plans'

const PLANS = [
  { key: 'starter', track: 'cooperative', name: 'Starter', price: 'Free', cadence: 'No card required', description: 'x', features: [], cta: 'Create free workspace', bands: null },
  { key: 'growth', track: 'cooperative', name: 'Growth', price: 'GHS 299', cadence: 'per organisation / month', description: 'x', features: [], cta: 'Start Growth onboarding', featured: true, bands: [
    { key: 'base', label: 'Up to 50 members', price: 299 },
    { key: 'plus_50', label: 'Up to 100 members', price: 449 },
  ] },
  { key: 'enterprise', track: 'cooperative', name: 'Enterprise', price: 'Custom', cadence: 'Annual agreement', description: 'x', features: [], cta: 'Talk to enterprise sales', bands: null },
  { key: 'solo', track: 'farmer', name: 'Solo Farm', price: 'GHS 99', cadence: 'per farm / month', description: 'x', features: [], cta: 'Start Solo Farm onboarding', bands: [
    { key: 'w20', label: 'Up to 20 workers', price: 99 },
    { key: 'w50', label: 'Up to 50 workers', price: 199 },
    { key: 'custom', label: 'Custom worker count', price: null },
  ] },
]

function LocationProbe() {
  const location = useLocation()
  return <div data-testid="loc">{location.pathname}{location.search}</div>
}

describe('PricingPage', () => {
  beforeEach(() => {
    fetchPlans.mockResolvedValue(PLANS)
    globalThis.IntersectionObserver = class { observe() {} unobserve() {} disconnect() {} }
    window.scrollTo = () => undefined
  })
  afterEach(cleanup)

  it('renders two tracks', async () => {
    render(<MemoryRouter initialEntries={['/pricing']}><PricingPage /></MemoryRouter>)
    expect(await screen.findByText(/For Cooperatives/i)).toBeTruthy()
    expect(screen.getByText(/For Independent Farmers/i)).toBeTruthy()
  })

  it('selecting a Growth band updates price and navigates with band', async () => {
    render(
      <MemoryRouter initialEntries={['/pricing']}>
        <Routes>
          <Route path="/pricing" element={<PricingPage />} />
          <Route path="/subscribe/:plan" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>,
    )
    await screen.findByText(/For Cooperatives/i)
    const growthBand = screen.getAllByRole('combobox')[0]
    fireEvent.change(growthBand, { target: { value: 'plus_50' } })
    expect(await screen.findByText('GHS 449')).toBeTruthy()
    fireEvent.click(screen.getAllByRole('button', { name: /Start Growth onboarding/i })[0])
    expect(screen.getByTestId('loc').textContent).toBe('/subscribe/growth?band=plus_50')
  })

  it('routes a custom Solo Farm band to sales instead of checkout', async () => {
    render(
      <MemoryRouter initialEntries={['/pricing']}>
        <Routes>
          <Route path="/pricing" element={<PricingPage />} />
          <Route path="/book-demo" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>,
    )
    await screen.findByText(/For Independent Farmers/i)
    const soloBand = screen.getAllByRole('combobox')[1]
    fireEvent.change(soloBand, { target: { value: 'custom' } })
    expect(screen.getAllByText('Custom').length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole('button', { name: /Talk to sales/i }))
    expect(screen.getByTestId('loc').textContent).toBe('/book-demo?plan=solo&band=custom&topic=Custom+plan')
  })
})
