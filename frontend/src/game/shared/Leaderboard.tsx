import type { BoardEntry } from '../types.ts'

type Props = { title: string; entries: BoardEntry[]; revealFromBottom?: boolean }

const REVEAL_STEP_SECONDS = 0.6

export function Leaderboard({ title, entries, revealFromBottom = false }: Props) {
  return (
    <section className="board">
      <h3>{title}</h3>
      {entries.length === 0 ? (
        <p className="muted">No points yet</p>
      ) : (
        <ol>
          {entries.map((entry, index) => (
            <li
              key={entry.name}
              className={revealFromBottom ? 'board-row board-row--rise' : 'board-row'}
              style={revealFromBottom ? { animationDelay: `${(entries.length - index) * REVEAL_STEP_SECONDS}s` } : undefined}
            >
              <span className="board-rank">{index + 1}</span>
              <span className="board-name">{entry.name}</span>
              <span className="board-points">{entry.points.toLocaleString()}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
