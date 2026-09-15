export const formatCompact = (value: number): string =>
  new Intl.NumberFormat('en-GB', { notation: 'compact', maximumFractionDigits: 1 }).format(value)

export const formatCellValue = (value: unknown): string => {
  if (value === null || value === undefined || value === '') {
    return '—'
  }

  if (typeof value === 'number') {
    return new Intl.NumberFormat('en-GB').format(value)
  }

  return String(value)
}

export const humanizeColumnName = (column: string): string =>
  column.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
