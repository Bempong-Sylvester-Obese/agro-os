import React from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { DashboardPagination, DashboardTableToolbar, useDashboardTable } from './DashboardTableTools'

const rows = Array.from({ length: 12 }, (_, index) => ({
  id: index + 1,
  name: index === 11 ? 'Special Farmer' : `Farmer ${index + 1}`,
  status: index % 2 ? 'inactive' : 'active',
  created_at: `2026-07-${String(index + 1).padStart(2, '0')}T10:00:00Z`,
}))

function Harness({ onExport = () => {} }) {
  const table = useDashboardTable({
    rows,
    searchableText: row => row.name,
    statusValue: row => row.status,
    dateValue: row => row.created_at,
  })
  return (
    <>
      <DashboardTableToolbar
        label="Members"
        table={table}
        statuses={[
          { value: 'active', label: 'Active' },
          { value: 'inactive', label: 'Inactive' },
        ]}
        onExport={() => onExport(table.exportFilters)}
      />
      <div data-testid="rows">{table.pageRows.map(row => row.name).join(',')}</div>
      <DashboardPagination label="Members" table={table} />
    </>
  )
}

describe('DashboardTableTools', () => {
  beforeEach(() => window.history.replaceState(null, '', '/dashboard/members'))
  afterEach(cleanup)

  it('filters by search, status, and inclusive dates', () => {
    render(<Harness />)

    fireEvent.change(screen.getByRole('searchbox', { name: 'Search Members' }), { target: { value: 'Farmer' } })
    fireEvent.change(screen.getByRole('combobox', { name: 'Filter Members by status' }), { target: { value: 'inactive' } })
    const startDate = screen.getByText('From').closest('label').querySelector('input')
    fireEvent.change(startDate, { target: { value: '2026-07-12' } })

    expect(screen.getByTestId('rows').textContent).toBe('Special Farmer')
  })

  it('paginates and passes active filters to export', () => {
    const onExport = vi.fn()
    render(<Harness onExport={onExport} />)

    expect(screen.getByText('Showing 1–10 of 12')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Next Members page' }))
    expect(screen.getByText('Showing 11–12 of 12')).toBeTruthy()
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search Members' }), { target: { value: 'Special' } })
    fireEvent.click(screen.getByRole('button', { name: 'Export filtered Members as CSV' }))

    expect(onExport).toHaveBeenCalledWith(expect.objectContaining({ q: 'Special' }))
  })

  it('restores filters from the dashboard URL', () => {
    window.history.replaceState(null, '', '/dashboard/members?q=Special&status=inactive')
    render(<Harness />)

    expect(screen.getByRole('searchbox', { name: 'Search Members' }).value).toBe('Special')
    expect(screen.getByRole('combobox', { name: 'Filter Members by status' }).value).toBe('inactive')
    expect(screen.getByTestId('rows').textContent).toBe('Special Farmer')
  })
})
