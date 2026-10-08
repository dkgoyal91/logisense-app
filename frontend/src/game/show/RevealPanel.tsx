import { CopilotCard } from '../shared/CopilotCard.tsx'
import { Leaderboard } from '../shared/Leaderboard.tsx'
import { OptionGrid } from '../shared/OptionGrid.tsx'
import type { Boards, QuestionView, RevealView } from '../types.ts'

const TOP_FIVE = 5

type Props = { question: QuestionView; reveal: RevealView; boards: Boards; handsMode: boolean }

export function RevealPanel({ question, reveal, boards, handsMode }: Props) {
  return (
    <div className="reveal">
      <div className="reveal-main">
        <h2 className="stage-question">{question.text}</h2>
        <OptionGrid
          options={question.options}
          distribution={handsMode ? undefined : reveal.distribution}
          correctIndex={reveal.correct_index}
        />
        {reveal.copilot && <CopilotCard result={reveal.copilot} prompt={question.copilot_prompt} />}
      </div>
      {!handsMode && <Leaderboard title="Leaderboard" entries={boards.overall.slice(0, TOP_FIVE)} />}
    </div>
  )
}
