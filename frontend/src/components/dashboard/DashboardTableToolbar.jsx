import { Search } from 'lucide-react'

export default function DashboardTableToolbar({ search, onSearch, placeholder, children }) {
  return (
    <div className="dashboard-table-toolbar">
      <div className="dashboard-table-filters">
        <label className="dashboard-table-search">
          <Search size={16} />
          <input type="search" placeholder={placeholder || 'Search workers…'} value={search}
            onChange={e => onSearch(e.target.value)} />
        </label>
        {children}
      </div>
    </div>
  )
}
