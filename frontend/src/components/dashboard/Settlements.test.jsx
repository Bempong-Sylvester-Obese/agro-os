import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Settlements from './Settlements'
import { calculateSettlement, retrySettlement } from '../../api/commerce'

vi.mock('../../api/commerce', () => ({
  approveSettlement: vi.fn(),
  calculateSettlement: vi.fn(),
  paySettlement: vi.fn(),
  retrySettlement: vi.fn(),
  reviewSettlement: vi.fn(),
}))

const farmer = { id: 4, name: 'Ama Mensah' }
const verifiedSale = { id: 9, status: 'verified', total_amount: 1000 }

describe('farmer settlements', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(cleanup)

  it('gates settlement calculation on verified buyer funds', () => {
    render(<Settlements settlements={[]} sales={[{ id: 2, status: 'confirmed' }]} farmers={[farmer]} />)

    expect(screen.getByText(/no verified buyer funds are available/i)).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Calculate settlement' })).toBeNull()
  })

  it('shows an understandable per-farmer gross, deductions, and net preview', async () => {
    calculateSettlement.mockResolvedValue({
      id: 18,
      status: 'calculated',
      farmer_lines: [{
        farmer_id: 4,
        accepted_quantity_kg: 100,
        unit_price: 10,
        gross_amount: 1000,
        deductions: [
          { label: 'Cooperative fee', amount: 50 },
          { label: 'Loan recovery', amount: 100 },
        ],
        total_deductions: 150,
        net_payable: 850,
      }],
    })
    render(<Settlements settlements={[]} sales={[verifiedSale]} farmers={[farmer]} />)

    fireEvent.change(screen.getByLabelText('Verified sale'), { target: { value: '9' } })
    fireEvent.click(screen.getByRole('button', { name: 'Calculate settlement' }))

    await waitFor(() => expect(screen.getByText('Farmer settlement preview')).toBeTruthy())
    expect(screen.getByText('Ama Mensah')).toBeTruthy()
    expect(screen.getByText(/Cooperative fee: GHS 50.00/)).toBeTruthy()
    expect(screen.getByText(/Loan recovery: GHS 100.00/)).toBeTruthy()
    expect(screen.getByText('GHS 850.00')).toBeTruthy()
  })

  it('offers retry only for failed transfers', async () => {
    retrySettlement.mockResolvedValue({})
    render(
      <Settlements
        sales={[verifiedSale]}
        farmers={[farmer]}
        settlements={[
          {
            id: 20,
            status: 'partially_failed',
            lines: [
              { id: 1, farmer_id: 4, payout_status: 'paid' },
              { id: 2, farmer_id: 5, payout_status: 'failed' },
            ],
          },
          {
            id: 21,
            status: 'paid',
            lines: [{ id: 3, farmer_id: 6, payout_status: 'paid' }],
          },
        ]}
      />,
    )

    const retry = screen.getByRole('button', { name: 'Retry 1 failed transfers for settlement 20' })
    expect(screen.queryByRole('button', { name: /retry.*settlement 21/i })).toBeNull()
    fireEvent.click(retry)

    await waitFor(() => expect(retrySettlement).toHaveBeenCalledWith(20))
  })
})
