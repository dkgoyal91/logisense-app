from __future__ import annotations

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
    state['summary'] = summary

    if table is None:
        state['grounded_answer'] = summary
        return state

    preview = rows[:3]
    state['grounded_answer'] = (
        f'{summary} The query targeted the {table} table. '
        f'Example rows: {preview if preview else "no matching records"}.'
    )
    return state


def summary_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Phrase the final answer with the LLM, strictly grounded on the SQL agent's output."""
    state['final_response'] = state['grounded_answer']

    llm = build_llm()
    if llm is None or not state.get('rows'):
        return state

    messages: list[Any] = [
        SystemMessage(
            content=(
                'You are LogiSense, a senior logistics AI assistant. Rewrite the grounded data summary '
                'below into a concise, professional answer for the user, using the conversation history '
                'for context on follow-up questions. Use only the facts provided; never invent data or '
                'numbers that are not present in the summary or sample rows.'
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
        state['final_response'] = str(getattr(result, 'content', result))
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

    answer = state.get('final_response', 'No response generated.')
    rows = state.get('rows', [])
    summary = state.get('summary', 'No SQL query executed.')
    table = state.get('table')

    conversation_store[session_id].append(f'User: {trimmed_message}')
    conversation_store[session_id].append(f'Assistant: {answer}')

    return {
        'answer': answer,
        'table': table,
        'rows': rows,
        'summary': summary,
        'session_id': session_id,
        'provider': settings.active_ai_provider,
        'context': list(conversation_store[session_id])[-6:],
    }

