import { useEffect, useMemo, useRef, useState } from 'react'
import './Dashboard.css'
import { formatCellValue, formatCompact, humanizeColumnName } from '../utils/format'

type DashboardTableId = 'opportunities' | 'jobs' | 'shipments' | 'vehicles'

type DashboardTableMeta = {
  id: DashboardTableId
  label: string
}

type DashboardKpis = {
  active_shipments: number
  delayed_shipments: number
  fleet_utilization_avg: number
  open_jobs: number
  active_opportunities: number
}

type DashboardSnapshot = {
  kpis: DashboardKpis
}

type LiveTableResponse = {
  table: string
  rows: Record<string, unknown>[]
  summary: string
  page: number
  page_size: number
  total: number
  total_pages: number
}

type FilterOptionsResponse = {
  table: string
  columns: Record<string, (string | number)[]>
}

const DASHBOARD_TABLES: DashboardTableMeta[] = [
  { id: 'opportunities', label: 'Logistics Portfolio' },
  { id: 'jobs', label: 'Work Orders' },
  { id: 'shipments', label: 'Shipments' },
  { id: 'vehicles', label: 'Fleet' },
]

const PAGE_SIZE_OPTIONS = [25, 50, 100]
const SEARCH_DEBOUNCE_MS = 350

export function Dashboard({ apiBaseUrl }: { apiBaseUrl: string }) {
  const [selectedTable, setSelectedTable] = useState<DashboardTableId>('opportunities')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)
  const [searchInput, setSearchInput] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [filters, setFilters] = useState<Record<string, string>>({})
  const [isFilterPanelOpen, setIsFilterPanelOpen] = useState(false)
  const [filterOptions, setFilterOptions] = useState<FilterOptionsResponse | null>(null)
  const [tableData, setTableData] = useState<LiveTableResponse | null>(null)
  const [kpis, setKpis] = useState<DashboardKpis | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const activeFilterCount = Object.values(filters).filter((value) => value !== '').length

  // Debounce the free-text search box so we don't fire a request on every keystroke.
  useEffect(() => {
    const timer = window.setTimeout(() => setSearchTerm(searchInput.trim()), SEARCH_DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [searchInput])

  useEffect(() => {
    let cancelled = false

    const fetchKpis = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/api/dashboard`)
        if (!response.ok) {
          throw new Error('Dashboard snapshot fetch failed')
        }
        const data = (await response.json()) as DashboardSnapshot
        if (!cancelled) {
          setKpis(data.kpis)
        }
      } catch (error) {
        console.error('Unable to load dashboard KPIs', error)
      }
    }

    void fetchKpis()
    return () => {
      cancelled = true
    }
  }, [apiBaseUrl])

  useEffect(() => {
    let cancelled = false

    const fetchFilterOptions = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/api/live/${selectedTable}/filters`)
        if (!response.ok) {
          throw new Error('Filter options fetch failed')
        }
        const data = (await response.json()) as FilterOptionsResponse
        if (!cancelled) {
          setFilterOptions(data)
        }
      } catch (error) {
        console.error('Unable to load filter options', error)
      }
    }

    setFilters({})
    setIsFilterPanelOpen(false)
    void fetchFilterOptions()
    return () => {
      cancelled = true
    }
  }, [apiBaseUrl, selectedTable])

  // Reset back to page 1 whenever the dataset, search term, page size, or filters change.
  useEffect(() => {
    setPage(1)
  }, [selectedTable, searchTerm, pageSize, filters])

  useEffect(() => {
    let cancelled = false

    const fetchRows = async () => {
      setIsLoading(true)
      setErrorMessage(null)
      try {
        const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
        if (searchTerm) {
          params.set('q', searchTerm)
        }
        const activeFilters = Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== ''))
        if (Object.keys(activeFilters).length > 0) {
          params.set('filters', JSON.stringify(activeFilters))
        }

        const response = await fetch(`${apiBaseUrl}/api/live/${selectedTable}?${params.toString()}`)
        if (!response.ok) {
          throw new Error('Dashboard table fetch failed')
        }
        const data = (await response.json()) as LiveTableResponse
        if (!cancelled) {
          setTableData(data)
        }
      } catch (error) {
        console.error('Unable to load dashboard table rows', error)
        if (!cancelled) {
          setErrorMessage('Unable to load records. Check backend connectivity and try again.')
          setTableData(null)
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    void fetchRows()
    return () => {
      cancelled = true
    }
  }, [apiBaseUrl, selectedTable, page, pageSize, searchTerm, filters])

  const rows = tableData?.rows ?? []
  const columns = useMemo(() => (rows.length > 0 ? Object.keys(rows[0]) : []), [rows])
  const total = tableData?.total ?? 0
  const totalPages = tableData?.total_pages ?? 1
  const rangeStart = total === 0 ? 0 : (page - 1) * pageSize + 1
  const rangeEnd = total === 0 ? 0 : Math.min(page * pageSize, total)

  const filterPanelRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!isFilterPanelOpen) {
      return
    }
    const handleClickOutside = (event: MouseEvent) => {
      if (filterPanelRef.current && !filterPanelRef.current.contains(event.target as Node)) {
        setIsFilterPanelOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isFilterPanelOpen])

  const kpiCards = kpis
    ? [
        { label: 'Active Logistics Portfolio', value: formatCompact(kpis.active_opportunities) },
        { label: 'Open Work Orders', value: formatCompact(kpis.open_jobs) },
        { label: 'Active Shipments', value: formatCompact(kpis.active_shipments) },
        { label: 'Delayed Shipments', value: formatCompact(kpis.delayed_shipments) },
        { label: 'Fleet Utilization', value: `${kpis.fleet_utilization_avg}%` },
      ]
    : []

  return (
    <div className="dashboard-view">
      <div className="dashboard-kpi-row">
        {kpiCards.length > 0
          ? kpiCards.map((card) => (
              <div key={card.label} className="dashboard-kpi-card">
                <span className="dashboard-kpi-value">{card.value}</span>
                <span className="dashboard-kpi-label">{card.label}</span>
              </div>
            ))
          : Array.from({ length: 5 }).map((_, index) => (
              <div key={index} className="dashboard-kpi-card dashboard-kpi-card-loading" />
            ))}
      </div>

      <div className="dashboard-table-tabs" role="tablist" aria-label="Dashboard datasets">
        {DASHBOARD_TABLES.map((table) => (
          <button
            key={table.id}
            type="button"
            role="tab"
            aria-selected={table.id === selectedTable}
            className={`dashboard-table-tab ${table.id === selectedTable ? 'active' : ''}`}
            onClick={() => setSelectedTable(table.id)}
          >
            {table.label}
          </button>
        ))}
      </div>

      <div className="dashboard-toolbar">
        <div className="dashboard-search-wrap">
          <span className="dashboard-search-icon" aria-hidden="true">⌕</span>
          <input
            type="text"
            className="dashboard-search-input"
            placeholder={`Search ${DASHBOARD_TABLES.find((table) => table.id === selectedTable)?.label ?? ''}...`}
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            aria-label="Search dashboard records"
          />
        </div>

        <div className="dashboard-filter-wrap" ref={filterPanelRef}>
          <button
            type="button"
            className={`dashboard-filter-button ${activeFilterCount > 0 ? 'active' : ''}`}
            onClick={() => setIsFilterPanelOpen((value) => !value)}
            aria-expanded={isFilterPanelOpen}
          >
            Filter{activeFilterCount > 0 ? ` (${activeFilterCount})` : ''}
          </button>

          {isFilterPanelOpen ? (
            <div className="dashboard-filter-panel">
              {filterOptions && Object.keys(filterOptions.columns).length > 0 ? (
                Object.entries(filterOptions.columns).map(([column, values]) => (
                  <label key={column} className="dashboard-filter-field">
                    <span>{humanizeColumnName(column)}</span>
                    <select
                      value={filters[column] ?? ''}
                      onChange={(event) =>
                        setFilters((current) => ({ ...current, [column]: event.target.value }))
                      }
                    >
                      <option value="">All</option>
                      {values.map((value) => (
                        <option key={String(value)} value={String(value)}>
                          {String(value)}
                        </option>
                      ))}
                    </select>
                  </label>
                ))
              ) : (
                <p className="dashboard-filter-empty">No filterable columns for this dataset.</p>
              )}
              <button
                type="button"
                className="dashboard-filter-clear"
                onClick={() => setFilters({})}
                disabled={activeFilterCount === 0}
              >
                Clear filters
              </button>
            </div>
          ) : null}
        </div>
      </div>

      <div className="dashboard-table-wrap">
        {errorMessage ? (
          <div className="dashboard-table-empty">{errorMessage}</div>
        ) : isLoading && rows.length === 0 ? (
          <div className="dashboard-table-empty">Loading records…</div>
        ) : rows.length === 0 ? (
          <div className="dashboard-table-empty">No records match your search or filters.</div>
        ) : (
          <table className="dashboard-table">
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column}>{humanizeColumnName(column)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rowIndex) => (
                <tr key={rowIndex} className={isLoading ? 'dashboard-row-refreshing' : ''}>
                  {columns.map((column) => (
                    <td key={column}>{formatCellValue(row[column])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="dashboard-pagination-bar">
        <label className="dashboard-page-size">
          Rows per page
          <select value={pageSize} onChange={(event) => setPageSize(Number(event.target.value))}>
            {PAGE_SIZE_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>

        <span className="dashboard-page-range">
          {total === 0 ? '0 of 0' : `${rangeStart}-${rangeEnd} of ${formatCompact(total)}`}
        </span>

        <div className="dashboard-page-controls">
          <button type="button" onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={page <= 1}>
            ‹
          </button>
          <button
            type="button"
            onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
            disabled={page >= totalPages}
          >
            ›
          </button>
        </div>
      </div>
    </div>
  )
}
