"""Track open game sockets and push each one the view for its role."""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

SEND_TIMEOUT_SECONDS = 2.0
CLOSE_TIMEOUT_SECONDS = 1.0
SERVER_ERROR_CLOSE_CODE = 1011


@dataclass(eq=False)
class Connection:
    socket: Any
    role: str
    player_id: str | None = None


ViewBuilder = Callable[[Connection], dict[str, Any]]
Audience = Callable[[Connection], bool]


class Hub:
    def __init__(self) -> None:
        self._connections: set[Connection] = set()

    @property
    def size(self) -> int:
        return len(self._connections)

    def add(self, connection: Connection) -> None:
        self._connections.add(connection)

    def remove(self, connection: Connection) -> None:
        self._connections.discard(connection)

    async def publish(self, build_view: ViewBuilder, audience: Audience) -> None:
        targets = [connection for connection in list(self._connections) if audience(connection)]
        await asyncio.gather(*(self.send_view(connection, build_view(connection)) for connection in targets))

    async def send_view(self, connection: Connection, view: dict[str, Any]) -> None:
        await self._send(connection, {'type': 'state', 'view': view})

    async def send_error(self, connection: Connection, message: str) -> None:
        await self._send(connection, {'type': 'error', 'message': message})

    async def _send(self, connection: Connection, payload: dict[str, Any]) -> None:
        try:
            await asyncio.wait_for(connection.socket.send_json(payload), SEND_TIMEOUT_SECONDS)
        except Exception:  # A dead or stalled socket must never block the show.
            await self._drop(connection)

    async def _drop(self, connection: Connection) -> None:
        """Forget the connection and close its socket, so the client notices and reconnects."""
        self.remove(connection)
        try:
            await asyncio.wait_for(connection.socket.close(code=SERVER_ERROR_CLOSE_CODE), CLOSE_TIMEOUT_SECONDS)
        except Exception:  # Already closed or unreachable: nothing more to do.
            pass
