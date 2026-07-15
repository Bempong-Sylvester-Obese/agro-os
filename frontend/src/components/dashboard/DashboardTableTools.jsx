import React, { useEffect, useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight, Download, Search } from 'lucide-react'

const DEFAULT_PAGE_SIZE = 10

function dateKey(value) {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : date.toISOString().slice(0, 10)
}

export function useDashboardTable({
  rows,
  searchableText,
  statusValue,
  dateValue,
  pageSize = DEFAULT_PAGE_SIZE,
}) {
  const initialParams = useMemo(() => new URLSearchParams(window.location.search), [])
  const [search, setSearch] = useState(() => initialParams.get('q') || '')
  const [status, setStatus] = useState(() => initialParams.get('status') || 'all')
  const [startDate, setStartDate] = useState(() => initialParams.get('from') || '')
  const [endDate, setEndDate] = useState(() => initialParams.get('to') || '')
  const [page, setPage] = useState(() => Math.max(1, Number(initialParams.get('page')) || 1))

  const filteredRows = useMemo(() => {
    const query = search.trim().toLowerCase()
    return rows.filter(row => {
      const matchesSearch = !query || searchableText(row).toLowerCase().includes(query)
      const matchesStatus = status === 'all' || !statusValue || statusValue(row) === status
      const rowDate = dateValue ? dateKey(dateValue(row)) : ''
      const matchesStart = !startDate || (rowDate && rowDate >= startDate)
      const matchesEnd = !endDate || (rowDate && rowDate <= endDate)
      return matchesSearch && matchesStatus && matchesStart && matchesEnd
    })
  }, [dateValue, endDate, rows, search, searchableText, startDate, status, statusValue])

  const pageCount = Math.max(1, Math.ceil(filteredRows.length / pageSize))
  useEffect(() => setPage(1), [search, status, startDate, endDate])
  useEffect(() => setPage(current => Math.min(current, pageCount)), [pageCount])
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const values = { q: search, status: status === 'all' ? '' : status, from: startDate, to: endDate }
    Object.entries(values).forEach(([key, value]) => {
      if (value) params.set(key, value)
      else params.delete(key)
    })
    if (page > 1) params.set('page', String(page))
    else params.delete('page')
    const query = params.toString()
    window.history.replaceState(null, '', `${window.location.pathname}${query ? `?${query}` : ''}`)
  }, [endDate, page, search, startDate, status])

  return {
    search,
    setSearch,
    status,
    setStatus,
    startDate,
    setStartDate,
    endDate,
    setEndDate,
    page,
    setPage,
    pageSize,
    pageCount,
    filteredRows,
    pageRows: filteredRows.slice((page - 1) * pageSize, page * pageSize),
    exportFilters: {
      q: search.trim() || undefined,
      status: status === 'all' ? undefined : status,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    },
  }
}

export function DashboardTableToolbar({
  label,
  table,
  statuses = [],
  onExport,
  exporting = false,
  exportError = '',
  children,
}) {
  return (
    <>
      <div className="dashboard-table-toolbar" aria-label={`${label} table controls`}>
        <div className="dashboard-table-filters">
        <label className="dashboard-table-search">
          <span className="sr-only">Search {label}</span>
          <Search size={16} aria-hidden="true" />
          <input
            type="search"
            placeholder={`Search ${label.toLowerCase()}…`}
            value={table.search}
            onChange={event => table.setSearch(event.target.value)}
          />
        </label>
        {statuses.length > 0 && (
          <label>
            <span className="sr-only">Filter {label} by status</span>
            <select value={table.status} onChange={event => table.setStatus(event.target.value)}>
              <option value="all">All statuses</option>
              {statuses.map(option => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
        )}
        <label className="dashboard-table-date">
          <span>From</span>
          <input type="date" value={table.startDate} onChange={event => table.setStartDate(event.target.value)} />
        </label>
        <label className="dashboard-table-date">
          <span>To</span>
          <input type="date" value={table.endDate} onChange={event => table.setEndDate(event.target.value)} />
        </label>
        </div>
        <div className="dashboard-table-actions">
          <button
            type="button"
            className="dashboard-export-btn"
            onClick={onExport}
            disabled={exporting}
            aria-label={`Export filtered ${label} as CSV`}
          >
            <Download size={15} aria-hidden="true" />
            {exporting ? 'Exporting…' : 'Export CSV'}
          </button>
          {children}
        </div>
      </div>
      {exportError && <div className="dashboard-inline-error" role="alert">{exportError}</div>}
    </>
  )
}

export function DashboardPagination({ label, table }) {
  if (table.filteredRows.length === 0) return null
  const first = (table.page - 1) * table.pageSize + 1
  const last = Math.min(table.page * table.pageSize, table.filteredRows.length)
  return (
    <nav className="dashboard-pagination" aria-label={`${label} pagination`}>
      <span>Showing {first}–{last} of {table.filteredRows.length}</span>
      <div>
        <button
          type="button"
          onClick={() => table.setPage(table.page - 1)}
          disabled={table.page === 1}
          aria-label={`Previous ${label} page`}
        >
          <ChevronLeft size={15} aria-hidden="true" />
        </button>
        <span>Page {table.page} of {table.pageCount}</span>
        <button
          type="button"
          onClick={() => table.setPage(table.page + 1)}
          disabled={table.page === table.pageCount}
          aria-label={`Next ${label} page`}
        >
          <ChevronRight size={15} aria-hidden="true" />
        </button>
      </div>
    </nav>
  )
}
