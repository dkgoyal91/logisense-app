import { useState, type FormEvent } from 'react'
import { loadSavedPlayer } from '../lib/storage.ts'

const MIN_NAME_LENGTH = 2
const MAX_NAME_LENGTH = 20

type Props = { onJoin: (name: string) => void; error: string | null }

export function JoinForm({ onJoin, error }: Props) {
  const [name, setName] = useState(() => loadSavedPlayer()?.name ?? '')
  const trimmed = name.trim()

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (trimmed.length >= MIN_NAME_LENGTH) onJoin(trimmed)
  }

  return (
    <form className="join" onSubmit={submit}>
      <h1>Beat the Copilot</h1>
      <p className="muted">Pick a nickname to join the game.</p>
      <input
        aria-label="Nickname"
        autoFocus
        maxLength={MAX_NAME_LENGTH}
        placeholder="Your nickname"
        value={name}
        onChange={(event) => setName(event.target.value)}
      />
      <button type="submit" className="primary" disabled={trimmed.length < MIN_NAME_LENGTH}>
        Join
      </button>
      {error && <p className="muted">{error}</p>}
    </form>
  )
}
