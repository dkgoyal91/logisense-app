from __future__ import annotations

import re

from app.game.models import GameError

MIN_NAME_LENGTH = 2
MAX_NAME_LENGTH = 20
# Strong words are caught even inside other words ("ShitHead"); mild ones only as whole words ("Peacock" is fine).
STRONG_WORDS = frozenset({
    'asshole', 'bastard', 'bitch', 'bollocks', 'cunt', 'dick', 'fuck', 'hitler', 'nazi', 'shit', 'slut',
    'twat', 'wank', 'whore',
})
MILD_WORDS = frozenset({'arse', 'cock', 'crap', 'piss', 'prick'})
ALLOWED_WORDS = frozenset({
    'arsenal', 'cockburn', 'dickens', 'essex', 'hancock', 'middlesex', 'scunthorpe', 'sussex',
})
WORD_PATTERN = re.compile(r'[A-Za-z]+')
STRONG_PATTERN = re.compile('|'.join(sorted(STRONG_WORDS, key=len, reverse=True)), re.IGNORECASE)
ZERO_WIDTH_CHARACTERS = dict.fromkeys(map(ord, '\u200b\u200c\u200d\u2060\ufeff'))


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
    return ' '.join(str(raw or '').translate(ZERO_WIDTH_CHARACTERS).split())


def _contains_blocked_word(text: str) -> bool:
    return any(_is_offensive(word) for word in WORD_PATTERN.findall(text))


def _is_offensive(word: str) -> bool:
    lowered = word.lower()
    if lowered in ALLOWED_WORDS:
        return False
    return lowered in MILD_WORDS or STRONG_PATTERN.search(lowered) is not None


def _mask_blocked_words(text: str) -> str:
    return WORD_PATTERN.sub(_mask_if_blocked, text)


def _mask_if_blocked(match: re.Match[str]) -> str:
    word = match.group()
    lowered = word.lower()
    if lowered in ALLOWED_WORDS:
        return word
    if lowered in MILD_WORDS:
        return _stars(word)
    return STRONG_PATTERN.sub(lambda found: _stars(found.group()), word)


def _stars(text: str) -> str:
    return '*' * len(text)


def _with_suffix(name: str, suffix: int) -> str:
    digits = str(suffix)
    return f'{name[:MAX_NAME_LENGTH - len(digits)]}{digits}'
