import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.game import engine, routes
from app.game.models import GameError
from app.game.persistence import SnapshotStore
from app.game.service import GameService
from app.game.takeaway import TakeawayDispatcher, TakeawayLog
from app.game.takeaway_batch import TakeawayBroadcaster, pending_recipients, read_log
from app.game.takeaway_mail import MailSettings, build_bcc_message
from app.main import app
from game_support import QUESTIONS, fake_copilot, joined_state

PIN = 'broadcast-pin-1234'
SETTINGS = MailSettings(host='smtp.gmail.com', port=587, username=None, password=None,
                        from_address='flocompanion2026@gmail.com', from_name='LogiSense @ Flo 2026',
                        repo_url='https://github.com/dkgoyal91/logisense-app')


class RecordingSender:
    def __init__(self) -> None:
        self.sent = []

    def send(self, message) -> None:
        self.sent.append(message)


class FailingSender:
    def send(self, _message) -> None:
        raise OSError('quota exceeded')


def _log_with(tmp_path: Path, *emails: str) -> TakeawayLog:
    log = TakeawayLog(tmp_path / 'takeaway.csv')
    for email in emails:
        log.record('p', email, 'pending')
    return log


# Message and broadcaster ------------------------------------------------------------------

def test_bcc_message_goes_to_the_sender_with_everyone_in_bcc() -> None:
    message = build_bcc_message(['a@x.com', 'b@y.com'], SETTINGS)
    assert message['To'] == 'flocompanion2026@gmail.com'
    assert message['Bcc'] == 'a@x.com, b@y.com'
    assert 'Hi there,' in message.get_body(('plain',)).get_content()


def test_broadcaster_sends_one_email_and_marks_everyone_sent(tmp_path: Path) -> None:
    sender = RecordingSender()
    log = _log_with(tmp_path, 'a@x.com', 'b@y.com', 'A@X.com')
    broadcaster = TakeawayBroadcaster(SETTINGS, log, sender)
    recipients = broadcaster.pending()
    assert recipients == ['a@x.com', 'b@y.com']
    assert asyncio.run(broadcaster.send(recipients)) == ('sent', '')
    assert len(sender.sent) == 1
    assert pending_recipients(read_log(log.path)) == []


def test_broadcaster_failure_keeps_everyone_pending(tmp_path: Path) -> None:
    log = _log_with(tmp_path, 'a@x.com')
    status, detail = asyncio.run(TakeawayBroadcaster(SETTINGS, log, FailingSender()).send(['a@x.com']))
    assert status == 'failed'
    assert 'quota exceeded' in detail
    assert pending_recipients(read_log(log.path)) == ['a@x.com']


def test_broadcaster_without_a_sender_cannot_send(tmp_path: Path) -> None:
    assert TakeawayBroadcaster(SETTINGS, _log_with(tmp_path), None).can_send is False


# Engine -----------------------------------------------------------------------------------

def test_broadcast_needs_recipients_and_cannot_overlap() -> None:
    state, _ids = joined_state('Ada')
    with pytest.raises(GameError, match='Nobody has asked'):
        engine.start_takeaway_broadcast(state, 0)
    engine.start_takeaway_broadcast(state, 3)
    assert state.takeaway_broadcast == {'status': 'sending', 'count': 3, 'detail': ''}
    with pytest.raises(GameError, match='already sending'):
        engine.start_takeaway_broadcast(state, 3)


def test_finished_broadcast_marks_waiting_players_sent() -> None:
    state, (ada, bob) = joined_state('Ada', 'Bob')
    engine.request_takeaway(state, ada, 'a•••@x.com')
    engine.record_takeaway_result(state, ada, 'saved')
    engine.start_takeaway_broadcast(state, 1)
    engine.finish_takeaway_broadcast(state, 'sent', 1)
    assert state.players[ada].takeaway_status == 'sent'
    assert state.players[bob].takeaway_status is None
    assert state.takeaway_broadcast['status'] == 'sent'


# End to end over WebSockets ------------------------------------------------------------------

@pytest.fixture
def setup(tmp_path: Path):
    sender = RecordingSender()
    log = TakeawayLog(tmp_path / 'takeaway.csv')
    service = GameService(
        questions=QUESTIONS, store=SnapshotStore(tmp_path / 'snapshot.json'), run_copilot=fake_copilot,
        host_pin=PIN, join_url='', broadcast_interval=0.01,
        takeaway=TakeawayDispatcher(SETTINGS, log, None, min_interval=0),
        broadcaster=TakeawayBroadcaster(SETTINGS, log, sender),
    )
    routes.use_service(service)
    with TestClient(app) as client:
        yield client, sender
    routes.use_service(None)


def _view_until(socket, predicate) -> dict:
    for _ in range(20):
        message = socket.receive_json()
        if message['type'] == 'state' and predicate(message['view']):
            return message['view']
    raise AssertionError('expected view never arrived')


def test_host_button_sends_one_bcc_email_and_everyone_sees_it(setup) -> None:
    client, sender = setup
    with client.websocket_connect('/ws/game/play') as ada, client.websocket_connect('/ws/game/play') as bob:
        for socket, name, email in ((ada, 'Ada', 'ada@x.com'), (bob, 'Bob', 'bob@y.com')):
            socket.receive_json()
            socket.send_json({'type': 'join', 'name': name})
            socket.receive_json()
            socket.send_json({'type': 'takeaway', 'email': email, 'consent': True})
            _view_until(socket, lambda v: (v['me']['takeaway'] or {}).get('status') == 'saved')
        with client.websocket_connect(f'/ws/game/host?pin={PIN}') as host, client.websocket_connect('/ws/game/show') as show:
            host.receive_json()
            show.receive_json()
            host.send_json({'type': 'host', 'action': 'send_takeaway'})
            assert host.receive_json() == {'type': 'error', 'message': 'Tap the button twice to confirm sending.'}
            host.send_json({'type': 'host', 'action': 'send_takeaway', 'confirm': 'SEND'})
            sent = _view_until(show, lambda v: (v['takeaway_broadcast'] or {}).get('status') == 'sent')
            assert sent['takeaway_broadcast']['count'] == 2
        assert _view_until(ada, lambda v: v['me']['takeaway']['status'] == 'sent')
    assert len(sender.sent) == 1
    assert sender.sent[0]['Bcc'] == 'ada@x.com, bob@y.com'
