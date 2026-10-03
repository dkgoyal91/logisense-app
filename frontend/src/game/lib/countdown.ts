export const remainingSeconds = (secondsLeft: number, receivedAtMs: number, nowMs: number): number =>
  Math.min(secondsLeft, Math.max(0, secondsLeft - (nowMs - receivedAtMs) / 1000))

export const elapsedSeconds = (baseSeconds: number, receivedAtMs: number, nowMs: number): number =>
  baseSeconds + Math.max(0, Math.floor((nowMs - receivedAtMs) / 1000))

const twoDigits = (value: number): string => String(value).padStart(2, '0')

export const formatClock = (totalSeconds: number): string =>
  `${twoDigits(Math.floor(totalSeconds / 60))}:${twoDigits(Math.floor(totalSeconds % 60))}`
