import { CopilotCard } from '../shared/CopilotCard.tsx'
import type { BonusView } from '../types.ts'

export function BonusBoard({ bonus }: { bonus: BonusView }) {
  return (
    <div className="bonus-board">
      <h2 className="stage-question">Ask Anything: vote on your phone</h2>
      <ol className="bonus-list">
        {bonus.questions.map((question) => (
          <li key={question.id}>
            <span>{question.text}</span>
            <strong>▲ {question.votes}</strong>
          </li>
        ))}
      </ol>
      {bonus.answer && <CopilotCard result={bonus.answer} prompt={bonus.answer.text} />}
    </div>
  )
}
