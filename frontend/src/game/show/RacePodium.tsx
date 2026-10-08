import { formatClock } from '../lib/countdown.ts'
import type { BuilderEntry } from '../types.ts'

const PODIUM_ORDER = [1, 0, 2]

export function RacePodium({ finishers }: { finishers: BuilderEntry[] }) {
  return (
    <div className="podium-wrap">
      <h2 className="stage-question">Fastest builders</h2>
      {finishers.length === 0 ? (
        <p className="muted">Nobody has finished yet. Keep building!</p>
      ) : (
        <div className="podium">
          {PODIUM_ORDER.filter((index) => finishers[index]).map((index) => (
            <div key={finishers[index].name} className={`podium-step place-${index + 1}`}>
              <span className="podium-name">{finishers[index].name}</span>
              <span>{formatClock(finishers[index].seconds)}</span>
              <strong>#{index + 1}</strong>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
