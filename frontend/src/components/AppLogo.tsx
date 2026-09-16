import { useId } from 'react'

type AppLogoProps = {
  size?: number
  title?: string
}

/**
 * LogiSense brand mark: three waypoints tracing a routing path in an implied "L".
 * Mirrors public/logisense-mark.svg so the favicon and in-app logo stay identical.
 */
export function AppLogo({ size = 32, title }: AppLogoProps) {
  const gradientId = useId()

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      className="app-logo"
      role={title ? 'img' : 'presentation'}
      aria-label={title}
      aria-hidden={title ? undefined : true}
      focusable="false"
    >
      <defs>
        <linearGradient id={gradientId} x1="8" y1="6" x2="24" y2="26" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#34d399" />
          <stop offset="1" stopColor="#3b82f6" />
        </linearGradient>
      </defs>

      <rect width="32" height="32" rx="8" fill="#06111f" />
      <rect x="0.5" y="0.5" width="31" height="31" rx="7.5" fill="none" stroke="#34d399" strokeOpacity="0.24" />

      <path
        d="M10 8.5 V20 H22.5"
        fill="none"
        stroke={`url(#${gradientId})`}
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      <circle cx="10" cy="8.5" r="3" fill="#06111f" stroke="#34d399" strokeWidth="2.2" />
      <circle cx="10" cy="20" r="2.4" fill="#5eead4" />
      <circle cx="22.5" cy="20" r="3" fill="#06111f" stroke="#3b82f6" strokeWidth="2.2" />
    </svg>
  )
}
