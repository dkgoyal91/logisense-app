from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.chat_agent import process_chat_turn
from app.config import settings
from app.database import initialize_database
from app.sql_service import get_dashboard_snapshot, get_filter_options, get_live_table_rows

app = FastAPI(title=settings.app_name, version='0.1.0')

initialize_database()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


class ChatMessage(BaseModel):
    message: str
    session_id: str | None = None


@app.get('/health')
def health() -> dict[str, str]:
    return {
        'status': 'ok',
        'app_name': settings.app_name,
        'provider': settings.active_ai_provider,
    }


@app.post('/api/chat')
def chat_message(payload: ChatMessage) -> dict[str, object]:
    message = payload.message.strip()
    if not message:
        return {
            'answer': 'Please provide a question to analyze.',
            'table': None,
            'rows': [],
            'summary': 'No input provided.',
            'provider': settings.active_ai_provider,
            'session_id': payload.session_id or 'default-session',
        }

    result = process_chat_turn(payload.session_id or 'default-session', message)
    return {
        'answer': result['answer'],
        'table': result.get('table'),
        'rows': result.get('rows', []),
        'summary': result.get('summary', result['answer']),
        'provider': result['provider'],
        'session_id': result['session_id'],
        'context': result['context'],
    }


@app.get('/api/dashboard')
def dashboard_snapshot() -> dict[str, object]:
    return get_dashboard_snapshot()


@app.get('/api/live/{table_name}')
def live_table_data(
    table_name: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    q: str | None = Query(default=None, max_length=200),
    filters: str | None = Query(default=None, max_length=1000),
) -> dict[str, object]:
    parsed_filters: dict[str, object] = {}
    if filters:
        try:
            parsed = json.loads(filters)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail='filters must be valid JSON.') from exc
        if not isinstance(parsed, dict):
            raise HTTPException(status_code=400, detail='filters must be a JSON object of column: value pairs.')
        parsed_filters = parsed

    try:
        return get_live_table_rows(table_name, page=page, page_size=page_size, search=q, filters=parsed_filters)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get('/api/live/{table_name}/filters')
def live_table_filter_options(table_name: str) -> dict[str, object]:
    try:
        return {'table': table_name.lower().strip(), 'columns': get_filter_options(table_name)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.websocket('/ws/chat')
async def websocket_chat(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            payload = await websocket.receive_text()
            if not payload:
                continue

            session_id = 'default-session'
            message = payload
            result = process_chat_turn(session_id, message)
            await websocket.send_json(result)
    except WebSocketDisconnect:
        return
