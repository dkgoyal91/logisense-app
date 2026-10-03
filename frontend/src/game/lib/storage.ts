const PLAYER_KEY = 'beat-the-copilot:player'

export type SavedPlayer = { name: string; token: string }

const parseSavedPlayer = (raw: string): SavedPlayer | null => {
  const value = JSON.parse(raw) as Partial<SavedPlayer>
  return typeof value.name === 'string' && typeof value.token === 'string' ? { name: value.name, token: value.token } : null
}

export const loadSavedPlayer = (): SavedPlayer | null => {
  try {
    const raw = window.localStorage.getItem(PLAYER_KEY)
    return raw ? parseSavedPlayer(raw) : null
  } catch {
    return null
  }
}

export const savePlayer = (player: SavedPlayer): void => {
  try {
    window.localStorage.setItem(PLAYER_KEY, JSON.stringify(player))
  } catch {
    // Private mode or blocked storage: the player simply cannot auto-rejoin.
  }
}
