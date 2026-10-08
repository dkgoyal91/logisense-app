from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.game import routes
from app.game.persistence import SnapshotStore
from app.game.service import GameService
from app.game.takeaway import TakeawayDispatcher, TakeawayLog
from app.game.takeaway_mail import MailSettings
from app.main import app
from game_support import QUESTIONS, fake_copilot

PIN = 'takeaway-pin-1234'
SETTINGS = MailSettings(host='smtp.gmail.com', port=587, username='flo.demo@gmail.com', password='pw',
                        from_address='flo.demo@gmail.com', from_name='LogiSense', repo_url='https://github.com/o/r')


class RecordingSender:
    def __init__(self) -> None:
        self.sent = []

    def send(self, message) -> None:
        self.sent.append(message)


def _service(tmp_path: Path, takeaway: TakeawayDispatcher | None) -> GameService:
    return GameService(questions=QUESTIONS, store=SnapshotStore(tmp_path / 'snapshot.json'), run_copilot=fake_copilot,
                       host_pin=PIN, join_url='', broadcast_interval=0.01, takeaway=takeaway)


@pytest.fixture
def sender() -> RecordingSender:
    return RecordingSender()


@pytest.fixture
def client(tmp_path: Path, sender: RecordingSender):
    dispatcher = TakeawayDispatcher(SETTINGS, TakeawayLog(tmp_path / 'takeaway.csv'), sender, min_interval=0)
    routes.use_service(_service(tmp_path, dispatcher))
    with TestClient(app) as test_client:
        yield test_client
    routes.use_service(None)


def _next(socket) -> dict:
    return socket.receive_json()


def _joined(client: TestClient):
    socket = client.websocket_connect('/ws/game/play')
    ws = socket.__enter__()
    _next(ws)
    ws.send_json({'type': 'join', 'name': 'Ananya'})
    _next(ws)
    return socket, ws


def test_takeaway_needs_consent(client: TestClient) -> None:
    socket, ws = _joined(client)
    ws.send_json({'type': 'takeaway', 'email': 'ananya@nagarro.com', 'consent': False})
    assert _next(ws) == {'type': 'error', 'message': 'Please tick the consent box first.'}
    socket.__exit__(None, None, None)


def test_takeaway_is_sent_once_and_the_phone_sees_progress(client: TestClient, sender: RecordingSender) -> None:
    socket, ws = _joined(client)
    ws.send_json({'type': 'takeaway', 'email': ' Ananya@Nagarro.COM ', 'consent': True})
    queued = _next(ws)['view']['me']['takeaway']
    assert queued == {'status': 'queued', 'email_hint': 'A•••@nagarro.com'}
    assert _next(ws)['view']['me']['takeaway']['status'] == 'sent'
    assert sender.sent[0]['To'] == 'Ananya@nagarro.com'
    ws.send_json({'type': 'takeaway', 'email': 'ananya@nagarro.com', 'consent': True})
    assert _next(ws) == {'type': 'error', 'message': 'Your email is already on its way.'}
    socket.__exit__(None, None, None)
    with client.websocket_connect(f'/ws/game/host?pin={PIN}') as host:
        view = _next(host)['view']
        assert view['takeaway_counts'] == {'sent': 1}
        assert 'nagarro' not in str(view['players'])


def test_invalid_email_is_rejected(client: TestClient) -> None:
    socket, ws = _joined(client)
    ws.send_json({'type': 'takeaway', 'email': 'not-an-email', 'consent': True})
    assert _next(ws) == {'type': 'error', 'message': 'Please enter a valid email address.'}
    socket.__exit__(None, None, None)


def test_takeaway_unavailable_without_a_dispatcher(tmp_path: Path) -> None:
    routes.use_service(_service(tmp_path, None))
    try:
        with TestClient(app) as test_client:
            socket, ws = _joined(test_client)
            ws.send_json({'type': 'takeaway', 'email': 'ananya@nagarro.com', 'consent': True})
            assert _next(ws) == {'type': 'error', 'message': 'Email takeaway is not available right now.'}
            socket.__exit__(None, None, None)
    finally:
        routes.use_service(None)
