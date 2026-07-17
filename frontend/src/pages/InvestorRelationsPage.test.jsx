import React from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import Footer from '../components/Footer'
import InvestorRelationsPage from './InvestorRelationsPage'

function LocationProbe() {
  const location = useLocation()
  return <div data-testid="location">{location.pathname}{location.search}</div>
}

describe('Investor relations page', () => {
  afterEach(cleanup)

  beforeEach(() => {
    window.scrollTo = () => undefined
  })

  it('links Investor relations from the Company footer column', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<Footer />} />
          <Route path="/investors" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>,
    )

    const link = screen.getByRole('link', { name: 'Investor relations' })
    expect(link.getAttribute('href')).toBe('/investors')
    fireEvent.click(link)
    expect(screen.getByTestId('location').textContent).toBe('/investors')
  })

  it('renders the IR hub sections and honest empty financial archive', () => {
    render(
      <MemoryRouter initialEntries={['/investors']}>
        <Routes>
          <Route path="/investors" element={<InvestorRelationsPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: 'Investor relations' })).toBeTruthy()
    expect(screen.getByRole('navigation', { name: 'Investor relations sections' })).toBeTruthy()
    expect(document.getElementById('overview')).toBeTruthy()
    expect(document.getElementById('why-agroos')).toBeTruthy()
    expect(document.getElementById('financials')).toBeTruthy()
    expect(document.getElementById('news-events')).toBeTruthy()
    expect(document.getElementById('governance')).toBeTruthy()
    expect(document.getElementById('resources')).toBeTruthy()
    expect(document.getElementById('contact')).toBeTruthy()
    expect(screen.getByText(/No securities are being offered here/i)).toBeTruthy()
    expect(screen.getAllByText('Not yet published').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'investors@agroos.app' }).getAttribute('href')).toBe(
      'mailto:investors@agroos.app',
    )
  })

  it('routes the investor briefing CTA to the enterprise book-demo topic', () => {
    render(
      <MemoryRouter initialEntries={['/investors']}>
        <Routes>
          <Route path="/investors" element={<InvestorRelationsPage />} />
          <Route path="/book-demo" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>,
    )

    const cta = screen.getByRole('link', { name: 'Request investor briefing' })
    expect(cta.getAttribute('href')).toBe('/book-demo?plan=enterprise&topic=Investor+relations')
    fireEvent.click(cta)
    expect(screen.getByTestId('location').textContent).toBe(
      '/book-demo?plan=enterprise&topic=Investor+relations',
    )
  })
})
