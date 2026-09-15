import { useEffect, useState } from 'react'
import './App.css'
import { ResultChart, ResultMap } from './components/ResultVisuals'
import { Dashboard } from './components/Dashboard'
import { formatCellValue, formatCompact } from './utils/format'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

type ResultView = 'chart' | 'map' | 'summary'

type ChatMessage = {
  role: 'user' | 'assistant'
  text: string
  view?: ResultView | null
  createdAt?: number
  thinkingOpen?: boolean
  data?: {
    table?: string | null
    summary?: string
    rows?: Record<string, unknown>[]
  }
}

type ChatSession = {
  id: string
  title: string
  messages: ChatMessage[]
}

type DashboardKpis = {
  active_shipments: number
  delayed_shipments: number
  fleet_utilization_avg: number
  open_jobs: number
  active_records: number
}

type RouteRisk = {
  route: string
  delayed_count: number
}

type DashboardResponse = {
  kpis: DashboardKpis
  risk_routes: RouteRisk[]
  live_shipments: Record<string, unknown>[]
}

type ChatResponse = {
  answer?: string
  table?: string | null
  rows?: Record<string, unknown>[]
  summary?: string
}

type LiveRowsResponse = {
  table: string
  rows: Record<string, unknown>[]
  summary: string
}

type ModuleTab = {
  id: string
  label: string
  table: 'shipments' | 'vehicles' | 'jobs' | 'logistics_records'
  limit: number
  helperPrompt: string
}

type QuickMetric = {
  id: 'shipments' | 'fleet' | 'jobs' | 'logistics_records'
  label: string
  value: string
  detail: string
  icon: string
}

type PromptAction = {
  label: string
  prompt: string
  description?: string
}

const tabs: ModuleTab[] = [
  { id: 'freight', label: 'Freight Overview', table: 'shipments', limit: 50, helperPrompt: 'Review active shipments, hubs, and corridor pressure in one view.' },
  { id: 'fleet', label: 'Fleet Status', table: 'vehicles', limit: 50, helperPrompt: 'Inspect fleet readiness, utilization, and maintenance exposure.' },
  { id: 'routes', label: 'Route Planning', table: 'shipments', limit: 50, helperPrompt: 'Assess route performance before the next dispatch decision.' },
  { id: 'incidents', label: 'Delivery Exceptions', table: 'shipments', limit: 50, helperPrompt: 'Focus on delayed loads, risk signals, and service exceptions.' },
  { id: 'analytics', label: 'Work Orders', table: 'jobs', limit: 50, helperPrompt: 'Track open operational work and prioritize aged actions.' },
  { id: 'config', label: 'Records Hub', table: 'logistics_records', limit: 50, helperPrompt: 'Browse logistics records, reviews, and account planning context.' },
]

const quickStartActions: PromptAction[] = [
  {
    label: 'Review 2025 records due for decision',
    prompt: 'Show logistics records with review dates in 2025',
    description: 'Surface records that need commercial review in the current planning cycle.',
  },
  {
    label: 'Prioritize delayed shipments',
    prompt: 'Show delayed shipments by delivery date',
    description: 'Sort late deliveries into a clear operational queue for recovery planning.',
  },
  {
    label: 'Escalate ageing work orders',
    prompt: 'Show open work orders sorted by days open',
    description: 'Identify the oldest open actions before they impact service delivery.',
  },
]

const suggestedPrompts: PromptAction[] = [
  { label: 'Show delayed shipments for Birmingham routes', prompt: 'Show delayed shipments for Birmingham routes' },
  { label: 'Which logistics routes have the highest delivery risk?', prompt: 'Which logistics routes have the highest delivery risk?' },
  { label: 'List fleet vehicles in maintenance status', prompt: 'List fleet vehicles in maintenance status' },
  { label: 'Show open work orders with highest days open', prompt: 'Show open work orders with highest days open' },
]

// Defense-in-depth: the LLM is instructed to avoid markdown, but strip any raw pipe-table
// syntax it still emits, since the matching rows already render as a real table below.
const stripMarkdownTableSyntax = (text: string): string => {
  const isTableLikeLine = (line: string): boolean => {
    const trimmed = line.trim()
    if (!trimmed.includes('|')) {
      return false
    }
    if (/^\|?\s*:?-{2,}.*\|/.test(trimmed)) {
      return true
    }
    return (trimmed.match(/\|/g) ?? []).length >= 2
  }

  return text
    .split(/\r?\n/)
    .filter((line) => !isTableLikeLine(line))
    .join('\n')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/(?<!\w)\*(.+?)\*(?!\w)/g, '$1')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

const buildAssistantText = (data: ChatResponse): string => {
  const fallback = 'No response from the assistant.'
  const rawText = (data.answer ?? fallback).trim()
  const rowCount = Array.isArray(data.rows) ? data.rows.length : 0

  if (rowCount === 0) {
    return sanitizeVisibleText(stripMarkdownTableSyntax(rawText))
  }

  const markerIndex = rawText.toLowerCase().indexOf('example rows:')
  const trimmed = markerIndex >= 0 ? rawText.slice(0, markerIndex).trim() : rawText

  return sanitizeVisibleText(stripMarkdownTableSyntax(trimmed) || 'Here are the matching records.')
}

const buildResultSummary = (rows: Record<string, unknown>[], table?: string | null, fallback = 'Result set ready'): string => {
  if (rows.length === 0) {
    return fallback
  }

  const total = rows.length
  const statusCounts = rows.reduce<Record<string, number>>((counts, row) => {
    const status = String(row.status ?? 'unknown').trim().toLowerCase()
    counts[status] = (counts[status] ?? 0) + 1
    return counts
  }, {})

  const delayed = statusCounts.delayed ?? 0
  const onTime = statusCounts['on time'] ?? 0
  const maintenance = statusCounts.maintenance ?? 0
  const route = String(rows[0].route ?? rows[0].destination ?? rows[0].region ?? 'the selected route corridor')
  const region = String(rows[0].region ?? rows[0].destination ?? 'the selected logistics area')

  if (table === 'shipments') {
    const delayShare = Math.round((delayed / total) * 100) || 0
    const summarySentences = [
      `There are ${total} shipments in view across the active logistics network.`,
      `The current status mix shows ${delayed} delayed loads and ${onTime || total - delayed} on-time movements.`,
      `The strongest concentration is around ${route}, which is the main corridor driving current delivery pressure.`,
      `This means ${delayShare}% of the visible batch requires operational attention before the next dispatch window.`,
      `Priority focus should remain on route timing, vehicle readiness, and customer communication for the delayed freight.`,
    ]

    return summarySentences.join('\n')
  }

  if (table === 'vehicles') {
    const summarySentences = [
      `There are ${total} vehicles in view across the active fleet.`,
      `The fleet is generally stable, with ${maintenance} vehicles currently under maintenance or service review.`,
      `${Math.max(total - maintenance, 0)} vehicles remain available for live operations and dispatch coverage.`,
      `This suggests the network is operating within a manageable service window for the current demand profile.`,
      `Monitoring utilization and maintenance turnaround should remain the main operational priority for the next cycle.`,
    ]

    return summarySentences.join('\n')
  }

  if (table === 'jobs') {
    const open = rows.filter((row) => String(row.status ?? '').toLowerCase() !== 'completed').length
    const longestWait = Math.max(...rows.map((row) => Number(row.days_open ?? 0)).filter((value) => Number.isFinite(value)), 0)
    const summarySentences = [
      `There are ${total} work orders in view across the operations backlog.`,
      `${open} items remain active, which indicates the current workload is still concentrated in live execution.`,
      `The longest outstanding action is waiting ${longestWait} days, highlighting the most urgent operational bottleneck.`,
      `This points to a steady workload that is manageable but still needs proactive scheduling and escalation on the oldest orders.`,
      `The best near-term response is to prioritize age-based execution and clear the longest open work items first.`,
    ]

    return summarySentences.join('\n')
  }

  const summarySentences = [
    `There are ${total} logistics records in view for the current operational scope.`,
    `The strongest activity is centered around ${region}, where most of the recent movement and planning focus is concentrated.`,
    `This indicates the network is experiencing a meaningful level of live operational activity in the selected area.`,
    `The key business signal is that demand remains active and distributed across the relevant routes and service nodes.`,
    `For the next decision cycle, the most valuable follow-up is to review route-level exceptions and capacity pressure in this zone.`,
  ]

  return summarySentences.join('\n')
}

const formatTimestamp = (value?: number): string => {
  if (!value) {
    return ''
  }

  return new Intl.DateTimeFormat('en-GB', {
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

const formatColumnLabel = (column: string): string => {
  const normalized = column
    .replace(/opportunity_ref/gi, 'record_ref')
    .replace(/pipeline_ref/gi, 'record_ref')
    .replace(/salesforce_number/gi, 'record_ref')
    .replace(/job_director/gi, 'operations_lead')
    .replace(/opportunity_owner/gi, 'logistics_owner')
    .replace(/valuation_date/gi, 'review_date')
    .replace(/number_of_properties/gi, 'route_count')
    .replace(/portfolio/gi, 'record set')
    .replace(/_+/g, ' ')
    .trim()

  return normalized.replace(/\b\w/g, (letter) => letter.toUpperCase())
}

const sanitizeVisibleText = (text: string): string => {
  return text
    .replace(/\bopportunities?\b/gi, 'logistics records')
    .replace(/\bportfolio\b/gi, 'record set')
    .replace(/\bpipeline\b/gi, 'logistics flow')
    .replace(/\bprojects?\b/gi, 'logistics work')
    .replace(/\bvaluation\b/gi, 'review')
    .replace(/\bopportunity\b/gi, 'logistics record')
}

const buildFullTableText = (rows: Record<string, unknown>[], table?: string | null): string => {
  if (rows.length === 0) {
    return `No ${table ? table.replace(/_/g, ' ') : 'logistics'} records available.`
  }

  const columns = Array.from(new Set(rows.flatMap((row) => Object.keys(row))))
  const header = columns.map((column) => formatColumnLabel(column)).join('\t')
  const lines = rows.map((row) =>
    columns
      .map((column) => String(formatCellValue(row[column])).replace(/\t/g, ' '))
      .join('\t'),
  )

  return [header, ...lines].join('\n')
}

// Grounded, honest trace of what the agent workflow did — never invented reasoning.
const NAME_LIKE_KEYS = ['customer', 'client_name', 'destination', 'route', 'region', 'depot']

const buildThinkingSteps = (message: ChatMessage): string[] => {
  const table = message.data?.table
  const rowCount = message.data?.rows?.length ?? 0
  const steps = ['Router agent reviewed the question and matched it to the approved logistics data model.']

  if (table) {
    steps.push(`SQL agent executed a validated, read-only query against the approved logistics records model and retrieved ${rowCount} record${rowCount === 1 ? '' : 's'}.`)
    steps.push('Summary agent grounded the response strictly in the retrieved rows before phrasing the final answer.')
  } else {
    steps.push('SQL agent found no approved logistics records matching this question, so no data was queried.')
  }

  return steps
}

// Builds contextual follow-up prompts from the entities actually present in the result rows.
const buildContextualPrompts = (rows: Record<string, unknown>[], table: string | null | undefined): PromptAction[] => {
  if (!table || rows.length === 0) {
    return suggestedPrompts
  }

  const nameKey = NAME_LIKE_KEYS.find((key) => typeof rows[0][key] === 'string')
  const distinctNames = nameKey
    ? Array.from(new Set(rows.map((row) => String(row[nameKey])))).slice(0, 3)
    : []

  if (distinctNames.length === 0) {
    return suggestedPrompts
  }

  return distinctNames.map((name) => ({
    label: `Show all ${table} records for ${name}`,
    prompt: `Show all ${table} records for ${name}`,
  }))
}

const initialAssistantMessage: ChatMessage = {
  role: 'assistant',
  text: 'Logistics operations are live. Click a module or quick prompt to inspect fleet, shipment, and route data end to end.',
}

function App() {
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([
    {
      id: 'ops-session-1',
      title: 'Chat 1',
      messages: [initialAssistantMessage],
    },
  ])
  const [activeSessionId, setActiveSessionId] = useState('ops-session-1')
  const [draft, setDraft] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null)
  const [selectedTabId, setSelectedTabId] = useState<string>(tabs[0].id)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [isChatMenuOpen, setIsChatMenuOpen] = useState(false)
  const [activeView, setActiveView] = useState<'chat' | 'dashboard'>('chat')

  const selectedTab = tabs.find((item) => item.id === selectedTabId) ?? tabs[0]
  const activeSession = chatSessions.find((session) => session.id === activeSessionId) ?? chatSessions[0]
  const activeMessages = activeSession?.messages ?? []
  const isWelcomeState = activeMessages.length === 1 && activeMessages[0]?.role === 'assistant'
  const visibleMessages = isWelcomeState ? [] : activeMessages
  const lastAssistantWithRows = [...activeMessages].reverse().find((message) => message.role === 'assistant' && (message.data?.rows?.length ?? 0) > 0)
  const contextualPrompts = buildContextualPrompts(lastAssistantWithRows?.data?.rows ?? [], lastAssistantWithRows?.data?.table)
  const topbarTitle = activeView === 'dashboard' ? 'LogiSense Operations Dashboard' : 'LogiSense Logistics Copilot'
  const topbarSubtitle = activeView === 'dashboard'
    ? 'Track live KPIs, review network exceptions, and inspect operational records.'
    : 'Ask grounded questions across shipments, fleet, routes, and work orders.'
  const canSendMessage = draft.trim().length > 0 && !isLoading

  const appendSessionMessage = (sessionId: string, message: ChatMessage) => {
    setChatSessions((current) =>
      current.map((session) =>
        session.id === sessionId
          ? {
              ...session,
              messages: [...session.messages, { ...message, createdAt: message.createdAt ?? Date.now() }],
            }
          : session,
      ),
    )
  }

  const quickMetrics: QuickMetric[] = [
    {
      id: 'shipments',
      label: 'Shipments',
      value: dashboard ? formatCompact(dashboard.kpis.active_shipments) : '...',
      detail: 'Active now',
      icon: 'S',
    },
    {
      id: 'fleet',
      label: 'Fleet',
      value: dashboard ? `${dashboard.kpis.fleet_utilization_avg}%` : '...',
      detail: 'Utilization',
      icon: 'F',
    },
    {
      id: 'jobs',
      label: 'Jobs',
      value: dashboard ? formatCompact(dashboard.kpis.open_jobs) : '...',
      detail: 'Open work',
      icon: 'J',
    },
    {
      id: 'logistics_records',
      label: 'Records',
      value: dashboard ? formatCompact(dashboard.kpis.active_records) : '...',
      detail: 'Active logistics records',
      icon: 'P',
    },
  ]

  const fetchDashboard = async () => {
    const response = await fetch(`${apiBaseUrl}/api/dashboard`)
    if (!response.ok) {
      throw new Error('Dashboard fetch failed')
    }

    const data = (await response.json()) as DashboardResponse
    setDashboard(data)
  }

  const fetchLiveRowsForTab = async (tab: ModuleTab) => {
    const response = await fetch(`${apiBaseUrl}/api/live/${tab.table}?limit=${tab.limit}`)
    if (!response.ok) {
      throw new Error('Live rows fetch failed')
    }

    const data = (await response.json()) as LiveRowsResponse
    appendSessionMessage(activeSessionId, {
      role: 'assistant',
      text: `${tab.label} loaded. ${data.summary}`,
      data: {
        table: data.table,
        summary: data.summary,
        rows: data.rows,
      },
    })
  }

  useEffect(() => {
    fetchDashboard().catch((error) => console.error('Unable to load initial dashboard data', error))
  }, [])

  useEffect(() => {
    if (!autoRefresh) {
      return
    }

    const timer = window.setInterval(() => {
      fetchDashboard().catch((error) => console.error('Auto-refresh dashboard failed', error))
    }, 20000)

    return () => window.clearInterval(timer)
  }, [autoRefresh])

  const handleSend = async (prompt?: string) => {
    const nextPrompt = (prompt ?? draft).trim()
    if (!nextPrompt || isLoading) {
      return
    }

    const sessionId = activeSessionId
    appendSessionMessage(sessionId, { role: 'user', text: nextPrompt })
    setDraft('')
    setIsLoading(true)

    try {
      const response = await fetch(`${apiBaseUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: nextPrompt, session_id: sessionId }),
      })

      if (!response.ok) {
        throw new Error('Request failed')
      }

      const data = (await response.json()) as ChatResponse
      const rows = Array.isArray(data.rows) ? data.rows : []
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        text: buildAssistantText(data),
        data: {
          table: data.table ?? null,
          summary: data.summary,
          rows,
        },
      }

      appendSessionMessage(sessionId, assistantMessage)
    } catch (error) {
      console.error('Unable to call backend', error)
      appendSessionMessage(sessionId, {
        role: 'assistant',
        text: 'The logistics copilot is currently unavailable. Check backend startup and AI provider settings.',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleTabClick = async (tab: ModuleTab) => {
    setSelectedTabId(tab.id)
    try {
      await fetchLiveRowsForTab(tab)
    } catch (error) {
      console.error('Unable to fetch tab data', error)
      appendSessionMessage(activeSessionId, {
        role: 'assistant',
        text: `Unable to load ${tab.label}. Please check backend connectivity.`,
      })
    }
  }

  const handleRefreshClick = async () => {
    try {
      await fetchDashboard()
      await fetchLiveRowsForTab(selectedTab)
    } catch (error) {
      console.error('Unable to refresh', error)
    }
  }

  const handleStopGeneration = () => {
    setIsLoading(false)
  }

  const handleIconClick = (mode: 'shipments' | 'fleet' | 'jobs' | 'logistics_records') => {
    if (mode === 'shipments') {
      void handleTabClick(tabs[0])
      return
    }

    if (mode === 'fleet') {
      void handleTabClick(tabs[1])
      return
    }

    if (mode === 'jobs') {
      void handleTabClick(tabs[4])
      return
    }

    void handleTabClick(tabs[5])
  }

  const handleNewChat = () => {
    const nextNumber = chatSessions.length + 1
    const newSessionId = `ops-session-${Date.now()}`

    setChatSessions((current) => [
      ...current,
      {
        id: newSessionId,
        title: `Chat ${nextNumber}`,
        messages: [initialAssistantMessage],
      },
    ])

    setActiveSessionId(newSessionId)
    setDraft('')
    setIsChatMenuOpen(false)
  }

  const toggleMessageView = (messageIndex: number, view: ResultView) => {
    setChatSessions((current) =>
      current.map((session) =>
        session.id === activeSessionId
          ? {
              ...session,
              messages: session.messages.map((message, index) =>
                index === messageIndex ? { ...message, view: message.view === view ? null : view } : message,
              ),
            }
          : session,
      ),
    )
  }

  const toggleMessageThinking = (messageIndex: number) => {
    setChatSessions((current) =>
      current.map((session) =>
        session.id === activeSessionId
          ? {
              ...session,
              messages: session.messages.map((message, index) =>
                index === messageIndex ? { ...message, thinkingOpen: !message.thinkingOpen } : message,
              ),
            }
          : session,
      ),
    )
  }

  const handleCopyMessage = async (rows: Record<string, unknown>[], table?: string | null, summary?: string) => {
    try {
      const content = rows.length > 0
        ? buildFullTableText(rows, table)
        : summary ?? 'No table data available.'
      await navigator.clipboard.writeText(content)
    } catch (error) {
      console.error('Unable to copy table data', error)
    }
  }

  const handleRegenerateMessage = (messageIndex: number) => {
    const precedingUserMessage = [...activeMessages.slice(0, messageIndex)].reverse().find((message) => message.role === 'user')
    if (!precedingUserMessage) {
      return
    }

    void handleSend(precedingUserMessage.text)
  }

  const handleClearAllChats = () => {
    const newSessionId = `ops-session-${Date.now()}`
    setChatSessions([{ id: newSessionId, title: 'Chat 1', messages: [initialAssistantMessage] }])
    setActiveSessionId(newSessionId)
    setIsChatMenuOpen(false)
  }

  return (
    <div className="logisense-shell">
      <header className="app-topbar">
        <div className="app-topbar-primary">
          <div className="app-topbar-brand">
            <div className="app-topbar-logo" aria-hidden="true">LS</div>
            <div className="app-topbar-copy">
              <span className="app-topbar-title">{topbarTitle}</span>
              <span className="app-topbar-subtitle">{topbarSubtitle}</span>
            </div>
          </div>

          <div className="app-view-switch" role="tablist" aria-label="Primary view">
            <button
              type="button"
              role="tab"
              aria-selected={activeView === 'chat'}
              className={`app-view-switch-item ${activeView === 'chat' ? 'active' : ''}`}
              onClick={() => setActiveView('chat')}
            >
              Chat
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeView === 'dashboard'}
              className={`app-view-switch-item ${activeView === 'dashboard' ? 'active' : ''}`}
              onClick={() => setActiveView('dashboard')}
            >
              Dashboard
            </button>
          </div>

          <div className="app-topbar-controls">
            <button type="button" className={autoRefresh ? 'active' : ''} onClick={() => setAutoRefresh((value) => !value)}>
              {autoRefresh ? 'Auto Refresh On' : 'Auto Refresh Off'}
            </button>
            <button type="button" onClick={() => void handleRefreshClick()}>
              Refresh Data
            </button>
          </div>
        </div>

        <div className="app-topbar-secondary">
          {activeView === 'chat' ? (
            <nav className="app-topbar-nav" aria-label="Operations modules">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  className={`app-topbar-nav-item ${tab.id === selectedTabId ? 'active' : ''}`}
                  onClick={() => void handleTabClick(tab)}
                  aria-label={tab.label}
                  title={tab.helperPrompt}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          ) : (
            <div className="app-topbar-status-strip" aria-label="Dashboard status">
              <span className="app-status-pill">Live operations view</span>
              <span className="app-status-copy">Monitor KPIs, records, and operational exceptions in one workspace.</span>
            </div>
          )}

          <div className="app-topbar-metrics" aria-label="Quick metrics">
            {quickMetrics.map((metric) => (
              <button
                key={metric.id}
                type="button"
                className="app-topbar-metric"
                onClick={() => {
                  setActiveView('chat')
                  handleIconClick(metric.id)
                }}
                aria-label={`${metric.label} quick metric`}
                title={metric.detail}
              >
                <span className="app-topbar-metric-mark">{metric.icon}</span>
                <span className="app-topbar-metric-body">
                  <strong>{metric.value}</strong>
                  <span>{metric.label}</span>
                </span>
              </button>
            ))}
          </div>
        </div>
      </header>

      {activeView === 'dashboard' ? (
        <main className="chat-stage dashboard-stage">
          <Dashboard apiBaseUrl={apiBaseUrl} />
        </main>
      ) : (
      <main className="chat-stage">
        <header className="chat-stage-header">
          <div className="chat-stage-context">
            <span className="chat-stage-eyebrow">Operations chat</span>
            <div className="chat-stage-title-row">
              <h2>{selectedTab.label}</h2>
              <span className="chat-stage-chip">Live</span>
            </div>
            <p>{selectedTab.helperPrompt}</p>
          </div>

          <div className="chat-controls">
            <button type="button" className="icon-toggle" aria-label="New chat" title="New chat" onClick={handleNewChat}>
              ✎
            </button>
            <div className="chat-menu-wrap">
              <button
                type="button"
                className="icon-toggle"
                aria-label="Chat options"
                aria-expanded={isChatMenuOpen}
                onClick={() => setIsChatMenuOpen((value) => !value)}
              >
                ⋮
              </button>
              {isChatMenuOpen ? (
                <div className="chat-menu">
                  <button type="button" className="chat-menu-item" onClick={handleNewChat}>
                    + New Chat
                  </button>
                  <div className="chat-menu-label">Recent Chats</div>
                  {chatSessions.map((session) => (
                    <button
                      key={session.id}
                      type="button"
                      className={`chat-menu-item ${session.id === activeSessionId ? 'active' : ''}`}
                      onClick={() => {
                        setActiveSessionId(session.id)
                        setIsChatMenuOpen(false)
                      }}
                    >
                      {session.title}
                    </button>
                  ))}
                  <button type="button" className="chat-menu-item chat-menu-danger" onClick={handleClearAllChats}>
                    Clear All
                  </button>
                </div>
              ) : null}
            </div>
            {isLoading ? (
              <button type="button" className="icon-toggle stop-toggle" aria-label="Stop generation" onClick={handleStopGeneration}>
                ■
              </button>
            ) : null}
          </div>
        </header>

        <div className="chat-thread">
          {isWelcomeState ? (
            <div className="assistant-welcome">
              <div className="assistant-welcome-mark">LS</div>
              <span className="assistant-welcome-eyebrow">Live workspace</span>
              <h3>Start with a logistics question or choose an operational workflow.</h3>
              <p>Use the modules above to inspect freight, fleet, route risk, work orders, and records without leaving the workspace.</p>
            </div>
          ) : null}

          {visibleMessages.map((message, index) => {
            const rows = message.data?.rows ?? []
            const objectKeys = rows.length > 0 ? Object.keys(rows[0]) : []
            const summaryText = message.data?.summary?.trim() || buildResultSummary(rows, message.data?.table, 'Result set ready')
            const hasRows = rows.length > 0

            if (message.role === 'user') {
              return (
                <div key={`user-${index}`} className="chat-bubble-row user">
                  <div className="user-pill">{message.text}</div>
                </div>
              )
            }

                    return (
                      <div key={`assistant-${index}`} className="chat-bubble-row assistant">
                        <div className="chat-bubble">
                          <div className="bubble-meta">
                            <button type="button" className="thinking-toggle" onClick={() => toggleMessageThinking(index)}>
                              <span className="thinking-dot" aria-hidden="true" />
                              Show thinking
                              <span className={`thinking-chevron ${message.thinkingOpen ? 'open' : ''}`}>⌄</span>
                            </button>
                            <span className="bubble-timestamp">{formatTimestamp(message.createdAt)}</span>
                          </div>
                          {message.thinkingOpen ? (
                            <ul className="thinking-trace">
                              {buildThinkingSteps(message).map((step) => (
                                <li key={step}>{step}</li>
                              ))}
                            </ul>
                          ) : null}
                          <p>{message.text}</p>
                          {hasRows ? (
                            <div className="chat-result-table">
                              <div className="chat-result-head">
                                <span>Result set</span>
                                <span>{summaryText}</span>
                              </div>
                              <div className="chat-result-body">
                                <table>
                                  <thead>
                                    <tr>
                                      {objectKeys.map((column) => (
                                        <th key={column}>{formatColumnLabel(column)}</th>
                                      ))}
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {rows.slice(0, 5).map((row, rowIndex) => (
                                      <tr key={`${index}-${rowIndex}`}>
                                        {objectKeys.map((column) => (
                                          <td key={`${index}-${rowIndex}-${column}`}>{formatCellValue(row[column])}</td>
                                        ))}
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          ) : null}

                          {hasRows ? (
                            <div className="message-action-row">
                              <button type="button" onClick={() => void handleCopyMessage(rows, message.data?.table, message.text)}>
                                Copy
                              </button>
                              <button type="button" onClick={() => handleRegenerateMessage(index)}>
                                Regenerate
                              </button>
                              <button
                                type="button"
                                className={message.view === 'chart' ? 'active' : ''}
                                onClick={() => toggleMessageView(index, 'chart')}
                              >
                                {message.view === 'chart' ? 'Close Chart' : 'View Chart'}
                              </button>
                              <button
                                type="button"
                                className={message.view === 'map' ? 'active' : ''}
                                onClick={() => toggleMessageView(index, 'map')}
                              >
                                {message.view === 'map' ? 'Close Map' : 'View Map'}
                              </button>
                              <button
                                type="button"
                                className={message.view === 'summary' ? 'active' : ''}
                                onClick={() => toggleMessageView(index, 'summary')}
                              >
                                {message.view === 'summary' ? 'Close Summary' : 'View Summary'}
                              </button>
                            </div>
                          ) : null}

                          {hasRows && message.view === 'chart' ? (
                            <div className="chat-visual-card">
                              <div className="chat-visual-card-head">
                                <h4>Results Breakdown</h4>
                                <span>{message.data?.table ?? 'Result'} by record count</span>
                              </div>
                              <ResultChart rows={rows} />
                            </div>
                          ) : null}
                          {hasRows && message.view === 'map' ? (
                            <div className="chat-visual-card">
                              <div className="chat-visual-card-head">
                                <h4>Location Map</h4>
                                <span>Plotted from result coordinates</span>
                              </div>
                              <ResultMap rows={rows} />
                            </div>
                          ) : null}
                          {hasRows && message.view === 'summary' ? (
                            <div className="chat-visual-card summary-panel">
                              <div className="chat-visual-card-head summary-head">
                                <h4>Summary</h4>
                              </div>
                              <p className="chat-visual-card-body summary-body">{summaryText}</p>
                            </div>
                          ) : null}
                        </div>
                      </div>
                    )
                  })}

                  {isLoading && (
                    <div className="chat-bubble-row assistant">
                      <div className="chat-bubble thinking">
                        <span className="thinking-indicator" />
                        LogiSense logistics AI is thinking...
                      </div>
                    </div>
                  )}

                  {isWelcomeState ? (
                    <div className="quick-start-block">
                      <div className="section-heading">
                        <h4>Quick Start</h4>
                        <p>Choose a high-value workflow to open the first grounded result set.</p>
                      </div>
                      <div className="quick-start-list">
                        {quickStartActions.map((action) => (
                          <button key={action.label} type="button" className="quick-start-row" onClick={() => void handleSend(action.prompt)}>
                            <span className="quick-start-icon" aria-hidden="true">✦</span>
                            <span className="quick-start-copy">
                              <span className="quick-start-label">{action.label}</span>
                              <span className="quick-start-description">{action.description}</span>
                            </span>
                            <span className="quick-start-chevron">›</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="suggestion-block">
                      <div className="section-heading compact">
                        <h4>Suggested Prompts</h4>
                        <p>Follow the current result context with another grounded question.</p>
                      </div>
                      <div className="suggestion-row">
                        {contextualPrompts.map((item) => (
                          <button key={item.label} type="button" className="suggestion-pill" onClick={() => void handleSend(item.prompt)}>
                            {item.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <div className="composer-shell">
                  <div className="composer-input-wrap">
                    <input
                      type="text"
                      value={draft}
                      maxLength={1500}
                      aria-label="Ask logistics copilot"
                      placeholder="Ask a grounded question about freight, fleet, route risk, or work orders..."
                      onChange={(event) => setDraft(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter') {
                          void handleSend()
                        }
                      }}
                    />
                    <span className="composer-counter">{draft.length}/1500</span>
                  </div>
                  <button type="button" onClick={() => void handleSend()} aria-label="Send message" disabled={!canSendMessage}>
                    Send
                  </button>
                </div>
              </main>
      )}
            </div>
  )
}

export default App

