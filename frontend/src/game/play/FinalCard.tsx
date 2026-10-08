import { useEffect } from 'react'
import { fireConfetti } from '../lib/confetti.ts'
import { AWARD_LABELS } from '../shared/labels.ts'
import type { Award, Me } from '../types.ts'

export function FinalCard({ me, awards }: { me: Me; awards: Award[] }) {
  const hasAward = awards.length > 0
  useEffect(() => {
    if (hasAward) fireConfetti()
  }, [hasAward])

  return (
    <div className="final">
      <p className="final-rank">{me.rank ? `#${me.rank}` : '-'}</p>
      <p>{me.total.toLocaleString()} points</p>
      {awards.map((award) => (
        <p key={award.category} className="award">
          🏆 {AWARD_LABELS[award.category]}: #{award.place}
        </p>
      ))}
    </div>
  )
}
