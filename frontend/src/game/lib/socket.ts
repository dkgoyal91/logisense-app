export type GameRole = 'show' | 'play' | 'host'

type LocationLike = Pick<Location, 'protocol' | 'host' | 'search'>

const BASE_RECONNECT_DELAY_MS = 500
const MAX_RECONNECT_DELAY_MS = 8000

export const gameSocketUrl = (role: GameRole, location: LocationLike): string => {
  const scheme = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${scheme}://${location.host}/ws/game/${role}${hostPinQuery(role, location.search)}`
}

const hostPinQuery = (role: GameRole, search: string): string => {
  const pin = role === 'host' ? new URLSearchParams(search).get('pin') : null
  return pin ? `?pin=${encodeURIComponent(pin)}` : ''
}

export const reconnectDelay = (attempt: number): number =>
  Math.min(BASE_RECONNECT_DELAY_MS * 2 ** attempt, MAX_RECONNECT_DELAY_MS)
