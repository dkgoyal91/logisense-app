import { useState, type FormEvent } from 'react'
import { canSendTakeaway, takeawayStatusText } from '../lib/takeaway.ts'
import type { Takeaway } from '../types.ts'

type Props = { takeaway: Takeaway | null; onSend: (email: string) => void }

export function TakeawayCard({ takeaway, onSend }: Props) {
  if (takeaway && takeaway.status !== 'failed') {
    return <p className="takeaway takeaway--done">{takeawayStatusText(takeaway)}</p>
  }
  return <TakeawayForm failed={takeaway} onSend={onSend} />
}

function TakeawayForm({ failed, onSend }: { failed: Takeaway | null; onSend: (email: string) => void }) {
  const [email, setEmail] = useState('')
  const [consent, setConsent] = useState(false)
  const ready = canSendTakeaway(email, consent)

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (ready) onSend(email.trim())
  }

  return (
    <form className="takeaway" onSubmit={submit}>
      <h3>📩 Email me the repo + build prompt</h3>
      {failed && <p className="takeaway-error">{takeawayStatusText(failed)}</p>}
      <input
        type="email"
        inputMode="email"
        autoComplete="email"
        aria-label="Your email"
        placeholder="you@company.com"
        maxLength={254}
        value={email}
        onChange={(event) => setEmail(event.target.value)}
      />
      <label className="takeaway-consent">
        <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} />
        <span>Use my email only to send this; it's deleted after the event.</span>
      </label>
      <button type="submit" className="primary" disabled={!ready}>Send it to me</button>
    </form>
  )
}
