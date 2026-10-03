from __future__ import annotations

import re

from app.game.models import GameError

MIN_NAME_LENGTH = 2
MAX_NAME_LENGTH = 20
BLOCKED_WORDS = frozenset({
    'arse', 'asshole', 'bastard', 'bitch', 'bollocks', 'cock', 'crap', 'cunt', 'dick',
    'fuck', 'fucker', 'hitler', 'nazi', 'piss', 'prick', 'shit', 'slut', 'twat', 'wanker', 'whore',
})
WORD_PATTERN = re.compile(r'[A-Za-z]+')


def clean_name(raw: str) -> str:
    name = _collapse_whitespace(raw)[:MAX_NAME_LENGTH].strip()
    if len(name) < MIN_NAME_LENGTH:
        raise GameError(f'Name must be at least {MIN_NAME_LENGTH} characters.')
    if _contains_blocked_word(name):
        raise GameError('Please choose a different name.')
    return name


def unique_name(name: str, taken: set[str]) -> str:
    lowered_taken = {existing.lower() for existing in taken}
    if name.lower() not in lowered_taken:
        return name
    suffix = 2
    while _with_suffix(name, suffix).lower() in lowered_taken:
        suffix += 1
    return _with_suffix(name, suffix)


def clean_free_text(raw: str, max_length: int) -> str:
    text = _collapse_whitespace(raw)[:max_length].strip()
    if not text:
        raise GameError('Please type something first.')
    return _mask_blocked_words(text)


def _collapse_whitespace(raw: str) -> str:
    return ' '.join(str(raw or '').split())


def _contains_blocked_word(text: str) -> bool:
    return any(word.lower() in BLOCKED_WORDS for word in WORD_PATTERN.findall(text))


def _mask_blocked_words(text: str) -> str:
    return WORD_PATTERN.sub(_mask_if_blocked, text)


def _mask_if_blocked(match: re.Match[str]) -> str:
    word = match.group()
    return '*' * len(word) if word.lower() in BLOCKED_WORDS else word


def _with_suffix(name: str, suffix: int) -> str:
    digits = str(suffix)
    return f'{name[:MAX_NAME_LENGTH - len(digits)]}{digits}'
