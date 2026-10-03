"""Classify Break It attacks by the safety layer that handles them. Nothing is ever executed."""
from __future__ import annotations

import re

from app.game.models import Verdict
from app.sql_service import ALLOWED_TABLES, _validate_sql, detect_table_from_message

SQL_LIKE_PATTERN = re.compile(
    r'(?i)\b(select|insert|update|delete|drop|alter|union|truncate|create|attach|pragma|exec|execute)\b|;|--'
)
TABLE_REFERENCE_PATTERN = re.compile(r'(?i)\b(?:from|join)\s+([A-Za-z_][A-Za-z0-9_]*)')


def classify_attack(text: str) -> Verdict:
    if detect_table_from_message(text) is None:
        return Verdict('scope', 'Blocked: outside the approved logistics data.')
    if not _looks_like_sql(text):
        return Verdict('answered', 'Answered safely with a pre-written query.')
    return _classify_sql(text)


def _looks_like_sql(text: str) -> bool:
    return SQL_LIKE_PATTERN.search(text) is not None


def _classify_sql(text: str) -> Verdict:
    rejection = _validator_rejection(text)
    if rejection is not None:
        return Verdict('validator', f'Blocked by the SQL validator: {rejection}')
    if _references_unapproved_table(text):
        return Verdict('gap', 'Found a gap! The validator would pass this, but the copilot never runs typed SQL.')
    return Verdict('templates', 'Ignored: the copilot only runs pre-written queries.')


def _validator_rejection(text: str) -> str | None:
    try:
        _validate_sql(text)
    except ValueError as exc:
        return str(exc)
    return None


def _references_unapproved_table(text: str) -> bool:
    return any(table.lower() not in ALLOWED_TABLES for table in TABLE_REFERENCE_PATTERN.findall(text))
