import type { MyResult } from '../types.ts'

const resultIcon = (result: MyResult): string => {
  if (result.correct) return '✅'
  return result.answered ? '❌' : '⏱️'
}

const resultTitle = (result: MyResult): string => {
  if (result.correct) return `+${result.points} points`
  return result.answered ? 'Not this time' : 'No answer'
}

export function ResultCard({ result, rank }: { result: MyResult; rank: number | null }) {
  return (
    <div className={`result ${result.correct ? 'good' : 'bad'}`}>
      <p className="result-icon">{resultIcon(result)}</p>
      <p className="result-title">{resultTitle(result)}</p>
      {!result.correct && <p>Answer: {result.correct_option}</p>}
      {rank !== null && <p className="muted">You're #{rank}</p>}
    </div>
  )
}
