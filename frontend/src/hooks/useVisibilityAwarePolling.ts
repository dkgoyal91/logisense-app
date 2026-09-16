import { useEffect, useRef } from 'react'

type PollingOptions = {
  intervalMs: number
  enabled: boolean
  onPoll: () => void
}

const isDocumentVisible = (): boolean => document.visibilityState === 'visible'

/**
 * Polls `onPoll` on an interval, but only while polling is enabled and the tab is in
 * the foreground. A backgrounded tab stops issuing requests entirely, and resuming
 * polls immediately so what is on screen is fresh the moment it matters again.
 */
export function useVisibilityAwarePolling({ intervalMs, enabled, onPoll }: PollingOptions) {
  const latestOnPoll = useRef(onPoll)

  useEffect(() => {
    latestOnPoll.current = onPoll
  }, [onPoll])

  useEffect(() => {
    if (!enabled) {
      return
    }

    let timerId: number | undefined

    const stopPolling = () => {
      if (timerId !== undefined) {
        window.clearInterval(timerId)
        timerId = undefined
      }
    }

    const startPolling = () => {
      if (timerId !== undefined) {
        return
      }
      latestOnPoll.current()
      timerId = window.setInterval(() => latestOnPoll.current(), intervalMs)
    }

    const syncWithVisibility = () => {
      if (isDocumentVisible()) {
        startPolling()
      } else {
        stopPolling()
      }
    }

    syncWithVisibility()
    document.addEventListener('visibilitychange', syncWithVisibility)

    return () => {
      stopPolling()
      document.removeEventListener('visibilitychange', syncWithVisibility)
    }
  }, [enabled, intervalMs])
}
