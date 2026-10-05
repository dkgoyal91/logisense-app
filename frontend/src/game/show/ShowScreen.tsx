import { useGameSocket } from '../hooks/useGameSocket.ts'
import type { ShowView } from '../types.ts'
import { AttackFeed } from './AttackFeed.tsx'
import { BonusBoard } from './BonusBoard.tsx'
import { Finale } from './Finale.tsx'
import { LobbyWall } from './LobbyWall.tsx'
import { QuestionStage } from './QuestionStage.tsx'
import { RaceClock } from './RaceClock.tsx'
import { RacePodium } from './RacePodium.tsx'
import { RevealPanel } from './RevealPanel.tsx'
import { TakeawayBanner } from './TakeawayBanner.tsx'

export function ShowScreen() {
  const { view, receivedAt, connected } = useGameSocket<ShowView>('show')
  if (!view) return <p className="centered">Connecting to the game server…</p>
  return (
    <div className="show">
      {!connected && <div className="offline-banner">Reconnecting…</div>}
      <TakeawayBanner broadcast={view.takeaway_broadcast} />
      <ShowStage view={view} receivedAt={receivedAt} />
      {view.race.started && view.phase !== 'finale' && <RaceClock race={view.race} receivedAt={receivedAt} />}
    </div>
  )
}

function ShowStage({ view, receivedAt }: { view: ShowView; receivedAt: number }) {
  switch (view.phase) {
    case 'lobby':
      return <LobbyWall lobby={view.lobby} joinUrl={view.join_url} />
    case 'question_open':
      return view.question && <QuestionStage question={view.question} handsMode={view.hands_mode} receivedAt={receivedAt} />
    case 'question_revealed':
      return view.question && view.reveal && (
        <RevealPanel question={view.question} reveal={view.reveal} boards={view.boards} handsMode={view.hands_mode} />
      )
    case 'break_it_open':
    case 'break_it_closed':
      return <AttackFeed attacks={view.attacks} open={view.phase === 'break_it_open'} joinUrl={view.join_url} />
    case 'race_podium':
      return <RacePodium finishers={view.race.finishers} />
    case 'bonus':
      return view.bonus && <BonusBoard bonus={view.bonus} />
    case 'finale':
      return <Finale boards={view.boards} />
  }
}
