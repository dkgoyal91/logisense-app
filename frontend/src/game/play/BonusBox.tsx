import { useState, type FormEvent } from 'react'
import type { BonusView } from '../types.ts'

const MAX_BONUS_LENGTH = 120

type Props = { bonus: BonusView; onAsk: (text: string) => void; onVote: (questionId: string) => void }

export function BonusBox({ bonus, onAsk, onVote }: Props) {
  const [text, setText] = useState('')

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (!text.trim()) return
    onAsk(text)
    setText('')
  }

  return (
    <div className="bonus-box">
      <h2>Ask the copilot anything</h2>
      <form onSubmit={submit}>
        <input
          aria-label="Your question"
          maxLength={MAX_BONUS_LENGTH}
          placeholder="e.g. Which vehicles are in maintenance?"
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
        <button type="submit" className="primary">Submit question</button>
      </form>
      <ul className="bonus-list">
        {bonus.questions.map((question) => (
          <li key={question.id}>
            <span>{question.text}</span>
            <button type="button" disabled={question.voted} onClick={() => onVote(question.id)}>
              ▲ {question.votes}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
