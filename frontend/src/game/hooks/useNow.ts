import { useEffect, useState } from 'react'
import { elapsedSeconds, remainingSeconds } from '../lib/countdown.ts'

export function useNow(intervalMs: number, active: boolean): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!active) return
    const timer = window.setInterval(() => setNow(Date.now()), intervalMs)
    return () => window.clearInterval(timer)
  }, [intervalMs, active])
  return now
}

export function useCountdown(secondsLeft: number, receivedAt: number): number {
  const now = useNow(200, secondsLeft > 0)
  return Math.ceil(remainingSeconds(secondsLeft, receivedAt, now))
}

export function useElapsed(baseSeconds: number, receivedAt: number, active: boolean): number {
  const now = useNow(1000, active)
  return elapsedSeconds(baseSeconds, receivedAt, now)
}
