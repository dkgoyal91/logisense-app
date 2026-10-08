import { useElapsed } from '../hooks/useNow.ts'
import { formatClock } from '../lib/countdown.ts'
import type { RaceView } from '../types.ts'

export function RaceClock({ race, receivedAt }: { race: RaceView; receivedAt: number }) {
  const elapsed = useElapsed(race.elapsed_seconds, receivedAt, race.started)
  return (
    <div className="race-clock">
      🏁 Build race <strong>{formatClock(elapsed)}</strong> · {race.finishers.length} finished
    </div>
  )
}
