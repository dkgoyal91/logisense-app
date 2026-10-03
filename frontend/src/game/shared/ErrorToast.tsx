import { useEffect } from 'react'

const TOAST_MS = 3500

type Props = { message: string | null; onDismiss: () => void }

export function ErrorToast({ message, onDismiss }: Props) {
  useEffect(() => {
    if (!message) return
    const timer = window.setTimeout(onDismiss, TOAST_MS)
    return () => window.clearTimeout(timer)
  }, [message, onDismiss])

  if (!message) return null
  return (
    <button type="button" className="toast" onClick={onDismiss}>
      {message}
    </button>
  )
}
