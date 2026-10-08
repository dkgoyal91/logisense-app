import type { CopilotResult } from '../types.ts'

const MAX_COLUMNS = 5

type Props = { result: CopilotResult; prompt: string }

export function CopilotCard({ result, prompt }: Props) {
  return (
    <section className="copilot-card">
      <p className="copilot-prompt">“{prompt}”</p>
      {result.sql ? <pre className="copilot-sql">{result.sql}</pre> : <p className="copilot-refusal">{result.error ?? result.summary}</p>}
      <p className="copilot-meta">
        {result.row_count} row{result.row_count === 1 ? '' : 's'} returned{result.table ? ` from ${result.table}` : ''}
      </p>
      {result.sample_rows.length > 0 && <SampleRows rows={result.sample_rows} />}
    </section>
  )
}

function SampleRows({ rows }: { rows: Record<string, unknown>[] }) {
  const columns = Object.keys(rows[0]).slice(0, MAX_COLUMNS)
  return (
    <table className="copilot-rows">
      <thead>
        <tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr key={index}>{columns.map((column) => <td key={column}>{String(row[column] ?? '')}</td>)}</tr>
        ))}
      </tbody>
    </table>
  )
}
