import asyncio

from app.game import hub as hub_module
from app.game.hub import Connection, Hub


class StuckSocket:
    async def send_json(self, _payload: dict) -> None:
        await asyncio.sleep(10)


class RecordingSocket:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)


def test_publish_drops_connections_that_time_out(monkeypatch) -> None:
    monkeypatch.setattr(hub_module, 'SEND_TIMEOUT_SECONDS', 0.05)
    hub = Hub()
    stuck = Connection(StuckSocket(), 'play')
    healthy_socket = RecordingSocket()
    healthy = Connection(healthy_socket, 'show')
    hub.add(stuck)
    hub.add(healthy)

    asyncio.run(hub.publish(lambda connection: {'role': connection.role}, lambda _connection: True))

    assert healthy_socket.sent == [{'type': 'state', 'view': {'role': 'show'}}]
    assert hub.size == 1


def test_publish_only_reaches_the_audience() -> None:
    hub = Hub()
    show_socket, play_socket = RecordingSocket(), RecordingSocket()
    hub.add(Connection(show_socket, 'show'))
    hub.add(Connection(play_socket, 'play'))

    asyncio.run(hub.publish(lambda _connection: {}, lambda connection: connection.role == 'show'))

    assert len(show_socket.sent) == 1
    assert play_socket.sent == []


class StuckClosableSocket(StuckSocket):
    def __init__(self) -> None:
        self.closed_with: int | None = None

    async def close(self, code: int = 1000) -> None:
        self.closed_with = code


def test_publish_closes_a_timed_out_socket_so_the_client_reconnects(monkeypatch) -> None:
    monkeypatch.setattr(hub_module, 'SEND_TIMEOUT_SECONDS', 0.05)
    hub = Hub()
    socket = StuckClosableSocket()
    hub.add(Connection(socket, 'host'))

    asyncio.run(hub.publish(lambda _connection: {}, lambda _connection: True))

    assert socket.closed_with == 1011
    assert hub.size == 0
