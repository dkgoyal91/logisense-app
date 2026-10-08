import { useEffect } from 'react'
import { fireConfetti } from '../lib/confetti.ts'
import { formatClock } from '../lib/countdown.ts'
import { AWARD_LABELS } from '../shared/labels.ts'
import { Leaderboard } from '../shared/Leaderboard.tsx'
import type { Boards } from '../types.ts'

const CONFETTI_DELAY_MS = 6500

export function Finale({ boards }: { boards: Boards }) {
  useEffect(() => {
    const timer = window.setTimeout(fireConfetti, CONFETTI_DELAY_MS)
    return () => window.clearTimeout(timer)
  }, [])

  return (
    <div className="finale">
      <h2 className="stage-question">And the winners are…</h2>
      <div className="finale-grid">
        <Leaderboard title="Overall" entries={boards.overall} revealFromBottom />
        <div className="winners">
          <Winner label={AWARD_LABELS.predictor} name={boards.predictor[0]?.name} />
          <Winner label={AWARD_LABELS.hacker} name={boards.hacker[0]?.name} />
          <Winner
            label={AWARD_LABELS.builder}
            name={boards.builder[0] ? `${boards.builder[0].name} (${formatClock(boards.builder[0].seconds)})` : undefined}
          />
        </div>
      </div>
    </div>
  )
}

function Winner({ label, name }: { label: string; name?: string }) {
  return (
    <div className="winner">
      <span>{label}</span>
      <strong>{name ?? 'No winner'}</strong>
    </div>
  )
}
