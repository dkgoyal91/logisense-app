import asyncio
import csv
from pathlib import Path

import pytest

from app.game import engine
from app.game.models import GameError
from app.game.takeaway import TakeawayDispatcher, TakeawayLog
from app.game.takeaway_mail import MailSettings
from game_support import joined_state

CONFIGURED = MailSettings(host='smtp.gmail.com', port=587, username='flo.demo@gmail.com', password='pw',
                          from_address='flo.demo@gmail.com', from_name='LogiSense', repo_url='https://github.com/o/r')
UNCONFIGURED = MailSettings(host='smtp.gmail.com', port=587, username=None, password=None, from_address=None,
                            from_name='LogiSense', repo_url='https://github.com/o/r')


class RecordingSender:
    def __init__(self) -> None:
        self.sent = []

    def send(self, message) -> None:
        self.sent.append(message)


class FailingSender:
    def send(self, _message) -> None:
        raise OSError('535 Username and Password not accepted')


def _rows(path: Path) -> list[dict]:
    with path.open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def test_dispatcher_sends_and_logs(tmp_path: Path) -> None:
    sender = RecordingSender()
    dispatcher = TakeawayDispatcher(CONFIGURED, TakeawayLog(tmp_path / 'log.csv'), sender, min_interval=0)
    assert asyncio.run(dispatcher.deliver('Ananya', 'ananya@nagarro.com')) == 'sent'
    assert sender.sent[0]['To'] == 'ananya@nagarro.com'
    assert [(r['name'], r['email'], r['status']) for r in _rows(tmp_path / 'log.csv')] == [('Ananya', 'ananya@nagarro.com', 'sent')]


def test_dispatcher_without_mail_settings_collects_for_later(tmp_path: Path) -> None:
    dispatcher = TakeawayDispatcher(UNCONFIGURED, TakeawayLog(tmp_path / 'log.csv'), None, min_interval=0)
    assert asyncio.run(dispatcher.deliver('Ananya', 'ananya@nagarro.com')) == 'saved'
    assert _rows(tmp_path / 'log.csv')[0]['status'] == 'pending'


def test_dispatcher_records_failures_with_the_reason(tmp_path: Path) -> None:
    dispatcher = TakeawayDispatcher(CONFIGURED, TakeawayLog(tmp_path / 'log.csv'), FailingSender(), min_interval=0)
    assert asyncio.run(dispatcher.deliver('Ananya', 'ananya@nagarro.com')) == 'failed'
    row = _rows(tmp_path / 'log.csv')[0]
    assert row['status'] == 'failed'
    assert '535' in row['detail']


def test_log_writes_the_header_once(tmp_path: Path) -> None:
    log = TakeawayLog(tmp_path / 'nested' / 'log.csv')
    log.record('A', 'a@x.com', 'sent')
    log.record('B', 'b@x.com', 'failed', 'boom')
    lines = (tmp_path / 'nested' / 'log.csv').read_text(encoding='utf-8').splitlines()
    assert lines[0].startswith('timestamp,name,email,status,detail')
    assert len(lines) == 3


def test_request_takeaway_once_per_player_but_allows_retry_after_failure() -> None:
    state, (ada,) = joined_state('Ada')
    engine.request_takeaway(state, ada, 'a•••@x.com')
    assert state.players[ada].takeaway_status == 'queued'
    with pytest.raises(GameError, match='already on its way'):
        engine.request_takeaway(state, ada, 'a•••@x.com')
    engine.record_takeaway_result(state, ada, 'failed')
    engine.request_takeaway(state, ada, 'a•••@y.com')
    assert state.players[ada].takeaway_hint == 'a•••@y.com'


def test_kicked_player_cannot_request_the_takeaway() -> None:
    state, (ada,) = joined_state('Ada')
    engine.kick(state, ada)
    with pytest.raises(GameError, match='removed'):
        engine.request_takeaway(state, ada, 'a•••@x.com')
