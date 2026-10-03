import type { HostAction, HostView, Phase } from '../types.ts'

export type Act = (action: HostAction, extra?: { player_id?: string; attack_id?: string; question_id?: string; confirm?: string }) => void

const NEXT_LABELS: Record<Phase, string> = {
  lobby: 'Start Round 1',
  question_open: 'Reveal',
  question_revealed: 'Next',
  break_it_open: 'Close attacks',
  break_it_closed: 'Show race podium',
  race_podium: 'Bonus round',
  bonus: 'Finale',
  finale: 'Show is over',
}

const skipLabel = (phase: Phase): string => {
  if (phase === 'question_open') return 'Skip question (no points)'
  if (phase === 'race_podium') return 'Skip bonus → finale'
  return 'Skip'
}

export function HostControls({ view, act }: { view: HostView; act: Act }) {
  const isOpen = view.phase === 'question_open'
  return (
    <div className="host-controls">
      <button
        type="button"
        className="primary big"
        disabled={view.phase === 'finale'}
        onClick={() => act(isOpen ? 'reveal' : 'next')}
      >
        {NEXT_LABELS[view.phase]}
      </button>
      {!view.race.started && (
        <button type="button" onClick={() => act('start_race')}>🏁 Start build race</button>
      )}
      <button type="button" disabled={view.phase === 'finale'} onClick={() => act('skip')}>
        {skipLabel(view.phase)}
      </button>
      <button type="button" onClick={() => act('hands_mode')}>
        ✋ Hands mode {view.hands_mode ? 'ON' : 'off'}
      </button>
    </div>
  )
}
