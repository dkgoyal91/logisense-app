import { useEffect, useState } from 'react'
import { fireConfetti } from '../lib/confetti.ts'
import { broadcastBannerText } from '../lib/takeaway.ts'
import type { TakeawayBroadcast } from '../types.ts'

const SENT_BANNER_MS = 15000

export function TakeawayBanner({ broadcast }: { broadcast: TakeawayBroadcast | null }) {
  const visible = useBannerVisibility(broadcast)
  if (!broadcast || !visible) return null
  return <div className={`takeaway-banner takeaway-banner--${broadcast.status}`}>{broadcastBannerText(broadcast)}</div>
}

function useBannerVisibility(broadcast: TakeawayBroadcast | null): boolean {
  const [hiddenFor, setHiddenFor] = useState<string | null>(null)
  const key = broadcast ? `${broadcast.status}:${broadcast.count}` : null
  useEffect(() => {
    if (broadcast?.status !== 'sent' || !key) return
    fireConfetti()
    const timer = window.setTimeout(() => setHiddenFor(key), SENT_BANNER_MS)
    return () => window.clearTimeout(timer)
  }, [broadcast?.status, key])
  return key !== null && hiddenFor !== key
}
