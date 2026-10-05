import { describe, expect, it } from 'vitest'
import { canSendTakeaway, takeawayCountsLabel, takeawayStatusText } from './takeaway.ts'

describe('takeawayStatusText', () => {
  it('describes each delivery state with the masked address', () => {
    expect(takeawayStatusText({ status: 'queued', email_hint: 'a•••@x.com' })).toBe('Sending to a•••@x.com…')
    expect(takeawayStatusText({ status: 'sent', email_hint: 'a•••@x.com' })).toBe('✓ Sent to a•••@x.com. Check your inbox (and spam).')
    expect(takeawayStatusText({ status: 'saved', email_hint: 'a•••@x.com' })).toBe("✓ Got it. We'll email a•••@x.com after the session.")
    expect(takeawayStatusText({ status: 'failed', email_hint: 'a•••@x.com' })).toBe("Couldn't send to a•••@x.com. Please try again.")
  })
})

describe('canSendTakeaway', () => {
  it('needs consent and something that looks like an email', () => {
    expect(canSendTakeaway('ananya@nagarro.com', true)).toBe(true)
    expect(canSendTakeaway('ananya@nagarro.com', false)).toBe(false)
    expect(canSendTakeaway('ananya', true)).toBe(false)
  })
})

describe('takeawayCountsLabel', () => {
  it('summarises delivery counts for the host', () => {
    expect(takeawayCountsLabel({ sent: 3, failed: 1, saved: 2 })).toBe('📩 Emails: 3 sent · 1 failed · 2 collected')
    expect(takeawayCountsLabel({})).toBe('📩 Emails: none yet')
  })
})
