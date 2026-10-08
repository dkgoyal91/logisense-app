import { describe, expect, it } from 'vitest'
import { gameSocketUrl, reconnectDelay } from './socket.ts'

describe('gameSocketUrl', () => {
  it('uses ws for http and wss for https', () => {
    expect(gameSocketUrl('play', { protocol: 'http:', host: 'localhost:5173', search: '' })).toBe('ws://localhost:5173/ws/game/play')
    expect(gameSocketUrl('show', { protocol: 'https:', host: 'x.trycloudflare.com', search: '' })).toBe('wss://x.trycloudflare.com/ws/game/show')
  })

  it('forwards the pin only for the host', () => {
    expect(gameSocketUrl('host', { protocol: 'http:', host: 'h', search: '?pin=12 34' })).toBe('ws://h/ws/game/host?pin=12%2034')
    expect(gameSocketUrl('play', { protocol: 'http:', host: 'h', search: '?pin=1234' })).toBe('ws://h/ws/game/play')
  })
})

describe('reconnectDelay', () => {
  it('backs off exponentially up to eight seconds', () => {
    expect([0, 1, 2, 3, 4, 10].map(reconnectDelay)).toEqual([500, 1000, 2000, 4000, 8000, 8000])
  })
})
