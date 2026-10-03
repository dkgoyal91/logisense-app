import { describe, expect, it } from 'vitest'
import { pickGameRoute } from './route.ts'

describe('pickGameRoute', () => {
  it('maps game paths and ignores everything else', () => {
    expect(pickGameRoute('/show')).toBe('show')
    expect(pickGameRoute('/play/')).toBe('play')
    expect(pickGameRoute('/host')).toBe('host')
    expect(pickGameRoute('/')).toBeNull()
    expect(pickGameRoute('/dashboard')).toBeNull()
  })
})
