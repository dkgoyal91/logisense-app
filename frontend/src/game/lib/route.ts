import type { GameRole } from './socket.ts'

const GAME_ROUTES: Record<string, GameRole> = { '/show': 'show', '/play': 'play', '/host': 'host' }

export const pickGameRoute = (pathname: string): GameRole | null =>
  GAME_ROUTES[pathname.replace(/\/+$/, '')] ?? null
