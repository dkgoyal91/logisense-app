import { useEffect, useState } from 'react'
import { useGameSocket, type GameSocket } from '../hooks/useGameSocket.ts'
import { loadSavedPlayer, savePlayer } from '../lib/storage.ts'
import { ErrorToast } from '../shared/ErrorToast.tsx'
import type { Me, PlayerView, Send } from '../types.ts'
import { AnswerPad } from './AnswerPad.tsx'
import { AttackBox } from './AttackBox.tsx'
import { BonusBox } from './BonusBox.tsx'
import { FinalCard } from './FinalCard.tsx'
import { JoinForm } from './JoinForm.tsx'
import { PlayerHeader } from './PlayerHeader.tsx'
import { RaceButton } from './RaceButton.tsx'
import { ResultCard } from './ResultCard.tsx'
import { TakeawayCard } from './TakeawayCard.tsx'
import { WaitingCard } from './WaitingCard.tsx'

const rejoinSavedPlayer = (send: Send): void => {
  const saved = loadSavedPlayer()
  if (saved) send({ type: 'join', name: saved.name, token: saved.token })
}

function useRememberPlayer(me: Me | null): void {
  const name = me?.name
  const token = me?.token
  useEffect(() => {
    if (name && token) savePlayer({ name, token })
  }, [name, token])
}

// While a saved token is on its way back, a tap on Join would create a duplicate player and lose the score.
const isRejoining = (hasSavedPlayer: boolean, error: string | null): boolean => hasSavedPlayer && error === null

const showRaceButton = (view: PlayerView, me: Me): boolean => view.race_started && !me.race_done && view.phase !== 'finale'

export function PlayScreen() {
  const socket = useGameSocket<PlayerView>('play', rejoinSavedPlayer)
  const { view, send, error, clearError } = socket
  const [hasSavedPlayer] = useState(() => loadSavedPlayer() !== null)
  useRememberPlayer(view?.me ?? null)

  if (!view) return <p className="centered">Connecting…</p>
  if (!view.me && isRejoining(hasSavedPlayer, error)) return <p className="centered">Rejoining…</p>
  if (!view.me) return <div className="play"><JoinForm onJoin={(name) => send({ type: 'join', name })} error={error} /></div>
  if (view.me.kicked) return <p className="centered">You were removed by the host.</p>

  return (
    <div className="play">
      <PlayerHeader me={view.me} />
      <ErrorToast message={error} onDismiss={clearError} />
      <PhaseBody view={view} me={view.me} socket={socket} />
      {showRaceButton(view, view.me) && <RaceButton onDone={() => send({ type: 'race_done' })} />}
    </div>
  )
}

type BodyProps = { view: PlayerView; me: Me; socket: GameSocket<PlayerView> }

function PhaseBody({ view, me, socket }: BodyProps) {
  const { send, receivedAt } = socket
  const takeaway = <TakeawayCard takeaway={me.takeaway} onSend={(email) => send({ type: 'takeaway', email, consent: true })} />
  switch (view.phase) {
    case 'lobby':
      return (
        <>
          <WaitingCard message={waitingMessage(view, me)} />
          {takeaway}
        </>
      )
    case 'question_open':
      return view.question && (
        <AnswerPad question={view.question} myAnswer={view.my_answer} receivedAt={receivedAt} onAnswer={(option) => send({ type: 'answer', option })} />
      )
    case 'question_revealed':
      return view.result && <ResultCard result={view.result} rank={me.rank} />
    case 'break_it_open':
      return <AttackBox attacks={view.my_attacks} onSend={(text) => send({ type: 'attack', text })} />
    case 'bonus':
      return view.bonus && (
        <BonusBox
          bonus={view.bonus}
          onAsk={(text) => send({ type: 'bonus_question', text })}
          onVote={(questionId) => send({ type: 'bonus_vote', question_id: questionId })}
        />
      )
    case 'finale':
      return (
        <>
          <FinalCard me={me} awards={view.awards} />
          {takeaway}
        </>
      )
    default:
      return <WaitingCard message={waitingMessage(view, me)} />
  }
}

const waitingMessage = (view: PlayerView, me: Me): string => {
  if (view.phase === 'break_it_closed') return 'Attacks closed. Watch the big screen!'
  if (view.phase === 'race_podium') return 'Build race podium is on the big screen!'
  return `You're in, ${me.name}! Watch the big screen.`
}
