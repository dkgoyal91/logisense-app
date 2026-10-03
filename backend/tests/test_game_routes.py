from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.game import routes
from app.game.persistence import SnapshotStore
from app.game.service import GameService
from app.main import app
from game_support import QUESTIONS, fake_copilot

PIN = '424242'


@pytest.fixture
def client(tmp_path: Path):
    service = GameService(
        questions=QUESTIONS,
        store=SnapshotStore(tmp_path / 'snapshot.json'),
        run_copilot=fake_copilot,
        host_pin=PIN,
        join_url='https://example.test/play',
    )
    routes.use_service(service)
    with TestClient(app) as test_client:
        yield test_client
    routes.use_service(None)


def _view(socket) -> dict:
    message = socket.receive_json()
    assert message['type'] == 'state', message
    return message['view']


def _join(socket, name: str) -> dict:
    socket.send_json({'type': 'join', 'name': name})
    return _view(socket)


def test_full_question_round_over_websockets(client: TestClient) -> None:
    with client.websocket_connect(f'/ws/game/host?pin={PIN}') as host:
        assert _view(host)['phase'] == 'lobby'
        with client.websocket_connect('/ws/game/play') as ada, client.websocket_connect('/ws/game/play') as bob:
            _view(ada)
            _view(bob)
            assert _join(ada, 'Ada')['me']['name'] == 'Ada'
            assert _view(host)['lobby']['count'] == 1
            _join(bob, 'Bob')
            _view(host)

            host.send_json({'type': 'host', 'action': 'next'})
            assert [_view(socket)['phase'] for socket in (host, ada, bob)] == ['question_open'] * 3

            ada.send_json({'type': 'answer', 'option': 2})
            assert _view(ada)['my_answer'] == 2
            _view(host)
            bob.send_json({'type': 'answer', 'option': 0})
            _view(bob)
            assert _view(host)['question']['answered_count'] == 2

            host.send_json({'type': 'host', 'action': 'reveal'})
            assert _view(host)['reveal']['distribution'] == [1, 0, 1, 0]
            assert _view(ada)['result']['correct'] is True
            assert _view(bob)['result']['correct'] is False


def test_errors_go_only_to_the_sender(client: TestClient) -> None:
    with client.websocket_connect('/ws/game/play') as ada:
        _view(ada)
        ada.send_json({'type': 'answer', 'option': 0})
        assert ada.receive_json() == {'type': 'error', 'message': 'Cannot answer during lobby.'}
        ada.send_text('not json')
        assert ada.receive_json() == {'type': 'error', 'message': 'Malformed message.'}
        ada.send_json({'type': 'answer', 'option': 'x'})
        assert ada.receive_json() == {'type': 'error', 'message': 'Malformed message.'}
        ada.send_json({'type': 'dance'})
        assert ada.receive_json() == {'type': 'error', 'message': 'Unknown message type.'}


def test_host_requires_the_pin(client: TestClient) -> None:
    with client.websocket_connect('/ws/game/host?pin=wrong') as host:
        with pytest.raises(WebSocketDisconnect) as closed:
            host.receive_json()
    assert closed.value.code == 1008


def test_rejoin_with_token_restores_the_player(client: TestClient) -> None:
    with client.websocket_connect('/ws/game/play') as first:
        _view(first)
        me = _join(first, 'Ada')['me']
    with client.websocket_connect('/ws/game/play') as second:
        _view(second)
        second.send_json({'type': 'join', 'name': 'Someone', 'token': me['token']})
        assert _view(second)['me']['id'] == me['id']


def test_reset_needs_confirmation(client: TestClient) -> None:
    with client.websocket_connect(f'/ws/game/host?pin={PIN}') as host:
        _view(host)
        host.send_json({'type': 'host', 'action': 'reset'})
        assert host.receive_json() == {'type': 'error', 'message': 'Type RESET to confirm.'}
        host.send_json({'type': 'host', 'action': 'reset', 'confirm': 'RESET'})
        assert _view(host)['phase'] == 'lobby'
