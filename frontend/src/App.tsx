import { useEffect, useMemo, useState } from 'react'
import './App.css'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

type ChatMessage = {
  role: 'user' | 'assistant'
  text: string
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

type ShipmentRow = {
  shipment_id: string
  customer: string
  origin: string
  destination: string
  status: string
  delivery_date: string
  weight_kg: number
  value_usd: number
}

type DashboardResponse = {
  kpis: DashboardKpis
  risk_routes: RouteRisk[]
  live_shipments: ShipmentRow[]
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

const tabs: ModuleTab[] = [
  { id: 'freight', label: 'Active Freight & Hubs', table: 'shipments', limit: 50, helperPrompt: 'Show latest freight and hub records.' },
  { id: 'fleet', label: 'Fleet Telemetry', table: 'vehicles', limit: 50, helperPrompt: 'Show current fleet utilization and maintenance data.' },
  { id: 'routes', label: 'Route Optimization', table: 'shipments', limit: 50, helperPrompt: 'Show route-level shipment data for planning.' },
  { id: 'incidents', label: 'Incident Exceptions', table: 'shipments', limit: 50, helperPrompt: 'Show delayed and exception shipment records.' },
  { id: 'analytics', label: 'Analytics & KPIs', table: 'jobs', limit: 50, helperPrompt: 'Show open jobs and KPI-supporting records.' },
  { id: 'config', label: 'System Config', table: 'opportunities', limit: 50, helperPrompt: 'Show client and opportunity configuration context.' },
]

const suggestions = [
  'Show delayed shipments for Birmingham routes',
  'Which routes have the highest delivery risk?',
  'List fleet vehicles in maintenance status',
  'Show open jobs with highest days open',
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

  const marker = 'example rows:'
  const markerIndex = rawText.toLowerCase().indexOf(marker)
  if (markerIndex >= 0) {
    return rawText.slice(0, markerIndex).trim()
  }

  return rawText
}

const initialAssistantMessage: ChatMessage = {
  role: 'assistant',
  text: 'Live operations online. Click any module tab or icon to fetch real data from the logistics database.',
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

  const selectedTab = tabs.find((item) => item.id === selectedTabId) ?? tabs[0]
  const activeSession = chatSessions.find((session) => session.id === activeSessionId) ?? chatSessions[0]
  const activeMessages = activeSession?.messages ?? []

  const appendSessionMessage = (sessionId: string, message: ChatMessage) => {
    setChatSessions((current) =>
      current.map((session) =>
        session.id === sessionId
          ? {
              ...session,
              messages: [...session.messages, message],
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

    loadInitial()
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
    const userMessage: ChatMessage = { role: 'user', text: nextPrompt }
    appendSessionMessage(sessionId, userMessage)
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
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        text: buildAssistantText(data),
        data: {
          table: data.table ?? null,
          summary: data.summary,
          rows: Array.isArray(data.rows) ? data.rows : [],
        },
      }
      appendSessionMessage(sessionId, assistantMessage)

      setTableRows(Array.isArray(data.rows) ? data.rows : [])
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

  const handleIconClick = (mode: 'shipments' | 'fleet' | 'jobs' | 'opportunities') => {
    setIsChatMaximized(true)
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
    setIsChatMaximized(true)
  }

  return (
    <div className={`ops-shell ${isChatMaximized ? 'chat-focus' : ''}`}>
      <aside className="ops-sidebar">
        <div className="ops-logo">LogiSense Copilot Platform</div>
        <nav className="ops-nav" aria-label="Operations modules">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={`ops-nav-item ${tab.id === selectedTabId ? 'active' : ''}`}
              onClick={() => handleTabClick(tab)}
              aria-label={tab.label}
              title={tab.helperPrompt}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        <div className="quick-icons" aria-label="Quick data icons">
          {quickMetrics.map((metric) => (
            <button
              key={metric.id}
              type="button"
              className="icon-button"
              onClick={() => handleIconClick(metric.id)}
              aria-label={`${metric.label} icon`}
            >
              <span className="icon-button-mark" aria-hidden="true">
                {metric.icon}
              </span>
              <span className="icon-button-body">
                <strong>{metric.value}</strong>
                <span>{metric.label}</span>
                <small>{metric.detail}</small>
              </span>
            </button>
          ))}
        </div>
      </aside>

      <main className="ops-main">
        <header className="ops-header">
          <div>
            <h1>Logistics Operations Tracker</h1>
            <p>Live terminal, route, and fleet insights driven by validated SQLite logistics data.</p>
          </div>
          <div className="header-actions">
            <button type="button" onClick={() => setAutoRefresh((value) => !value)}>
              {autoRefresh ? 'Auto ON' : 'Auto OFF'}
            </button>
            <button type="button" onClick={handleRefreshClick}>Refresh</button>
          </div>
        </header>

        {!isChatMaximized && (
          <section className="kpi-grid" aria-label="Operations KPIs">
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
            <article className="kpi-card warning">
              <span>Delayed Shipments</span>
              <strong>{dashboard ? formatCompact(dashboard.kpis.delayed_shipments) : '...'}</strong>
            </article>
            <article className="kpi-card">
              <span>Active Opportunities</span>
              <strong>{dashboard ? formatCompact(dashboard.kpis.active_opportunities) : '...'}</strong>
            </article>
          </section>
        )}

        <section className={`ops-layout ${isChatMaximized ? 'chat-maximized' : ''}`}>
          <section className="risk-panel">
            <div className="panel-head">
              <h2>Route Risk Radar</h2>
              <span>Top delayed corridors</span>
            </div>
            <ul>
              {(dashboard?.risk_routes ?? []).map((risk) => (
                <li key={risk.route}>
                  <span>{risk.route}</span>
                  <strong>{risk.delayed_count}</strong>
                </li>
              ))}
            </ul>

            <div className="data-grid-wrap">
              <div className="panel-head compact">
                <h2>{selectedTab.label}</h2>
                <span>
                  {tableSource ? `Fetched from ${tableSource.table}` : 'Live data feed'} · {tableRows.length} rows
                </span>
              </div>
              {tableSource && <div className="data-grid-summary">{tableSource.summary}</div>}
              <div className="data-grid">
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
                {tableRows.length === 0 && <div className="data-grid-empty">No rows returned for the current query.</div>}
              </div>
            </div>
          </section>

          <aside className="copilot-panel">
            <div className="copilot-head">
              <div className="copilot-title">
                <span className="copilot-bot-icon" aria-hidden="true">
                  AI
                </span>
                <div>
                  <h3>LogiSense Copilot</h3>
                  <p>Safe SQL Reasoning Agent</p>
                </div>
              </div>
              <div className="panel-actions">
                <label className="history-select" htmlFor="chat-history-select">
                  History
                  <select
                    id="chat-history-select"
                    value={activeSessionId}
                    onChange={(event) => setActiveSessionId(event.target.value)}
                    aria-label="Chat history"
                  >
                    {chatSessions.map((session) => (
                      <option key={session.id} value={session.id}>
                        {session.title}
                      </option>
                    ))}
                  </select>
                </label>
                <button type="button" className="panel-toggle secondary" onClick={handleNewChat} aria-label="Start new chat">
                  New Chat
                </button>
                <button
                  type="button"
                  className="panel-toggle"
                  onClick={() => setIsChatMaximized((value) => !value)}
                  aria-pressed={isChatMaximized}
                  aria-label={isChatMaximized ? 'Minimize chat panel' : 'Maximize chat panel'}
                >
                  {isChatMaximized ? 'Minimize' : 'Maximize'}
                </button>
              </div>
            </div>

            <div className="copilot-chat">
              {activeMessages.map((message, index) => (
                <div key={`${message.role}-${index}`} className={`message-row ${message.role}`}>
                  <div className="bubble">
                    <p className="message-text">{message.text}</p>
                    {(() => {
                      const rows = message.data?.rows ?? []
                      if (rows.length === 0) {
                        return null
                      }

                      const columns = Object.keys(rows[0])

                      return (
                        <div className="message-table-card">
                          <div className="message-table-head">
                            <span>{message.data?.table ? `${message.data.table} rows` : 'Query results'}</span>
                            <span>{message.data?.summary ?? `${rows.length} rows returned`}</span>
                          </div>
                          <div className="message-table-wrap">
                            <table>
                              <thead>
                                <tr>
                                  {columns.map((column) => (
                                    <th key={column}>{column.replaceAll('_', ' ')}</th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {rows.slice(0, 5).map((row, rowIndex) => (
                                  <tr key={`${index}-${rowIndex}`}>
                                    {columns.map((column) => (
                                      <td key={`${index}-${rowIndex}-${column}`}>{formatCellValue(row[column])}</td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )
                    })()}
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="message-row assistant">
                  <div className="bubble">Thinking...</div>
                </div>
              )}

              <div className="chip-row">
                {suggestions.map((item) => (
                  <button key={item} type="button" className="chip" onClick={() => handleSend(item)}>
                    {item}
                  </button>
                ))}
              </div>
            </div>

            <div className="composer">
              <input
                type="text"
                value={draft}
                aria-label="Ask logistics copilot"
                placeholder="Ask about shipments, fleet, hubs, or delay risk"
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    handleSend()
                  }
                }}
              />
              <button type="button" aria-label="Send message" onClick={() => handleSend()}>
                Send
              </button>
            </div>
          </aside>
        </section>
      </main>
    </div>
  )
}

export default App
