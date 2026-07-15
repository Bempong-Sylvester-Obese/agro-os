import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Loans from './Loans'
import * as loansApi from '../../api/loans'

vi.mock('../../api/loans', () => ({
  createLoan: vi.fn(),
  approveLoan: vi.fn(),
  rejectLoan: vi.fn(),
  disburseLoan: vi.fn(),
  cancelLoan: vi.fn(),
  fetchDisbursementStatus: vi.fn(),
  repayLoan: vi.fn(),
  verifyLoanRepayment: vi.fn(),
  RepaymentVerificationRequiredError: class extends Error {},
}))

vi.mock('../Motion', () => ({
  ModalPresence: ({ show, children }) => show ? children : null,
}))

const farmers = [{ id: 4, name: 'Ama Mensah', membership_status: 'active', phone: '0200000000' }]

function loan(overrides = {}) {
  return {
    id: 12,
    farmer_id: 4,
    amount: 1500,
    purpose: 'Seeds',
    repayment_date: '2026-09-01',
    created_at: '2026-07-01T10:00:00Z',
    status: 'requested',
    ...overrides,
  }
}

describe('Loans operations', () => {
  afterEach(cleanup)

  beforeEach(() => {
    vi.clearAllMocks()
    loansApi.fetchDisbursementStatus.mockResolvedValue({
      loan_id: 12,
      loan_status: 'requested',
      payout_status: 'none',
      transfer_reference: null,
      can_cancel: true,
      can_retry: false,
    })
  })

  it('requires confirmation before approving a requested loan', async () => {
    loansApi.approveLoan.mockResolvedValue({})
    render(<Loans farmers={farmers} loans={[loan()]} loading={false} />)

    fireEvent.click(screen.getByRole('button', { name: 'Approve' }))
    expect(loansApi.approveLoan).not.toHaveBeenCalled()

    const dialog = screen.getByRole('dialog', { name: 'Approve loan?' })
    expect(dialog.getAttribute('aria-modal')).toBe('true')
    fireEvent.click(screen.getByRole('button', { name: 'Approve loan' }))

    await waitFor(() => expect(loansApi.approveLoan).toHaveBeenCalledWith(12))
  })

  it('shows explicit failed-payout recovery and eligible cancellation actions', async () => {
    loansApi.fetchDisbursementStatus.mockResolvedValue({
      loan_id: 12,
      loan_status: 'approved',
      payout_status: 'failed',
      transfer_reference: 'TRF-123',
      can_cancel: true,
      can_retry: true,
    })
    render(<Loans farmers={farmers} loans={[loan({ status: 'approved' })]} loading={false} />)

    expect(await screen.findByText('Payout: failed')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Retry payout' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Reconcile payout' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Disburse' })).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.getByRole('dialog', { name: 'Cancel loan?' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel loan' }))
    expect(screen.getByRole('alert').textContent).toContain('Enter a cancellation reason')
    expect(loansApi.cancelLoan).not.toHaveBeenCalled()
  })

  it('fetches payout status once per unknown loan while allowing explicit reconciliation', async () => {
    const approvedLoan = loan({ status: 'approved' })
    const { rerender } = render(<Loans farmers={farmers} loans={[approvedLoan]} loading={false} />)

    await waitFor(() => expect(loansApi.fetchDisbursementStatus).toHaveBeenCalledTimes(1))
    rerender(<Loans farmers={farmers} loans={[approvedLoan]} loading={false} dataStale />)
    expect(loansApi.fetchDisbursementStatus).toHaveBeenCalledTimes(1)

    fireEvent.click(await screen.findByRole('button', { name: 'Reconcile payout' }))

    await waitFor(() => expect(loansApi.fetchDisbursementStatus).toHaveBeenCalledTimes(2))
  })
})
