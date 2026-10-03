"""Run the real copilot query path and shape the result for the projector."""
from __future__ import annotations

from typing import Any

from app.sql_service import execute_safe_query

SAMPLE_ROW_COUNT = 3
HIDDEN_COLUMNS = frozenset({'latitude', 'longitude'})


def run_copilot(prompt: str) -> dict[str, Any]:
    try:
        result = execute_safe_query(prompt)
    except ValueError as exc:
        return _blocked_result(str(exc))
    return _display_result(result)


def _display_result(result: dict[str, Any]) -> dict[str, Any]:
    rows = result.get('rows', [])
    return {
        'table': result.get('table'),
        'sql': result.get('sql'),
        'row_count': len(rows),
        'sample_rows': [_display_row(row) for row in rows[:SAMPLE_ROW_COUNT]],
        'summary': result.get('summary', ''),
        'error': None,
    }


def _display_row(row: dict[str, Any]) -> dict[str, Any]:
    return {column: value for column, value in row.items() if column not in HIDDEN_COLUMNS}


def _blocked_result(reason: str) -> dict[str, Any]:
    return {'table': None, 'sql': None, 'row_count': 0, 'sample_rows': [], 'summary': 'Blocked.', 'error': reason}
