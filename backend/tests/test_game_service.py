import asyncio
from pathlib import Path

from app.game.hub import Connection
from app.game.persistence import SnapshotStore
from app.game.service import GameService
from game_support import QUESTIONS, fake_copilot


class RecordingSocket:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)

    async def close(self, code: int = 1000) -> None:
        return None


def _service(tmp_path: Path, **overrides) -> GameService:
    options = {
        'questions': QUESTIONS,
        'store': SnapshotStore(tmp_path / 'snapshot.json'),
        'run_copilot': fake_copilot,
        'host_pin': 'rehearsal-pin-1234',
        'join_url': '',
    }
    return GameService(**{**options, **overrides})


async def _connect(service: GameService, role: str) -> tuple[RecordingSocket, Connection]:
    socket = RecordingSocket()
    connection = Connection(socket, role)
    await service.connect(connection)
    return socket, connection


def test_player_bursts_are_coalesced_for_show_and_host(tmp_path: Path) -> None:
    async def scenario():
        service = _service(tmp_path, broadcast_interval=0.05)
        show, _ = await _connect(service, 'show')
        actors = []
        for index in range(5):
            socket, connection = await _connect(service, 'play')
            await service.handle_player(connection, {'type': 'join', 'name': f'Player {index}'})
            actors.append(socket)
        await asyncio.sleep(0.2)
        return show, actors

    show, actors = asyncio.run(scenario())
    show_updates = show.sent[1:]
    assert 1 <= len(show_updates) < 5
    assert show_updates[-1]['view']['lobby']['count'] == 5
    assert all(socket.sent[-1]['view']['me'] is not None for socket in actors)
