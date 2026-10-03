import { describe, expect, it } from 'vitest'
import { resolveJoinUrl } from './links.ts'

describe('resolveJoinUrl', () => {
  it('prefers the configured public URL', () => {
    expect(resolveJoinUrl('https://x.trycloudflare.com/play', 'http://localhost:8000')).toBe('https://x.trycloudflare.com/play')
  })

  it('falls back to the current origin', () => {
    expect(resolveJoinUrl('', 'http://192.168.1.4:8000')).toBe('http://192.168.1.4:8000/play')
  })
})
