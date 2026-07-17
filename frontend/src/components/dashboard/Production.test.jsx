import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Production from './Production'
import { logProduction } from '../../api/production'

vi.mock('../../api/production', () => ({ logProduction: vi.fn() }))
vi.mock('../../api/reports', () => ({ exportDashboardReport: vi.fn() }))
vi.mock('../Motion', () => ({
  ModalPresence: ({ show, children }) => show ? children : null,
}))

const farmers = [
  {
    id: 1,
    name: 'Crop Farmer',
    phone: '0200000001',
    membership_status: 'active',
    production_focus: 'crop',
  },
  {
    id: 2,
    name: 'Mixed Farmer',
    phone: '0200000002',
    membership_status: 'active',
    production_focus: 'mixed',
  },
]

describe('unified production dashboard', () => {
  afterEach(cleanup)
  beforeEach(() => {
    vi.clearAllMocks()
    logProduction.mockResolvedValue({ id: 10 })
  })

  it('adapts the form and requires a production type for mixed members', async () => {
    render(<Production farmers={farmers} productions={[]} cooperativeId={1} loading={false} onRefresh={vi.fn()} />)

    fireEvent.click(screen.getByRole('button', { name: 'Log production' }))
    fireEvent.change(screen.getByLabelText('Member'), { target: { value: '2' } })
    expect(screen.getByLabelText('Production type')).toBeTruthy()

    fireEvent.change(screen.getByLabelText('Production type'), { target: { value: 'animal' } })
    expect(screen.getByLabelText('Animal product')).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Animal product'), { target: { value: 'Eggs' } })
    fireEvent.change(screen.getByLabelText('Activity / output'), { target: { value: 'Egg collection' } })
    fireEvent.change(screen.getByLabelText('Expected output'), { target: { value: '30' } })
    fireEvent.change(screen.getByLabelText('Actual output'), { target: { value: '24' } })
    fireEvent.change(screen.getByLabelText('Unit'), { target: { value: 'crates' } })
    fireEvent.change(screen.getByLabelText('Production date'), { target: { value: '2026-07-17' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save production log' }))

    await waitFor(() => expect(logProduction).toHaveBeenCalledWith({
      farmerId: '2',
      productionKind: 'animal',
      productName: 'Eggs',
      activity: 'Egg collection',
      unit: 'crates',
      expectedQuantity: '30',
      quantity: '24',
      productionDate: '2026-07-17',
    }))
  })

  it('locks crop members to crop fields', () => {
    render(<Production farmers={farmers} productions={[]} cooperativeId={1} loading={false} />)

    fireEvent.click(screen.getByRole('button', { name: 'Log production' }))
    fireEvent.change(screen.getByLabelText('Member'), { target: { value: '1' } })

    expect(screen.queryByLabelText('Production type')).toBeNull()
    expect(screen.getByLabelText('Crop product')).toBeTruthy()
  })

  it('keeps unit totals separate and displays legacy crop records', () => {
    const productions = [
      { id: 1, farmer_id: 1, crop_type: 'Maize', expected_kg: 120, quantity_kg: 100, harvest_date: '2026-07-01' },
      { id: 2, farmer_id: 2, production_kind: 'animal', product_name: 'Milk', activity: 'Milk collection', unit: 'litres', expected_quantity: 50, quantity: 40, production_date: '2026-07-02' },
    ]
    render(<Production farmers={farmers} productions={productions} cooperativeId={1} loading={false} />)

    expect(screen.getByText('100 kg · 40 litres')).toBeTruthy()
    expect(screen.getByText('120 kg · 50 litres')).toBeTruthy()
    expect(screen.getAllByText('Maize').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Milk').length).toBeGreaterThan(0)
  })
})
