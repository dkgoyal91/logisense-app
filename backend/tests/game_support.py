from __future__ import annotations

from typing import Any

from app.game import engine
from app.game.models import GameState, Question

QUESTIONS = [
    Question('prompt one', 'Question one?', 'Concept one', ('A', 'B', 'C', 'D'), 2),
    Question('prompt two', 'Question two?', 'Concept two', ('A', 'B', 'C', 'D'), 0),
]
COPILOT_RESULT: dict[str, Any] = {
    'table': 'jobs', 'sql': 'SELECT 1', 'row_count': 1, 'sample_rows': [], 'summary': 'ok', 'error': None,
}


def fake_copilot(prompt: str) -> dict[str, Any]:
    return {**COPILOT_RESULT, 'prompt_seen': prompt}


def joined_state(*names: str) -> tuple[GameState, list[str]]:
    state = GameState()
    ids = [engine.join(state, name, None, f'id-{name}', f'tok-{name}').id for name in names]
    return state, ids
