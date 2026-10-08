import type { Me } from '../types.ts'

export function PlayerHeader({ me }: { me: Me }) {
  return (
    <header className="player-header">
      <strong>{me.name}</strong>
      <span>
        {me.total.toLocaleString()} pts{me.rank ? ` · #${me.rank}` : ''}
      </span>
    </header>
  )
}
