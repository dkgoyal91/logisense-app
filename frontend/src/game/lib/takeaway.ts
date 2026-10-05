import type { Takeaway, TakeawayBroadcast, TakeawayStatus } from '../types.ts'

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

const people = (count: number): string => `${count} ${count === 1 ? 'person' : 'people'}`

export const broadcastBannerText = (broadcast: TakeawayBroadcast): string => {
  if (broadcast.status === 'sending') return `📩 Sending the repo to ${people(broadcast.count)}…`
  if (broadcast.status === 'sent') return `✓ Sent the repo to ${people(broadcast.count)}! Check your inbox.`
  return "The email didn't go out. We'll send it after the session."
}

export const sendButtonLabel = (waiting: number, broadcast: TakeawayBroadcast | null): string => {
  if (broadcast?.status === 'sending') return '📩 Sending…'
  return waiting > 0 ? `📩 Send email to everyone (${waiting} waiting)` : '📩 Send email (nobody waiting yet)'
}
