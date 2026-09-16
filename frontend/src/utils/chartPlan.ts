import { formatColumnLabel } from './format'

const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}/
const EXCLUDED_DIMENSIONS = ['latitude', 'longitude']
const MAX_BAR_CATEGORIES = 12
const MAX_DONUT_CATEGORIES = 6

export type ResultRow = Record<string, unknown>

export type ChartPlan = {
  kind: 'line' | 'bar' | 'donut'
  dimension: string
  measure: string | null
  points: { name: string; value: number }[]
}

const distinctCount = (rows: ResultRow[], column: string): number =>
  new Set(rows.map((row) => String(row[column] ?? ''))).size

const isDateColumn = (rows: ResultRow[], column: string): boolean =>
  rows.every((row) => typeof row[column] === 'string' && DATE_PATTERN.test(row[column] as string))

const isUsableDimension = (rows: ResultRow[], column: string): boolean => {
  if (EXCLUDED_DIMENSIONS.includes(column.toLowerCase())) {
    return false
  }
  if (typeof rows[0][column] !== 'string') {
    return false
  }

  const distinct = distinctCount(rows, column)
  // A column that is constant tells us nothing, and one unique per row is an identifier.
  return distinct > 1 && !(distinct === rows.length && rows.length > MAX_DONUT_CATEGORIES)
}

// Prefer a dimension that splits the rows into a readable number of groups.
const scoreDimension = (rows: ResultRow[], column: string): number => {
  const distinct = distinctCount(rows, column)
  if (distinct <= MAX_BAR_CATEGORIES) {
    return 100 - Math.abs(distinct - 5)
  }
  return 50 - distinct
}

const bestScoring = (rows: ResultRow[], columns: string[]): string =>
  columns.reduce((best, column) => (scoreDimension(rows, column) > scoreDimension(rows, best) ? column : best))

const selectDimension = (rows: ResultRow[]): string | null => {
  const candidates = Object.keys(rows[0]).filter((column) => isUsableDimension(rows, column))
  if (candidates.length === 0) {
    return null
  }

  // Prefer a categorical dimension; a date column is only a useful axis when the rows
  // have nothing else to group by, otherwise attributes like `last_service_date` win
  // over genuinely descriptive dimensions like `depot`.
  const categorical = candidates.filter((column) => !isDateColumn(rows, column))
  if (categorical.length > 0) {
    return bestScoring(rows, categorical)
  }

  return bestScoring(rows, candidates)
}

const selectMeasure = (rows: ResultRow[], dimension: string): string | null =>
  Object.keys(rows[0]).find(
    (column) =>
      column !== dimension &&
      !EXCLUDED_DIMENSIONS.includes(column.toLowerCase()) &&
      typeof rows[0][column] === 'number',
  ) ?? null

const RATIO_MEASURE_PATTERN = /pct|percent|rate|ratio|utilization|average|avg|score/i

export const aggregationFor = (measure: string | null): 'sum' | 'average' =>
  measure && RATIO_MEASURE_PATTERN.test(measure) ? 'average' : 'sum'

// Roll the raw rows up by the chosen dimension so each category appears exactly once.
const aggregate = (rows: ResultRow[], dimension: string, measure: string | null) => {
  const totals = new Map<string, { total: number; count: number }>()

  rows.forEach((row) => {
    const key = String(row[dimension] ?? '—')
    const amount = measure ? Number(row[measure]) || 0 : 1
    const bucket = totals.get(key) ?? { total: 0, count: 0 }
    totals.set(key, { total: bucket.total + amount, count: bucket.count + 1 })
  })

  const useAverage = aggregationFor(measure) === 'average'
  return Array.from(totals, ([name, bucket]) => ({
    name,
    value: useAverage ? Math.round((bucket.total / bucket.count) * 10) / 10 : bucket.total,
  }))
}

export const buildChartPlan = (rows: ResultRow[]): ChartPlan | null => {
  if (rows.length === 0) {
    return null
  }

  const dimension = selectDimension(rows)
  if (!dimension) {
    return null
  }

  const measure = selectMeasure(rows, dimension)
  const points = aggregate(rows, dimension, measure)

  if (isDateColumn(rows, dimension)) {
    return { kind: 'line', dimension, measure, points: points.sort((a, b) => a.name.localeCompare(b.name)) }
  }

  const ranked = points.sort((a, b) => b.value - a.value)
  if (ranked.length <= MAX_DONUT_CATEGORIES) {
    return { kind: 'donut', dimension, measure, points: ranked }
  }

  return { kind: 'bar', dimension, measure, points: ranked.slice(0, MAX_BAR_CATEGORIES) }
}

export const describeChart = (rows: ResultRow[]): string => {
  const plan = buildChartPlan(rows)
  if (!plan) {
    return 'Not enough variation in this result set to chart.'
  }

  const measureLabel = plan.measure
    ? `${aggregationFor(plan.measure) === 'average' ? 'Average' : 'Total'} ${formatColumnLabel(plan.measure)}`
    : 'Record count'
  return `${measureLabel} by ${formatColumnLabel(plan.dimension)}`
}
