type IconName =
  | 'compose'
  | 'more'
  | 'stop'
  | 'send'
  | 'copy'
  | 'refresh'
  | 'chart'
  | 'map'
  | 'summary'
  | 'spark'
  | 'chevron-right'
  | 'chevron-down'
  | 'search'
  | 'sort'
  | 'sort-asc'
  | 'sort-desc'

type IconProps = {
  name: IconName
  size?: number
  title?: string
}

// Single-path-per-icon set drawn on a 24x24 grid, stroked with currentColor so icons
// inherit whatever button variant they sit inside.
const ICON_PATHS: Record<IconName, string> = {
  compose: 'M4 20h4L19 9a2.1 2.1 0 0 0-3-3L5 17v3Z',
  more: 'M12 6h.01M12 12h.01M12 18h.01',
  stop: 'M7 7h10v10H7z',
  send: 'M22 2 11 13M22 2l-7 20-4-9-9-4 20-7Z',
  copy: 'M9 9h9v11H9zM6 15H4V4h11v2',
  refresh: 'M20 12a8 8 0 1 1-2.5-5.8M20 4v4h-4',
  chart: 'M5 19V11M12 19V5M19 19v-6M3 19h18',
  map: 'M12 21s6-5.2 6-10a6 6 0 1 0-12 0c0 4.8 6 10 6 10Z M12 11h.01',
  summary: 'M5 6h14M5 11h14M5 16h9',
  spark: 'M12 4l1.7 4.8L18.5 10l-4.8 1.7L12 16.5l-1.7-4.8L5.5 10l4.8-1.2L12 4Z',
  'chevron-right': 'M9 6l6 6-6 6',
  'chevron-down': 'M6 9l6 6 6-6',
  search: 'M11 18a7 7 0 1 1 0-14 7 7 0 0 1 0 14ZM20 20l-4-4',
  sort: 'M8 9l4-4 4 4M8 15l4 4 4-4',
  'sort-asc': 'M8 14l4-4 4 4',
  'sort-desc': 'M8 10l4 4 4-4',
}

const DOT_ICONS: IconName[] = ['more']

export function Icon({ name, size = 16, title }: IconProps) {
  const isDotIcon = DOT_ICONS.includes(name)

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      role={title ? 'img' : 'presentation'}
      aria-label={title}
      aria-hidden={title ? undefined : true}
      focusable="false"
      className="ls-icon"
    >
      <path d={ICON_PATHS[name]} strokeWidth={isDotIcon ? 2.6 : undefined} />
    </svg>
  )
}
