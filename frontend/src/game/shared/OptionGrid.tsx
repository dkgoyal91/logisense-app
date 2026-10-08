import { OPTION_MARKS, optionClass, sharePercent } from '../lib/options.ts'

type Props = { options: string[]; distribution?: number[]; correctIndex?: number }

const revealClass = (index: number, correctIndex?: number): string => {
  if (correctIndex === undefined) return ''
  return index === correctIndex ? ' correct' : ' dimmed'
}

export function OptionGrid({ options, distribution, correctIndex }: Props) {
  const total = distribution?.reduce((sum, count) => sum + count, 0) ?? 0
  return (
    <div className="option-grid">
      {options.map((option, index) => (
        <div key={option} className={`${optionClass(index)}${revealClass(index, correctIndex)}`}>
          <span className="opt-mark">{OPTION_MARKS[index]}</span>
          <span className="opt-label">{option}</span>
          {distribution && <span className="opt-count">{distribution[index]}</span>}
          {distribution && <span className="opt-bar" style={{ width: `${sharePercent(distribution[index], total)}%` }} />}
        </div>
      ))}
    </div>
  )
}
