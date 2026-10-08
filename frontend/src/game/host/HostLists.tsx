import { useState } from 'react'
import { ConfirmButton } from '../shared/ConfirmButton.tsx'
import { LAYER_LABELS } from '../shared/labels.ts'
import type { HostView } from '../types.ts'
import type { Act } from './HostControls.tsx'

type Props = { view: HostView; act: Act }

export function HostAttacks({ view, act }: Props) {
  if (view.attacks.length === 0) return null
  return (
    <section className="host-section">
      <h3>Attacks</h3>
      <ul className="host-list">
        {view.attacks.map((attack) => (
          <li key={attack.id}>
            <span>
              <strong>{LAYER_LABELS[attack.layer]}</strong> · {attack.name}: {attack.text}
            </span>
            <button type="button" disabled={attack.starred} onClick={() => act('star_attack', { attack_id: attack.id })}>
              {attack.starred ? '⭐' : '☆ Star'}
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}

export function HostBonus({ view, act }: Props) {
  if (!view.bonus) return null
  return (
    <section className="host-section">
      <h3>Bonus questions</h3>
      <ul className="host-list">
        {view.bonus.questions.map((question) => (
          <li key={question.id}>
            <span>▲ {question.votes} · {question.text}</span>
            <button type="button" onClick={() => act('ask_bonus', { question_id: question.id })}>Ask on screen</button>
          </li>
        ))}
      </ul>
    </section>
  )
}

export function HostPlayers({ view, act }: Props) {
  const [filter, setFilter] = useState('')
  const needle = filter.trim().toLowerCase()
  const players = view.players.filter((player) => !player.kicked && player.name.toLowerCase().includes(needle))
  return (
    <section className="host-section">
      <h3>Players ({players.length})</h3>
      <input aria-label="Find player" placeholder="Find player" value={filter} onChange={(event) => setFilter(event.target.value)} />
      <ul className="host-list">
        {players.map((player) => (
          <li key={player.id}>
            <span>
              {player.name} · {player.total.toLocaleString()}
              {player.race_done && ' 🏁'}
            </span>
            {player.race_done && !player.demo_awarded && (
              <button type="button" onClick={() => act('award_demo', { player_id: player.id })}>+500 demo</button>
            )}
            <ConfirmButton onConfirm={() => act('kick', { player_id: player.id })}>Kick</ConfirmButton>
          </li>
        ))}
      </ul>
    </section>
  )
}
