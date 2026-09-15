import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { ResultChart, ResultMap } from './components/ResultVisuals'

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
  active_opportunities: number
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
  table: 'shipments' | 'vehicles' | 'jobs' | 'opportunities'
  limit: number
  helperPrompt: string
}

type QuickMetric = {
  id: 'shipments' | 'fleet' | 'jobs' | 'opportunities'
  label: string
  value: string
  detail: string
  icon: string
}

type PromptAction = {
  label: string
  prompt: string
}

const tabs: ModuleTab[] = [
  { id: 'freight', label: 'Active Freight & Hubs', table: 'shipments', limit: 50, helperPrompt: 'Show latest freight and hub records.' },
  { id: 'fleet', label: 'Fleet Telemetry', table: 'vehicles', limit: 50, helperPrompt: 'Show current fleet utilization and maintenance data.' },
  { id: 'routes', label: 'Route Optimization', table: 'shipments', limit: 50, helperPrompt: 'Show route-level shipment data for planning.' },
  { id: 'incidents', label: 'Incident Exceptions', table: 'shipments', limit: 50, helperPrompt: 'Show delayed and exception shipment records.' },
  { id: 'analytics', label: 'Analytics & KPIs', table: 'jobs', limit: 50, helperPrompt: 'Show open jobs and KPI-supporting records.' },
  { id: 'config', label: 'System Config', table: 'opportunities', limit: 50, helperPrompt: 'Show client and opportunity configuration context.' },
]

const quickStartActions: PromptAction[] = [
  { label: 'Show opportunities with valuation dates in 2025', prompt: 'Show opportunities with valuation dates in 2025' },
  { label: 'Show delayed shipments by delivery date', prompt: 'Show delayed shipments by delivery date' },
  { label: 'Show open jobs sorted by days open', prompt: 'Show open jobs sorted by days open' },
]

const suggestedPrompts: PromptAction[] = [
  { label: 'Show delayed shipments for Birmingham routes', prompt: 'Show delayed shipments for Birmingham routes' },
  { label: 'Which routes have the highest delivery risk?', prompt: 'Which routes have the highest delivery risk?' },
  { label: 'List fleet vehicles in maintenance status', prompt: 'List fleet vehicles in maintenance status' },
  { label: 'Show open jobs with highest days open', prompt: 'Show open jobs with highest days open' },
]

const formatCompact = (value: number): string =>
  new Intl.NumberFormat('en-GB', { notation: 'compact', maximumFractionDigits: 1 }).format(value)

const formatCellValue = (value: unknown): string => {
  if (value === null || value === undefined) {
    return '—'
  }

  if (typeof value === 'number') {
    return new Intl.NumberFormat('en-GB').format(value)
  }

  return String(value)
}

const buildAssistantText = (data: ChatResponse): string => {
  const fallback = 'No response from the assistant.'
  const rawText = (data.answer ?? fallback).trim()
  const rowCount = Array.isArray(data.rows) ? data.rows.length : 0

  if (rowCount === 0) {
    return rawText
  }

  const markerIndex = rawText.toLowerCase().indexOf('example rows:')
  if (markerIndex >= 0) {
    return rawText.slice(0, markerIndex).trim()
  }

  return rawText
}

const buildPreviewSummary = (rows: Record<string, unknown>[], fallback: string): string => {
  if (rows.length === 0) {
    return fallback
  }

  const firstRow = rows[0]
  const candidateKeys = ['client_name', 'customer', 'route', 'status', 'delivery_date', 'valuation_date']
  const preview = candidateKeys
    .map((key) => firstRow[key])
    .filter((value): value is string | number => typeof value === 'string' || typeof value === 'number')
    .map((value) => String(value))

  return preview.length > 0 ? preview.slice(0, 3).join(' • ') : fallback
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

// Grounded, honest trace of what the agent pipeline actually did — never invented reasoning.
const buildThinkingSteps = (message: ChatMessage): string[] => {
  const table = message.data?.table
  const rowCount = message.data?.rows?.length ?? 0
  const steps = ['Router agent reviewed the question and matched it to the approved logistics data model.']

  if (table) {
    steps.push(`SQL agent executed a validated, read-only query against the "${table}" table and retrieved ${rowCount} record${rowCount === 1 ? '' : 's'}.`)
    steps.push('Summary agent grounded the response strictly in the retrieved rows before phrasing the final answer.')
  } else {
    steps.push('SQL agent found no approved table matching this question, so no data was queried.')
  }

  return steps
}

const NAME_LIKE_KEYS = ['customer', 'client_name', 'destination', 'route', 'region', 'depot']

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
  text: 'Live operations online. Click any module tab or quick prompt to fetch real data from the logistics database.',
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
  const [tableRows, setTableRows] = useState<Record<string, unknown>[]>([])
  const [tableSource, setTableSource] = useState<{ table: string; summary: string } | null>(null)
  const [selectedTabId, setSelectedTabId] = useState<string>(tabs[0].id)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [isChatMaximized, setIsChatMaximized] = useState(false)
  const [isChatOpen, setIsChatOpen] = useState(true)
  const [isChatMenuOpen, setIsChatMenuOpen] = useState(false)

  const selectedTab = tabs.find((item) => item.id === selectedTabId) ?? tabs[0]
  const activeSession = chatSessions.find((session) => session.id === activeSessionId) ?? chatSessions[0]
  const activeMessages = activeSession?.messages ?? []
  const isWelcomeState = activeMessages.length === 1 && activeMessages[0]?.role === 'assistant'
  const visibleMessages = isWelcomeState ? [] : activeMessages
  const lastAssistantWithRows = [...activeMessages].reverse().find((message) => message.role === 'assistant' && (message.data?.rows?.length ?? 0) > 0)
  const contextualPrompts = buildContextualPrompts(lastAssistantWithRows?.data?.rows ?? [], lastAssistantWithRows?.data?.table)

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
      id: 'opportunities',
      label: 'Opps',
      value: dashboard ? formatCompact(dashboard.kpis.active_opportunities) : '...',
      detail: 'Active pipeline',
      icon: 'O',
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

  const fetchLiveRowsForTab = async (tab: ModuleTab, announceInChat: boolean) => {
    const response = await fetch(`${apiBaseUrl}/api/live/${tab.table}?limit=${tab.limit}`)
    if (!response.ok) {
      throw new Error('Live rows fetch failed')
    }

    const data = (await response.json()) as LiveRowsResponse
    setTableRows(data.rows)
    setTableSource({ table: data.table, summary: data.summary })

    if (announceInChat) {
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
  }

  useEffect(() => {
    const loadInitial = async () => {
      try {
        await fetchDashboard()
        await fetchLiveRowsForTab(selectedTab, false)
      } catch (error) {
        console.error('Unable to load initial data', error)
      }
    }

    void loadInitial()
  }, [])

  useEffect(() => {
    if (!autoRefresh) {
      return
    }

    const timer = window.setInterval(() => {
      fetchDashboard().catch((error) => console.error('Auto-refresh dashboard failed', error))
      fetchLiveRowsForTab(selectedTab, false).catch((error) => console.error('Auto-refresh table failed', error))
    }, 20000)

    return () => window.clearInterval(timer)
  }, [autoRefresh, selectedTab])

  const columns = useMemo(() => {
    if (tableRows.length === 0) {
      return []
    }

    return Object.keys(tableRows[0])
  }, [tableRows])

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
      setTableRows(rows)
      setTableSource(
        data.table
          ? {
              table: data.table,
              summary: data.summary ?? assistantMessage.text,
            }
          : null,
      )
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
      await fetchLiveRowsForTab(tab, true)
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
      await fetchLiveRowsForTab(selectedTab, true)
    } catch (error) {
      console.error('Unable to refresh', error)
    }
  }

  const handleStopGeneration = () => {
    setIsLoading(false)
  }

  const handleIconClick = (mode: 'shipments' | 'fleet' | 'jobs' | 'opportunities') => {
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
    setIsChatOpen(true)
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

  const handleCopyMessage = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
    } catch (error) {
      console.error('Unable to copy assistant response', error)
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
    <div className={`logisense-shell ${isChatMaximized ? 'assistant-maximized' : ''}`}>
      <div className="workspace-shell">
        <aside className="project-panel">
          <div className="project-panel-header">
            <div className="project-brand">LogiSense Copilot</div>
            <p>Enterprise logistics assistant</p>
          </div>

          <nav className="module-nav" aria-label="Operations modules">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                className={`module-nav-item ${tab.id === selectedTabId ? 'active' : ''}`}
                onClick={() => void handleTabClick(tab)}
                aria-label={tab.label}
                title={tab.helperPrompt}
              >
                {tab.label}
              </button>
            ))}
          </nav>

          <div className="quick-metrics" aria-label="Quick metrics">
            {quickMetrics.map((metric) => (
              <button
                key={metric.id}
                type="button"
                className="quick-metric"
                onClick={() => handleIconClick(metric.id)}
                aria-label={`${metric.label} quick metric`}
              >
                <span className="quick-metric-mark">{metric.icon}</span>
                <span className="quick-metric-body">
                  <strong>{metric.value}</strong>
                  <span>{metric.label}</span>
                  <small>{metric.detail}</small>
                </span>
              </button>
            ))}
          </div>
        </aside>

        <main className="ops-surface">
          <header className="ops-surface-header">
            <div>
              <h1>Logistics Operations Tracker</h1>
              <p>Live terminal, route, and fleet insights driven by validated SQLite logistics data.</p>
            </div>
            <div className="header-controls">
              <button type="button" onClick={() => setAutoRefresh((value) => !value)}>
                {autoRefresh ? 'Auto ON' : 'Auto OFF'}
              </button>
              <button type="button" onClick={() => void handleRefreshClick()}>
                Refresh
              </button>
            </div>
          </header>

          <section className="analytics-strip" aria-label="Operations KPIs">
            <article className="kpi-card">
              <span>Active Shipments</span>
              <strong>{dashboard ? formatCompact(dashboard.kpis.active_shipments) : '...'}</strong>
            </article>
            <article className="kpi-card">
              <span>Open Jobs</span>
              <strong>{dashboard ? formatCompact(dashboard.kpis.open_jobs) : '...'}</strong>
            </article>
            <article className="kpi-card">
              <span>Fleet Utilization</span>
              <strong>{dashboard ? `${dashboard.kpis.fleet_utilization_avg}%` : '...'}</strong>
            </article>
            <article className="kpi-card alert">
              <span>Delayed Shipments</span>
              <strong>{dashboard ? formatCompact(dashboard.kpis.delayed_shipments) : '...'}</strong>
            </article>
            <article className="kpi-card">
              <span>Active Opportunities</span>
              <strong>{dashboard ? formatCompact(dashboard.kpis.active_opportunities) : '...'}</strong>
            </article>
          </section>

          <section className="content-split">
            <section className="record-panel">
              <div className="panel-head">
                <h2>Route Risk Radar</h2>
                <span>Top delayed corridors</span>
              </div>

              <ul className="route-list">
                {(dashboard?.risk_routes ?? []).map((risk) => (
                  <li key={risk.route}>
                    <span>{risk.route}</span>
                    <strong>{risk.delayed_count}</strong>
                  </li>
                ))}
              </ul>

              <div className="table-panel">
                <div className="table-panel-head">
                  <h3>{selectedTab.label}</h3>
                  <span>{tableSource ? `Fetched from ${tableSource.table}` : 'Live data feed'} · {tableRows.length} rows</span>
                </div>
                {tableSource && <div className="table-panel-summary">{tableSource.summary}</div>}

                <div className="data-table-wrap">
                  <table>
                    <thead>
                      <tr>
                        {columns.map((column) => (
                          <th key={column}>{column.replaceAll('_', ' ')}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {tableRows.map((row, index) => (
                        <tr key={`row-${index}`}>
                          {columns.map((column) => (
                            <td key={`${index}-${column}`}>{String(row[column] ?? '')}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {tableRows.length === 0 && <div className="empty-data">No rows returned for the current query.</div>}
                </div>
              </div>
            </section>

            {isChatOpen ? (
              <aside className={`chat-panel ${isChatMaximized ? 'is-maximized' : ''}`}>
                <header className="chat-panel-header">
                  <div className="chat-brand-block">
                    <div className="chat-logo" aria-hidden="true">
                      <span>LS</span>
                    </div>
                    <div>
                      <h2>LogiSense AI</h2>
                      <p>Your intelligent assistant</p>
                    </div>
                  </div>

                  <div className="chat-controls">
                    <button type="button" className="icon-toggle" aria-label="New chat" title="New chat" onClick={handleNewChat}>
                      ✎
                    </button>
                    <button type="button" className="icon-toggle" aria-label="Maximize assistant" onClick={() => setIsChatMaximized((value) => !value)}>
                      {isChatMaximized ? '⤢' : '▢'}
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
                    <button type="button" className="icon-toggle close-toggle" aria-label="Close assistant" onClick={() => setIsChatOpen(false)}>
                      ×
                    </button>
                  </div>
                </header>

                <div className="chat-thread">
                  {isWelcomeState ? (
                    <div className="assistant-welcome">
                      <div className="assistant-welcome-mark">LS</div>
                      <h3>Welcome back, Dinesh! 👋</h3>
                      <p>I'm here to help you find insights, analyze data, and answer questions about your logistics operations.</p>
                    </div>
                  ) : null}

                  {visibleMessages.map((message, index) => {
                    const rows = message.data?.rows ?? []
                    const objectKeys = rows.length > 0 ? Object.keys(rows[0]) : []
                    const summaryText = message.data?.summary ?? buildPreviewSummary(rows, 'Result set ready')
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
                                        <th key={column}>{column.replaceAll('_', ' ')}</th>
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
                              <button type="button" onClick={() => void handleCopyMessage(message.text)}>
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
                            <div className="chat-visual-card">
                              <div className="chat-visual-card-head">
                                <h4>Summary</h4>
                              </div>
                              <p className="chat-visual-card-body">{summaryText}</p>
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
                        LogiSense AI is thinking...
                      </div>
                    </div>
                  )}

                  {isWelcomeState ? (
                    <div className="quick-start-block">
                      <h4>Quick Start</h4>
                      <div className="quick-start-list">
                        {quickStartActions.map((action) => (
                          <button key={action.label} type="button" className="quick-start-row" onClick={() => void handleSend(action.prompt)}>
                            <span className="quick-start-icon">💡</span>
                            <span className="quick-start-label">{action.label}</span>
                            <span className="quick-start-chevron">›</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="suggestion-block">
                      <h4>Suggested Prompts</h4>
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
                      placeholder="Ask me anything about your projects..."
                      onChange={(event) => setDraft(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter') {
                          void handleSend()
                        }
                      }}
                    />
                    <span className="composer-counter">{draft.length}/1500</span>
                  </div>
                  <button type="button" onClick={() => void handleSend()} aria-label="Send message">
                    ➤
                  </button>
                </div>
              </aside>
            ) : (
              <button
                type="button"
                className="chat-launcher"
                aria-label="Open LogiSense AI assistant"
                onClick={() => setIsChatOpen(true)}
                title="Open LogiSense AI"
              >
                <span className="chat-launcher-icon">LS</span>
              </button>
            )}
          </section>
        </main>
      </div>
    </div>
  )
}

export default App

