import { useQrDataUrl } from '../hooks/useQrDataUrl.ts'
import { resolveJoinUrl } from '../lib/links.ts'
import type { LobbyView } from '../types.ts'

export function LobbyWall({ lobby, joinUrl }: { lobby: LobbyView; joinUrl: string }) {
  const url = resolveJoinUrl(joinUrl, window.location.origin)
  const qr = useQrDataUrl(url)
  return (
    <div className="lobby">
      <div>
        <h1>Beat the Copilot</h1>
        <p className="lobby-sub">Scan to play</p>
        {qr && <img className="qr" src={qr} alt={`QR code for ${url}`} />}
        <p className="lobby-url">{url}</p>
      </div>
      <div>
        <p className="lobby-count">
          {lobby.count} player{lobby.count === 1 ? '' : 's'}
        </p>
        <ul className="name-cloud">
          {lobby.names.map((name) => <li key={name} className="name-chip">{name}</li>)}
        </ul>
      </div>
    </div>
  )
}
