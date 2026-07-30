import { ChevronLeft, ChevronRight } from 'lucide-react'

export default function DashboardPagination({ page, pageCount, onPage, total, rangeStart, rangeEnd }) {
  if (total === 0) return null
  return (
    <nav className="dashboard-pagination">
      <span>Showing {rangeStart}–{rangeEnd} of {total}</span>
      <div>
        <button onClick={() => onPage(page - 1)} disabled={page === 0}>
          <ChevronLeft size={15} />
        </button>
        <span>Page {page + 1} of {pageCount}</span>
        <button onClick={() => onPage(page + 1)} disabled={page >= pageCount - 1}>
          <ChevronRight size={15} />
        </button>
      </div>
    </nav>
  )
}
