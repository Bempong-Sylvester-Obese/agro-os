import React from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Payments from './Payments'

vi.mock('../../api/transactions', () => ({
  fetchTransactionReceipt: vi.fn(),
  reconcileTransaction: vi.fn(),
}))

vi.mock('../Motion', () => ({
  ModalPresence: ({ show, children }) => show ? children : null,
}))

const farmers = [{
  id: 4,
  name: 'Ama Mensah',
  membership_status: 'active',
  phone: '0200000000',
}]

describe('Payments operations', () => {
  afterEach(cleanup)

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('keeps payment initiation on farmer USSD', () => {
    render(<Payments farmers={farmers} transactions={[]} loading={false} />)

    expect(screen.queryByRole('button', { name: 'Collect Dues' })).toBeNull()
    expect(screen.getByText(/members initiate dues and loan repayments through AgroOS USSD/i)).toBeTruthy()
    expect(screen.queryByLabelText(/OTP/i)).toBeNull()
  })

  it('labels durable customer-action states', () => {
    render(
      <Payments
        farmers={farmers}
        loading={false}
        transactions={[{
          id: 21,
          farmer_id: 4,
          amount: 50,
          channel: '13',
          status: 'pending',
          customer_action: 'otp',
          created_at: '2026-07-15T10:00:00Z',
        }]}
      />
    )

    expect(screen.getByText('Awaiting member OTP')).toBeTruthy()
  })
})
