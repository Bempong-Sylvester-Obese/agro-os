import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import WorkerForm from './WorkerForm'
import { createWorker, updateWorker } from '../../api/workers'

vi.mock('../../api/workers', () => ({
  createWorker: vi.fn(),
  updateWorker: vi.fn(),
}))

describe('WorkerForm', () => {
  afterEach(cleanup)
  beforeEach(() => vi.clearAllMocks())

  it('submits hire date, pay type, and optional user id', async () => {
    createWorker.mockResolvedValue({ id: 11 })
    const onSaved = vi.fn()
    render(<WorkerForm cooperativeId={3} onSaved={onSaved} onCancel={vi.fn()} />)

    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Kojo Boateng' } })
    fireEvent.change(screen.getByLabelText('Phone'), { target: { value: '0241110001' } })
    fireEvent.change(screen.getByLabelText('Pay type'), { target: { value: 'monthly' } })
    fireEvent.change(screen.getByLabelText(/Wage rate/), { target: { value: '800' } })
    fireEvent.change(screen.getByLabelText('Hire date'), { target: { value: '2026-04-01' } })
    fireEvent.change(screen.getByLabelText('Linked user ID (optional)'), { target: { value: '9' } })
    fireEvent.submit(screen.getByRole('button', { name: 'Create' }).closest('form'))

    await waitFor(() => expect(createWorker).toHaveBeenCalledWith(3, {
      name: 'Kojo Boateng',
      phone: '0241110001',
      wage_rate: 800,
      role: 'worker',
      pay_type: 'monthly',
      hire_date: '2026-04-01',
      user_id: 9,
    }))
    expect(onSaved).toHaveBeenCalled()
  })

  it('updates an existing worker including pay type', async () => {
    updateWorker.mockResolvedValue({ id: 4 })
    render(
      <WorkerForm
        cooperativeId={3}
        worker={{
          id: 4,
          name: 'Ama',
          phone: '0241110002',
          wage_rate: 40,
          role: 'supervisor',
          hire_date: '2026-01-01',
          pay_type: 'daily',
          user_id: null,
        }}
        onSaved={vi.fn()}
        onCancel={vi.fn()}
      />,
    )

    fireEvent.change(screen.getByLabelText('Pay type'), { target: { value: 'shift' } })
    fireEvent.submit(screen.getByRole('button', { name: 'Update' }).closest('form'))

    await waitFor(() => expect(updateWorker).toHaveBeenCalledWith(3, 4, expect.objectContaining({
      pay_type: 'shift',
      hire_date: '2026-01-01',
      user_id: null,
    })))
  })
})
