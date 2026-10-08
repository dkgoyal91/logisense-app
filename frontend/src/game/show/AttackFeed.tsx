import { resolveJoinUrl } from '../lib/links.ts'
import { LAYER_LABELS } from '../shared/labels.ts'
import type { AttackView } from '../types.ts'

type Props = { attacks: AttackView[]; open: boolean; joinUrl: string }

export function AttackFeed({ attacks, open, joinUrl }: Props) {
  return (
    <div className="attacks">
      <header className="stage-head">
        <h2>{open ? 'Break it! Send attacks from your phone' : 'Attacks closed'}</h2>
        <span className="muted">{resolveJoinUrl(joinUrl, window.location.origin)}</span>
      </header>
      <ul className="attack-feed">
        {attacks.map((attack) => (
          <li key={attack.id} className={`attack layer-${attack.layer}`}>
            <div className="attack-top">
              <span className="attack-badge">{LAYER_LABELS[attack.layer]}</span>
              {attack.starred && <span className="star">⭐ Best attack</span>}
              <span className="attack-name">{attack.name}</span>
            </div>
            <p className="attack-text">{attack.text}</p>
            <p className="attack-message">{attack.message}</p>
          </li>
        ))}
      </ul>
    </div>
  )
}
