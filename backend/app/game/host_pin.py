"""The host remote's PIN: long by default, compared in constant time, and locked out after repeated guesses."""
from __future__ import annotations

import secrets
from collections.abc import Callable

MIN_PIN_LENGTH = 8
MAX_FAILED_ATTEMPTS = 10
LOCKOUT_SECONDS = 60.0


def resolve_host_pin(configured: str | None) -> str:
    if not configured:
        return secrets.token_urlsafe(MIN_PIN_LENGTH)
    if len(configured) < MIN_PIN_LENGTH:
        raise ValueError(f'GAME_HOST_PIN must be at least {MIN_PIN_LENGTH} characters long.')
    return configured


class HostPinGuard:
    def __init__(self, pin: str, clock: Callable[[], float]) -> None:
        self._pin = pin.encode()
        self._clock = clock
        self._failed_attempts = 0
        self._locked_until = 0.0

    def accepts(self, candidate: str | None) -> bool:
        if self._is_locked():
            return False
        if candidate and secrets.compare_digest(candidate.encode(), self._pin):
            self._failed_attempts = 0
            return True
        self._record_failure()
        return False

    def _is_locked(self) -> bool:
        return self._clock() < self._locked_until

    def _record_failure(self) -> None:
        self._failed_attempts += 1
        if self._failed_attempts >= MAX_FAILED_ATTEMPTS:
            self._locked_until = self._clock() + LOCKOUT_SECONDS
            self._failed_attempts = 0
