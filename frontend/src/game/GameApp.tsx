import './game.css'
import { HostScreen } from './host/HostScreen.tsx'
import type { GameRole } from './lib/socket.ts'
import { PlayScreen } from './play/PlayScreen.tsx'
import { ShowScreen } from './show/ShowScreen.tsx'

const SCREENS = { show: ShowScreen, play: PlayScreen, host: HostScreen }

export function GameApp({ role }: { role: GameRole }) {
  const Screen = SCREENS[role]
  return (
    <div className="game">
      <Screen />
    </div>
  )
}
