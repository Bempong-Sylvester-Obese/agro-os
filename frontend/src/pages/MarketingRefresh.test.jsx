import React from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import HomePage from './HomePage'
import SolutionsPage from './SolutionsPage'

function LocationProbe() {
  const location = useLocation()
  return <div data-testid="location">{location.pathname}{location.search}</div>
}

describe('marketing refresh', () => {
  afterEach(cleanup)

  beforeEach(() => {
    globalThis.IntersectionObserver = class {
      observe() { return undefined }
      unobserve() { return undefined }
      disconnect() { return undefined }
    }
    window.scrollTo = () => undefined
  })

  it('routes the homepage primary action into Starter onboarding', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/subscribe/:plan" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>,
    )

    fireEvent.click(screen.getAllByRole('button', { name: /Create free workspace/i })[0])
    expect(screen.getByTestId('location').textContent).toBe('/subscribe/starter')
  })

  it('matches the implemented USSD main menu and enterprise route', () => {
    render(
      <MemoryRouter initialEntries={['/solutions']}>
        <Routes>
          <Route path="/solutions" element={<SolutionsPage />} />
          <Route path="/book-demo" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>,
    )

    const menu = screen.getByLabelText('AgroOS USSD main menu preview')
    expect(menu.textContent).toContain('Welcome to AgroOS')
    expect(menu.textContent).toContain('1. Check Loan Balance')
    expect(menu.textContent).toContain('2. Pay Dues')
    expect(menu.textContent).toContain('3. Announcements')
    expect(menu.textContent).toContain('Reply 1–3')
    expect(menu.textContent).not.toContain('*920#')

    fireEvent.click(screen.getByRole('button', { name: /Discuss enterprise rollout/i }))
    expect(screen.getByTestId('location').textContent).toContain('/book-demo?enterprise=true')
    expect(screen.getByTestId('location').textContent).toContain('topic=Solutions+consultation')
  })
})
