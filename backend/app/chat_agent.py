from __future__ import annotations

import re
from collections import defaultdict, deque
from typing import Any

try:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    from langgraph.graph import END, START, StateGraph
except ImportError:  # pragma: no cover - graceful path when dependencies are not installed
    AIMessage = None
    HumanMessage = None
    SystemMessage = None
    END = None
    START = None
    StateGraph = None

from app.config import settings
from app.sql_service import detect_table_from_message, execute_safe_query

conversation_store: dict[str, deque[str]] = defaultdict(lambda: deque(maxlen=8))
# Remembers the last table each session queried, so follow-up questions ("show more of those")
# stay grounded without the user having to restate the table every turn.
last_table_by_session: dict[str, str | None] = defaultdict(lambda: None)


def _sanitize_logistics_text(text: str) -> str:
    if not text:
        return text

    sanitized = text
    replacements = [
        (r'\bopportunities?\b', 'logistics records'),
        (r'\bportfolio\b', 'record set'),
        (r'\bpipeline\b', 'logistics flow'),
        (r'\bprojects?\b', 'logistics work'),
        (r'\bvaluation\b', 'review'),
        (r'\bproperty\b', 'site'),
    ]
    for pattern, replacement in replacements:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    return sanitized


def build_llm() -> Any | None:
    if not settings.is_groq_configured:
        return None

    try:
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=0.2,
        )
    except Exception:
        return None


def _history_to_messages(history: list[str]) -> list[Any]:
    """Turn the stored 'User: ...' / 'Assistant: ...' log into real chat messages for 2-way context."""
    messages: list[Any] = []
    for line in history[-6:]:
        if line.startswith('User: '):
            messages.append(HumanMessage(content=line[len('User: ') :]))
        elif line.startswith('Assistant: '):
            messages.append(AIMessage(content=line[len('Assistant: ') :]))
    return messages


def router_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Classify which approved table the question targets, falling back to the session's last table."""
    user_message = state['user_message']
    session_id = state.get('session_id', 'default-session')

    if not user_message:
        state['table_hint'] = None
        return state

    state['table_hint'] = detect_table_from_message(user_message) or last_table_by_session[session_id]
    return state


def sql_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Run the safe, schema-validated SQL lookup grounded on the router's table hint."""
    user_message = state['user_message']
    session_id = state.get('session_id', 'default-session')

    result = execute_safe_query(user_message, table_hint=state.get('table_hint'))
    table = result.get('table')
    rows = result.get('rows', [])
    summary = result.get('summary', 'No data available.')

    if table:
        last_table_by_session[session_id] = table

    state['table'] = table
    state['rows'] = rows
    state['summary'] = _sanitize_logistics_text(summary)

    if table is None:
        state['grounded_answer'] = state['summary']
        return state

    preview = rows[:3]
    state['grounded_answer'] = _sanitize_logistics_text(
        f'{state["summary"]} The query targeted the approved logistics records model. '
        f'Example rows: {preview if preview else "no matching records"}.'
    )
    return state


def _build_short_summary(rows: list[dict[str, Any]], table: str | None) -> str:
    if not rows:
        return 'No matching logistics records were found for this query.'

    if table == 'shipments':
        delayed = sum(1 for row in rows if str(row.get('status', '')).lower() == 'delayed')
        route_counts: dict[str, int] = {}
        for row in rows:
            route = str(row.get('route') or row.get('destination') or 'Unknown route')
            route_counts[route] = route_counts.get(route, 0) + 1
        top_route = max(route_counts.items(), key=lambda item: item[1])[0] if route_counts else 'the selected routes'
        if delayed:
            return f'{len(rows)} shipments are in view, with {delayed} delayed. The biggest concentration is on {top_route}.'
        return f'{len(rows)} shipments are in view; most are tracking normally across {top_route}.'

    if table == 'vehicles':
        maintenance = sum(1 for row in rows if str(row.get('status', '')).lower() == 'maintenance')
        if maintenance:
            return f'{len(rows)} vehicles are in view, and {maintenance} are currently in maintenance or service attention.'
        return f'{len(rows)} vehicles are in view; the fleet is broadly healthy with no major maintenance spikes.'

    if table == 'jobs':
        open_jobs = sum(1 for row in rows if str(row.get('status', '')).lower() != 'completed')
        longest_wait = max((row.get('days_open', 0) for row in rows if isinstance(row.get('days_open', 0), (int, float))), default=0)
        return f'{len(rows)} work orders are visible, with {open_jobs} still active and the longest open item waiting {longest_wait} days.'

    top_region = max(
        ((row.get('region'), 1) for row in rows if row.get('region')),
        key=lambda item: item[1],
        default=('the selected region', 0),
    )[0]
    return f'{len(rows)} logistics records are in view, with the strongest activity centered on {top_region}.'


def summary_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Phrase the final answer with the LLM, strictly grounded on the SQL agent's output."""
    state['final_response'] = state['grounded_answer']
    state['short_summary'] = _build_short_summary(state.get('rows', []), state.get('table'))

    llm = build_llm()
    if llm is None or not state.get('rows'):
        return state

    messages: list[Any] = [
        SystemMessage(
            content=(
                'You are LogiSense, a senior logistics AI assistant. Rewrite the grounded data summary '
                'below into a concise, professional answer for the user, using the conversation history '
                'for context on follow-up questions. Use only the facts provided; never invent data or '
                'numbers that are not present in the summary or sample rows. The matching records are '
                'already rendered to the user as a data table in the UI, so respond in plain prose '
                'sentences only: do not use markdown tables, pipe characters, bullet lists, or bold/italic '
                'asterisks, and do not restate the raw rows. Write a useful logistics recap in 3-5 clear '
                'sentences that explains what is happening, what is delayed, and what should be prioritized next.'
            )
        ),
        *_history_to_messages(state.get('history', [])),
        HumanMessage(
            content=(
                f'User question: {state["user_message"]}\n'
                f'Grounded summary: {state["summary"]}\n'
                f'Sample rows: {state["rows"][:3]}'
            )
        ),
    ]

    try:
        result = llm.invoke(messages)
        content = str(getattr(result, 'content', result)).strip()
        if content:
            cleaned_content = _sanitize_logistics_text(content)
            state['final_response'] = cleaned_content
            state['short_summary'] = cleaned_content
    except Exception:
        # Keep the safe, data-grounded answer already set above.
        pass

    return state


def _build_state_graph() -> Any:
    if StateGraph is None:
        raise RuntimeError('langgraph is not installed')

    graph = StateGraph(dict)
    graph.add_node('router_agent', router_agent)
    graph.add_node('sql_agent', sql_agent)
    graph.add_node('summary_agent', summary_agent)
    graph.add_edge(START, 'router_agent')
    graph.add_edge('router_agent', 'sql_agent')
    graph.add_edge('sql_agent', 'summary_agent')
    graph.add_edge('summary_agent', END)
    return graph


try:
    agent_graph = _build_state_graph().compile()
except Exception:  # pragma: no cover - graceful fallback when dependencies are unavailable
    agent_graph = None


def process_chat_turn(session_id: str, user_message: str) -> dict[str, Any]:
    session_id = session_id or 'default-session'
    history = list(conversation_store.get(session_id, []))
    trimmed_message = user_message.strip()

    if not trimmed_message:
        return {
            'answer': 'Please provide a question to analyze.',
            'table': None,
            'rows': [],
            'summary': 'No input provided.',
            'session_id': session_id,
            'provider': settings.active_ai_provider,
            'context': history,
        }

    state: dict[str, Any] = {
        'user_message': trimmed_message,
        'history': history,
        'session_id': session_id,
    }

    if agent_graph is None:
        state = router_agent(state)
        state = sql_agent(state)
        state = summary_agent(state)
    else:
        state = agent_graph.invoke(state)

    answer = _sanitize_logistics_text(state.get('final_response', 'No response generated.'))
    rows = state.get('rows', [])
    summary = _sanitize_logistics_text(state.get('summary', 'No SQL query executed.'))
    table = state.get('table')

    conversation_store[session_id].append(f'User: {trimmed_message}')
    conversation_store[session_id].append(f'Assistant: {answer}')

    short_summary = state.get('short_summary') or summary or 'No summary available.'

    return {
        'answer': answer,
        'table': table,
        'rows': rows,
        'summary': short_summary,
        'session_id': session_id,
        'provider': settings.active_ai_provider,
        'context': list(conversation_store[session_id])[-6:],
    }

