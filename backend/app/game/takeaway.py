"""Deliver takeaway emails in the background and keep an audit CSV so nothing is lost if a send fails."""
from __future__ import annotations

import asyncio
import csv
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from app.game.takeaway_mail import MailSettings, build_takeaway_message

LOG_FIELDS = ('timestamp', 'name', 'email', 'status', 'detail')
MAX_DETAIL_LENGTH = 200
DEFAULT_MIN_INTERVAL_SECONDS = 0.5  # keeps a burst of 300 sign-ups well inside Gmail's sending limits


class Sender(Protocol):
    def send(self, message) -> None: ...


class TakeawayLog:
    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def record(self, name: str, email: str, status: str, detail: str = '') -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        is_new = not self._path.exists()
        with self._path.open('a', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=LOG_FIELDS)
            if is_new:
                writer.writeheader()
            writer.writerow(_row(name, email, status, detail))


def _row(name: str, email: str, status: str, detail: str) -> dict[str, str]:
    return {
        'timestamp': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'name': name,
        'email': email,
        'status': status,
        'detail': detail[:MAX_DETAIL_LENGTH],
    }


class TakeawayDispatcher:
    """Sends one email at a time, spaced out, off the event loop. Returns 'sent', 'failed' or 'saved'."""

    def __init__(self, settings: MailSettings, log: TakeawayLog, sender: Sender | None,
                 min_interval: float = DEFAULT_MIN_INTERVAL_SECONDS) -> None:
        self._settings = settings
        self._log = log
        self._sender = sender
        self._min_interval = min_interval
        self._lock = asyncio.Lock()
        self._last_sent_at = 0.0

    @property
    def can_send(self) -> bool:
        return self._sender is not None and bool(self._settings.from_address)

    async def deliver(self, name: str, email: str) -> str:
        if not self.can_send:
            self._log.record(name, email, 'pending', 'mail not configured')
            return 'saved'
        async with self._lock:
            await self._respect_interval()
            return await self._send(name, email)

    async def _respect_interval(self) -> None:
        wait = self._min_interval - (time.monotonic() - self._last_sent_at)
        if wait > 0:
            await asyncio.sleep(wait)

    async def _send(self, name: str, email: str) -> str:
        message = build_takeaway_message(email, name, self._settings)
        try:
            await asyncio.to_thread(self._sender.send, message)
        except Exception as exc:  # any SMTP/network failure is logged for a manual resend, never raised into the game
            self._log.record(name, email, 'failed', f'{type(exc).__name__}: {exc}')
            return 'failed'
        finally:
            self._last_sent_at = time.monotonic()
        self._log.record(name, email, 'sent')
        return 'sent'
