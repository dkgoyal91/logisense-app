import { useMemo, useState } from 'react'
import { Icon } from './Icon'
import { formatCellValue, formatColumnLabel, isNumericColumn, statusTone } from '../utils/format'

type ResultRow = Record<string, unknown>

type SortState = {
  column: string
  direction: 'asc' | 'desc'
}

const COORDINATE_COLUMNS = ['latitude', 'longitude']
const COLLAPSED_ROW_COUNT = 5

const isCoordinateColumn = (column: string): boolean => COORDINATE_COLUMNS.includes(column.toLowerCase())

const compareValues = (left: unknown, right: unknown): number => {
  if (typeof left === 'number' && typeof right === 'number') {
    return left - right
  }

  return String(left ?? '').localeCompare(String(right ?? ''), 'en-GB', { numeric: true })
}

const sortRows = (rows: ResultRow[], sort: SortState | null): ResultRow[] => {
  if (!sort) {
    return rows
  }

  const direction = sort.direction === 'asc' ? 1 : -1
  return [...rows].sort((a, b) => compareValues(a[sort.column], b[sort.column]) * direction)
}

const nextSortState = (current: SortState | null, column: string): SortState => {
  if (current?.column === column && current.direction === 'asc') {
    return { column, direction: 'desc' }
  }

  return { column, direction: 'asc' }
}

const sortIconName = (sort: SortState | null, column: string) => {
  if (sort?.column !== column) {
    return 'sort' as const
  }

  return sort.direction === 'asc' ? ('sort-asc' as const) : ('sort-desc' as const)
}

function StatusCell({ value }: { value: unknown }) {
  const tone = statusTone(value)

  if (!tone) {
    return <>{formatCellValue(value)}</>
  }

  return <span className={`ls-status-pill ls-status-${tone}`}>{formatCellValue(value)}</span>
}

/**
 * Sortable, expandable result table shared by chat answers. Keeps coordinate columns
 * out of the way by default and never silently truncates the row set.
 */
export function ResultTable({ rows }: { rows: ResultRow[] }) {
  const [sort, setSort] = useState<SortState | null>(null)
  const [isExpanded, setIsExpanded] = useState(false)
  const [showCoordinates, setShowCoordinates] = useState(false)

  const allColumns = useMemo(() => Array.from(new Set(rows.flatMap((row) => Object.keys(row)))), [rows])
  const coordinateColumns = allColumns.filter(isCoordinateColumn)
  const columns = showCoordinates ? allColumns : allColumns.filter((column) => !isCoordinateColumn(column))

  const sortedRows = useMemo(() => sortRows(rows, sort), [rows, sort])
  const visibleRows = isExpanded ? sortedRows : sortedRows.slice(0, COLLAPSED_ROW_COUNT)
  const hasHiddenRows = rows.length > COLLAPSED_ROW_COUNT

  if (rows.length === 0) {
    return null
  }

  return (
    <div className="ls-table-wrap">
      <div className="ls-table-scroll">
        <table className="ls-table">
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column} className={isNumericColumn(rows, column) ? 'numeric' : undefined}>
                  <button
                    type="button"
                    className="ls-table-sort"
                    onClick={() => setSort((current) => nextSortState(current, column))}
                    aria-label={`Sort by ${formatColumnLabel(column)}`}
                  >
                    {formatColumnLabel(column)}
                    <Icon name={sortIconName(sort, column)} size={12} />
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {columns.map((column) => (
                  <td key={column} className={isNumericColumn(rows, column) ? 'numeric' : undefined}>
                    {column.toLowerCase() === 'status' ? (
                      <StatusCell value={row[column]} />
                    ) : (
                      formatCellValue(row[column])
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="ls-table-footer">
        <span className="ls-table-count">
          Showing {visibleRows.length} of {rows.length} row{rows.length === 1 ? '' : 's'}
        </span>

        <div className="ls-table-footer-actions">
          {coordinateColumns.length > 0 ? (
            <button type="button" className="ls-btn ls-btn--ghost ls-btn--sm" onClick={() => setShowCoordinates((value) => !value)}>
              {showCoordinates ? 'Hide coordinates' : 'Show coordinates'}
            </button>
          ) : null}

          {hasHiddenRows ? (
            <button type="button" className="ls-btn ls-btn--ghost ls-btn--sm" onClick={() => setIsExpanded((value) => !value)}>
              {isExpanded ? 'Show less' : `Show all ${rows.length}`}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  )
}
