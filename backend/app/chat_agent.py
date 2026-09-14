from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

try:
    from langchain_core.messages import HumanMessage, SystemMessage
    from langgraph.graph import END, START, StateGraph
except ImportError:  # pragma: no cover - fallback path when dependencies are not installed
    HumanMessage = None
    SystemMessage = None
    END = None
    START = None
    StateGraph = None

from app.config import settings
from app.sql_service import execute_safe_query

conversation_store: dict[str, deque[str]] = defaultdict(lambda: deque(maxlen=8))


def build_llm() -> Any | None:
    if settings.is_groq_configured:
        try:
            from langchain_groq import ChatGroq

            return ChatGroq(
                model=settings.groq_model,
                api_key=settings.groq_api_key,
                temperature=0.2,
            )
        except Exception:
            return None

    if settings.is_gemini_configured:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                api_key=settings.gemini_api_key,
                temperature=0.2,
            )
        except Exception:
            return None

    return None


def _fallback_answer(user_message: str, history: list[str]) -> str:
    context_text = ' '.join(history[-2:]) if history else 'No prior context.'
    return (
        'I am in a configured fallback mode. Based on the current conversation context, '
        f'you asked: "{user_message}". Recent context: {context_text}. '
        'Connect a valid Groq or Gemini API key in the environment to enable live model reasoning.'
    )


def _query_answer(user_message: str, history: list[str]) -> dict[str, Any]:
    result = execute_safe_query(user_message)
    if result.get('table') is None:
        return {
            'answer': _fallback_answer(user_message, history),
            'table': None,
            'rows': [],
            'summary': result.get('summary', 'No data available.'),
        }

    rows = result.get('rows', [])
    preview = rows[:3]
    summary = result.get('summary', f'Fetched {len(rows)} rows.')
    answer = (
        f'{summary} The query targeted the {result["table"]} table. '
        f'Example rows: {preview if preview else "no matching records"}.'
    )
    return {
        'answer': answer,
        'table': result['table'],
        'rows': rows,
        'summary': summary,
    }


def _build_state_graph() -> Any:
    if StateGraph is None:
        raise RuntimeError('langgraph is not installed')

    graph = StateGraph(dict)

    def intent_router(state: dict[str, Any]) -> dict[str, Any]:
        user_message = state['user_message']
        if not user_message:
            state['final_response'] = 'Please provide a valid question.'
            return state

        state['intent'] = 'logistics-insight'
        state['final_response'] = user_message
        return state

    def response_builder(state: dict[str, Any]) -> dict[str, Any]:
        llm = build_llm()
        user_message = state['user_message']
        recent_history = state.get('history', [])

        if llm is None:
            sql_result = _query_answer(user_message, recent_history)
            state['final_response'] = sql_result['answer']
            state['rows'] = sql_result['rows']
            state['summary'] = sql_result['summary']
            state['table'] = sql_result['table']
            return state

        messages = [
            SystemMessage(
                content=(
                    'You are LogiSense, a senior logistics AI assistant. Use the conversation context '
                    'to provide precise enterprise-grade insights. Be concise but helpful. '
                    'When data is not available, say so clearly.'
                )
            )
        ]

        for previous_message in recent_history:
            messages.append(HumanMessage(content=previous_message))

        messages.append(HumanMessage(content=user_message))

        try:
            result = llm.invoke(messages)
            content = getattr(result, 'content', str(result))
            state['final_response'] = str(content)
        except Exception:
            state['final_response'] = _fallback_answer(user_message, recent_history)

        return state

    graph.add_node('intent_router', intent_router)
    graph.add_node('response_builder', response_builder)
    graph.add_edge(START, 'intent_router')
    graph.add_edge('intent_router', 'response_builder')
    graph.add_edge('response_builder', END)
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
            'session_id': session_id,
            'provider': settings.active_ai_provider,
            'context': history,
        }

    state = {
        'user_message': trimmed_message,
        'history': history,
    }

    if agent_graph is None:
        answer = _fallback_answer(trimmed_message, history)
        rows: list[dict[str, Any]] = []
        summary = 'No SQL query executed.'
    else:
        result = agent_graph.invoke(state)
        answer = result.get('final_response', _fallback_answer(trimmed_message, history))
        rows = result.get('rows', [])
        summary = result.get('summary', 'No SQL query executed.')

    conversation_store[session_id].append(f'User: {trimmed_message}')
    conversation_store[session_id].append(f'Assistant: {answer}')

    return {
        'answer': answer,
        'rows': rows,
        'summary': summary,
        'session_id': session_id,
        'provider': settings.active_ai_provider,
        'context': list(conversation_store[session_id])[-6:],
    }
