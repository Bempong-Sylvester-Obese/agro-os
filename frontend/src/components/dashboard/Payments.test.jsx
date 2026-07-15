import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Payments from './Payments'
import * as transactionsApi from '../../api/transactions'

vi.mock('../../api/transactions', () => ({
  collectDues: vi.fn(),
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

  it('leaves OTP completion with the member after sending one request', async () => {
    transactionsApi.collectDues.mockResolvedValue({
      status: 'verification_required',
      customer_action: 'otp',
      transaction_id: 21,
    })
    render(<Payments farmers={farmers} transactions={[]} loading={false} />)

    fireEvent.click(screen.getByRole('button', { name: 'Collect Dues' }))
    fireEvent.change(screen.getByLabelText('Member'), { target: { value: '4' } })
    fireEvent.change(screen.getByLabelText('Amount (GHS)'), { target: { value: '50' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send Payment Prompt' }))

    await waitFor(() => expect(transactionsApi.collectDues).toHaveBeenCalledTimes(1))
    expect(await screen.findByText(/member must enter their OTP through AgroOS USSD/i)).toBeTruthy()
    expect(screen.queryByLabelText(/OTP/i)).toBeNull()
    expect(screen.queryByRole('button', { name: /submit OTP/i })).toBeNull()
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
