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

// Legacy CRM column names leak through from the seeded dataset; present them in
// logistics language instead.
export const formatColumnLabel = (column: string): string => {
  const normalized = column
    .replace(/opportunity_ref/gi, 'record_ref')
    .replace(/pipeline_ref/gi, 'record_ref')
    .replace(/salesforce_number/gi, 'record_ref')
    .replace(/job_director/gi, 'operations_lead')
    .replace(/opportunity_owner/gi, 'logistics_owner')
    .replace(/valuation_date/gi, 'review_date')
    .replace(/number_of_properties/gi, 'route_count')
    .replace(/portfolio/gi, 'record set')
    .replace(/_+/g, ' ')
    .trim()

  return normalized.replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export const isNumericColumn = (rows: Record<string, unknown>[], column: string): boolean =>
  rows.some((row) => typeof row[column] === 'number')

const STATUS_TONE_PATTERNS: [RegExp, string][] = [
  [/delay|overdue|fail|critical|breach/i, 'danger'],
  [/maintenance|hold|pending|review|awaiting|risk/i, 'warning'],
  [/on time|complete|delivered|active|available|in progress|open/i, 'good'],
]

export const statusTone = (value: unknown): string | null => {
  if (typeof value !== 'string') {
    return null
  }

  const match = STATUS_TONE_PATTERNS.find(([pattern]) => pattern.test(value))
  return match ? match[1] : 'neutral'
}
