import { useCallback } from 'react'
import { useGameSocket } from '../hooks/useGameSocket.ts'
import { ConfirmButton } from '../shared/ConfirmButton.tsx'
import { ErrorToast } from '../shared/ErrorToast.tsx'
import { takeawayCountsLabel } from '../lib/takeaway.ts'
import type { HostView } from '../types.ts'
import { HostControls, type Act } from './HostControls.tsx'
import { HostAttacks, HostBonus, HostPlayers } from './HostLists.tsx'

export function HostScreen() {
  const { view, send, error, clearError, connected } = useGameSocket<HostView>('host')
  const act: Act = useCallback((action, extra = {}) => send({ type: 'host', action, ...extra }), [send])

  if (!view) return <p className="centered">{error ?? 'Connecting…'}</p>
  return (
    <div className="host">
      <header className="host-status">
        <strong>{view.phase.replace(/_/g, ' ')}</strong>
        <span>{view.lobby.count} players</span>
        <span>{connected ? '🟢 live' : '🔴 reconnecting'}</span>
        <span>{takeawayCountsLabel(view.takeaway_counts ?? {})}</span>
      </header>
      <ErrorToast message={error} onDismiss={clearError} />
      <HostControls view={view} act={act} />
      {view.answer_key && <p className="answer-key">Answer: <strong>{view.answer_key}</strong></p>}
      <HostAttacks view={view} act={act} />
      <HostBonus view={view} act={act} />
      <HostPlayers view={view} act={act} />
      <ConfirmButton onConfirm={() => act('reset', { confirm: 'RESET' })}>Reset game</ConfirmButton>
    </div>
  )
}
