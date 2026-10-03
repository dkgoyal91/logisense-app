export type Phase =
  | 'lobby'
  | 'question_open'
  | 'question_revealed'
  | 'break_it_open'
  | 'break_it_closed'
  | 'race_podium'
  | 'bonus'
  | 'finale'

export type AttackLayer = 'scope' | 'validator' | 'templates' | 'gap' | 'answered'
export type AwardCategory = 'overall' | 'predictor' | 'hacker' | 'builder'

export type QuestionView = {
  index: number
  total: number
  text: string
  copilot_prompt: string
  concept: string
  options: string[]
  seconds_left: number
  answered_count: number
}

export type CopilotResult = {
  table: string | null
  sql: string | null
  row_count: number
  sample_rows: Record<string, unknown>[]
  summary: string
  error: string | null
}

export type RevealView = { correct_index: number; distribution: number[]; copilot: CopilotResult | null }
export type BoardEntry = { name: string; points: number }
export type BuilderEntry = { name: string; seconds: number }
export type Boards = { overall: BoardEntry[]; predictor: BoardEntry[]; hacker: BoardEntry[]; builder: BuilderEntry[] }
export type AttackSummary = { id: string; text: string; layer: AttackLayer; message: string; starred: boolean }
export type AttackView = AttackSummary & { name: string }
export type RaceView = { started: boolean; elapsed_seconds: number; finishers: BuilderEntry[] }
export type BonusQuestionView = { id: string; text: string; name: string; votes: number; voted: boolean; mine: boolean }
export type BonusAnswer = CopilotResult & { question_id: string; text: string }
export type BonusView = { questions: BonusQuestionView[]; answer: BonusAnswer | null }
export type LobbyView = { count: number; names: string[] }

export type ShowView = {
  phase: Phase
  hands_mode: boolean
  join_url: string
  lobby: LobbyView
  question: QuestionView | null
  reveal: RevealView | null
  race: RaceView
  attacks: AttackView[]
  boards: Boards
  bonus: BonusView | null
}

export type RosterEntry = { id: string; name: string; total: number; kicked: boolean; race_done: boolean; demo_awarded: boolean }
export type HostView = ShowView & { players: RosterEntry[]; answer_key: string | null }

export type Me = { id: string; name: string; token: string; total: number; rank: number | null; race_done: boolean; kicked: boolean }
export type MyResult = { answered: boolean; correct: boolean; points: number; correct_option: string }
export type Award = { category: AwardCategory; place: number }

export type PlayerView = {
  phase: Phase
  me: Me | null
  question: QuestionView | null
  my_answer: number | null
  result: MyResult | null
  my_attacks: AttackSummary[]
  race_started: boolean
  bonus: BonusView | null
  awards: Award[]
}

export type HostAction =
  | 'start_race'
  | 'next'
  | 'reveal'
  | 'skip'
  | 'kick'
  | 'star_attack'
  | 'award_demo'
  | 'ask_bonus'
  | 'hands_mode'
  | 'reset'

export type HostExtras = {
  player_id?: string
  attack_id?: string
  question_id?: string
  confirm?: string
  expected_phase?: Phase
}

export type ClientMessage =
  | { type: 'join'; name: string; token?: string }
  | { type: 'answer'; option: number }
  | { type: 'attack'; text: string }
  | { type: 'race_done' }
  | { type: 'bonus_question'; text: string }
  | { type: 'bonus_vote'; question_id: string }
  | ({ type: 'host'; action: HostAction } & HostExtras)

export type ServerMessage = { type: 'state'; view: unknown } | { type: 'error'; message: string }

export type Send = (message: ClientMessage) => void
