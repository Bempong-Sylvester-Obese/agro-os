import React from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Payments from './Payments'
import Production from './Production'
import Scores from './Scores'
import { exportDashboardReport } from '../../api/reports'

vi.mock('../../api/reports', () => ({ exportDashboardReport: vi.fn() }))
vi.mock('../../api/farmers', () => ({
  fetchFarmerTrustScore: vi.fn().mockRejectedValue(new Error('Unavailable')),
  recalculateTrustScore: vi.fn(),
}))
vi.mock('../Motion', () => ({
  ModalPresence: ({ show, children }) => show ? children : null,
}))

describe('dashboard report export errors', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    exportDashboardReport.mockRejectedValue(new Error('Report service unavailable'))
  })
  afterEach(cleanup)

  it.each([
    ['Payments', <Payments cooperativeId={2} loading={false} />],
    ['Production', <Production cooperativeId={2} loading={false} />],
    [
      'Scores',
      <Scores
        cooperativeId={2}
        loading={false}
        farmers={[{ id: 4, name: 'Ama Mensah', trust_score: 72 }]}
      />,
    ],
  ])('announces %s export failures', async (label, component) => {
    render(component)

    fireEvent.click(
      screen.getByRole('button', { name: `Export filtered ${label} as CSV` }),
    )

    expect((await screen.findByRole('alert')).textContent).toContain(
      'Report service unavailable',
    )
  })
})
