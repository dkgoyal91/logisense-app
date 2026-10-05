import type { Takeaway, TakeawayStatus } from '../types.ts'

const LOOKS_LIKE_EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const STATUS_TEXT: Record<TakeawayStatus, (hint: string) => string> = {
  queued: (hint) => `Sending to ${hint}…`,
  sent: (hint) => `✓ Sent to ${hint}. Check your inbox (and spam).`,
  saved: (hint) => `✓ Got it. We'll email ${hint} after the session.`,
  failed: (hint) => `Couldn't send to ${hint}. Please try again.`,
}

export const takeawayStatusText = (takeaway: Takeaway): string =>
  STATUS_TEXT[takeaway.status](takeaway.email_hint ?? 'your email')

export const canSendTakeaway = (email: string, consent: boolean): boolean =>
  consent && LOOKS_LIKE_EMAIL.test(email.trim())

const COUNT_LABELS: [TakeawayStatus, string][] = [['sent', 'sent'], ['failed', 'failed'], ['saved', 'collected'], ['queued', 'sending']]

export const takeawayCountsLabel = (counts: Partial<Record<TakeawayStatus, number>>): string => {
  const parts = COUNT_LABELS.filter(([status]) => counts[status]).map(([status, label]) => `${counts[status]} ${label}`)
  return `📩 Emails: ${parts.length ? parts.join(' · ') : 'none yet'}`
}
