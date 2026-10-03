export const OPTION_MARKS = ['▲', '◆', '●', '■'] as const

export const optionClass = (index: number): string => `opt opt-${index}`

export const sharePercent = (count: number, total: number): number =>
  total === 0 ? 0 : Math.round((count / total) * 100)
