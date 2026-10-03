import { useEffect, useState, type ReactNode } from 'react'

const DISARM_MS = 3000

type Props = { onConfirm: () => void; children: ReactNode; className?: string; disabled?: boolean }

export function ConfirmButton({ onConfirm, children, className = '', disabled = false }: Props) {
  const [armed, setArmed] = useState(false)

  useEffect(() => {
    if (!armed) return
    const timer = window.setTimeout(() => setArmed(false), DISARM_MS)
    return () => window.clearTimeout(timer)
  }, [armed])

  const handleClick = () => {
    if (!armed) {
      setArmed(true)
      return
    }
    setArmed(false)
    onConfirm()
  }

  return (
    <button type="button" className={`${className}${armed ? ' armed' : ''}`} disabled={disabled} onClick={handleClick}>
      {armed ? 'Tap again to confirm' : children}
    </button>
  )
}
