import type { AttackLayer, AwardCategory } from '../types.ts'

export const LAYER_LABELS: Record<AttackLayer, string> = {
  scope: 'Scope guard',
  validator: 'SQL validator',
  templates: 'Templates only',
  gap: 'Gap found!',
  answered: 'Answered safely',
}

export const AWARD_LABELS: Record<AwardCategory, string> = {
  overall: 'Overall',
  predictor: 'Top Predictor',
  hacker: 'Best Hacker',
  builder: 'Fastest Builder',
}
