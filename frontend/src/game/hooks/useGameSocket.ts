import { useCallback, useEffect, useRef, useState } from 'react'
import { gameSocketUrl, reconnectDelay, type GameRole } from '../lib/socket.ts'
import type { ClientMessage, Send, ServerMessage } from '../types.ts'

const POLICY_VIOLATION = 1008

export type GameSocket<View> = {
  view: View | null
  receivedAt: number
  connected: boolean
  error: string | null
  send: Send
  clearError: () => void
}

export function useGameSocket<View>(role: GameRole, onOpen?: (send: Send) => void): GameSocket<View> {
  const [view, setView] = useState<View | null>(null)
  const [receivedAt, setReceivedAt] = useState(0)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const socketRef = useRef<WebSocket | null>(null)
  const onOpenRef = useRef(onOpen)

  useEffect(() => {
    onOpenRef.current = onOpen
  }, [onOpen])

  const send = useCallback((message: ClientMessage) => {
    const socket = socketRef.current
    if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message))
  }, [])

  const handleMessage = useCallback((raw: string) => {
    const message = JSON.parse(raw) as ServerMessage
    if (message.type === 'error') {
      setError(message.message)
      return
    }
    setView(message.view as View)
    setReceivedAt(Date.now())
  }, [])

  useEffect(() => {
    let attempt = 0
    let stopped = false
    let timer: number | undefined

    const connect = () => {
      const socket = new WebSocket(gameSocketUrl(role, window.location))
      socketRef.current = socket
      socket.onopen = () => {
        attempt = 0
        setConnected(true)
        onOpenRef.current?.(send)
      }
      socket.onmessage = (event) => handleMessage(String(event.data))
      socket.onclose = (event) => {
        setConnected(false)
        if (event.code === POLICY_VIOLATION) {
          stopped = true
          setError('Access denied: check the host PIN in the URL.')
        }
        if (!stopped) timer = window.setTimeout(connect, reconnectDelay(attempt++))
      }
    }

    connect()
    return () => {
      stopped = true
      window.clearTimeout(timer)
      socketRef.current?.close()
    }
  }, [role, send, handleMessage])

  const clearError = useCallback(() => setError(null), [])
  return { view, receivedAt, connected, error, send, clearError }
}
