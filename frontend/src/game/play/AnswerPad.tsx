import { useCountdown } from '../hooks/useNow.ts'
import { OPTION_MARKS, optionClass } from '../lib/options.ts'
import type { QuestionView } from '../types.ts'

type Props = { question: QuestionView; myAnswer: number | null; receivedAt: number; onAnswer: (option: number) => void }

const statusText = (myAnswer: number | null, seconds: number): string => {
  if (myAnswer !== null) return 'Locked in! Watch the big screen.'
  return seconds > 0 ? `${seconds}s left: pick one!` : "Time's up!"
}

export function AnswerPad({ question, myAnswer, receivedAt, onAnswer }: Props) {
  const seconds = useCountdown(question.seconds_left, receivedAt)
  const locked = myAnswer !== null || seconds <= 0
  return (
    <div className="answer-pad">
      <p className="muted">{question.text}</p>
      <p className="pad-status">{statusText(myAnswer, seconds)}</p>
      <div className="pad-grid">
        {question.options.map((option, index) => (
          <button
            key={option}
            type="button"
            className={`${optionClass(index)}${myAnswer === index ? ' chosen' : ''}`}
            disabled={locked}
            onClick={() => onAnswer(index)}
          >
            <span className="opt-mark">{OPTION_MARKS[index]}</span>
            <span className="opt-label">{option}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
