import React from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'
import Navbar from './Navbar'

afterEach(cleanup)

function renderNav(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Navbar />
    </MemoryRouter>,
  )
}

function activeTabLabels() {
  return screen.getAllByRole('link')
    .filter((el) => el.classList.contains('nav-tab') && el.classList.contains('active'))
    .map((el) => el.textContent)
}

describe('Navbar tab highlight', () => {
  it('highlights only Book demo on /book-demo', () => {
    renderNav('/book-demo')
    expect(activeTabLabels()).toEqual(['Book demo'])
  })

  it('highlights only Home on /', () => {
    renderNav('/')
    expect(activeTabLabels()).toEqual(['Home'])
  })

  it('highlights only Pricing on /pricing', () => {
    renderNav('/pricing')
    expect(activeTabLabels()).toEqual(['Pricing'])
  })
})
