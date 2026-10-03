import { describe, expect, it } from 'vitest'
import { elapsedSeconds, formatClock, remainingSeconds } from './countdown.ts'

describe('remainingSeconds', () => {
  it('counts down from the server value and clamps to the valid range', () => {
    expect(remainingSeconds(20, 1000, 6000)).toBe(15)
    expect(remainingSeconds(20, 1000, 40000)).toBe(0)
    expect(remainingSeconds(20, 1000, 500)).toBe(20)
  })
})

describe('elapsedSeconds', () => {
  it('adds local time to the server base and never goes backwards', () => {
    expect(elapsedSeconds(60, 1000, 4000)).toBe(63)
    expect(elapsedSeconds(60, 1000, 0)).toBe(60)
  })
})

describe('formatClock', () => {
  it('formats minutes and seconds', () => {
    expect(formatClock(0)).toBe('00:00')
    expect(formatClock(754)).toBe('12:34')
  })
})
