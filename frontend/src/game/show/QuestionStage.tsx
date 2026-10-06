import { useCountdown } from '../hooks/useNow.ts'
import { OptionGrid } from '../shared/OptionGrid.tsx'
import type { QuestionView } from '../types.ts'

type Props = { question: QuestionView; handsMode: boolean; receivedAt: number }

export function QuestionStage({ question, handsMode, receivedAt }: Props) {
  const seconds = useCountdown(question.seconds_left, receivedAt)
  return (
    <div className="stage">
      <header className="stage-head">
        <span>Question {question.index + 1} / {question.total}</span>
        <span className="concept">{question.concept}</span>
        <span className="timer">{seconds}</span>
      </header>
      <p className="chat-bubble">“{question.copilot_prompt}”</p>
      <h2 className="stage-question">{question.text}</h2>
      {question.hint && <p className="stage-hint">{question.hint}</p>}
      <OptionGrid options={question.options} />
      <p className="stage-foot">{handsMode ? '✋ Show of hands!' : `${question.answered_count} answered`}</p>
    </div>
  )
}
