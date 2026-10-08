import { describe, expect, it } from 'vitest'
import { optionClass, sharePercent } from './options.ts'

describe('sharePercent', () => {
  it('rounds to whole percent and handles no votes', () => {
    expect(sharePercent(1, 3)).toBe(33)
    expect(sharePercent(0, 0)).toBe(0)
  })
})

describe('optionClass', () => {
  it('gives each option its own colour class', () => {
    expect(optionClass(2)).toBe('opt opt-2')
  })
})
