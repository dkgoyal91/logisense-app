"""Expose only the game through the public tunnel; the copilot dashboard and its APIs stay on localhost."""
from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import FastAPI
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

PUBLIC_PATHS = frozenset({
    '/play', '/show', '/host', '/logisense-mark.svg', '/ws/game/play', '/ws/game/show', '/ws/game/host',
})
PUBLIC_PREFIXES = ('/assets/',)
POLICY_VIOLATION = 1008


def install_public_allowlist(app: FastAPI, public_url: str) -> None:
    public_host = _host_of(public_url)
    if public_host:
        app.add_middleware(PublicHostAllowlist, public_host=public_host)


def is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES)


def _host_of(url: str) -> str:
    return urlsplit(url).netloc.lower() if url else ''


class PublicHostAllowlist:
    def __init__(self, app: ASGIApp, public_host: str) -> None:
        self.app = app
        self.public_host = public_host

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self._is_blocked(scope):
            await _refuse(scope, receive, send)
            return
        await self.app(scope, receive, send)

    def _is_blocked(self, scope: Scope) -> bool:
        if scope['type'] not in ('http', 'websocket'):
            return False
        return _request_host(scope) == self.public_host and not is_public_path(scope['path'])


def _request_host(scope: Scope) -> str:
    headers = dict(scope.get('headers') or [])
    return headers.get(b'host', b'').decode('latin-1').lower()


async def _refuse(scope: Scope, receive: Receive, send: Send) -> None:
    if scope['type'] == 'websocket':
        await send({'type': 'websocket.close', 'code': POLICY_VIOLATION})
        return
    await PlainTextResponse('Not found', status_code=404)(scope, receive, send)
