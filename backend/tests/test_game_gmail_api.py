import base64
import json
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from app.game.gmail_api import (
    GMAIL_SEND_SCOPE,
    GmailApiError,
    GmailApiSender,
    GmailToken,
    authorization_url,
    exchange_code,
    pkce_pair,
)

TOKEN = GmailToken(client_id='cid.apps.googleusercontent.com', client_secret='csecret', refresh_token='rtoken',
                   sender='flo.demo@gmail.com')


class FakeHttp:
    """Records requests and replays canned (status, json) responses in order."""

    def __init__(self, *responses) -> None:
        self.responses = list(responses)
        self.requests = []

    def __call__(self, url: str, body: bytes, headers: dict) -> tuple[int, dict]:
        self.requests.append((url, body, headers))
        return self.responses.pop(0)


def _message() -> EmailMessage:
    message = EmailMessage()
    message['To'] = 'ananya@nagarro.com'
    message['Subject'] = 'Hi'
    message.set_content('hello')
    return message


def test_token_round_trips_through_a_file(tmp_path: Path) -> None:
    path = tmp_path / 'gmail_token.json'
    TOKEN.save(path)
    assert GmailToken.load(path) == TOKEN


def test_missing_token_file_loads_as_none(tmp_path: Path) -> None:
    assert GmailToken.load(tmp_path / 'nope.json') is None


def test_send_refreshes_the_access_token_then_posts_the_raw_message() -> None:
    http = FakeHttp((200, {'access_token': 'atoken', 'expires_in': 3600}), (200, {'id': 'msg1'}))
    GmailApiSender(TOKEN, http=http, clock=lambda: 1000.0).send(_message())
    refresh_url, refresh_body, _ = http.requests[0]
    assert refresh_url == 'https://oauth2.googleapis.com/token'
    assert parse_qs(refresh_body.decode()) == {
        'client_id': ['cid.apps.googleusercontent.com'], 'client_secret': ['csecret'],
        'refresh_token': ['rtoken'], 'grant_type': ['refresh_token'],
    }
    send_url, send_body, send_headers = http.requests[1]
    assert send_url == 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send'
    assert send_headers['Authorization'] == 'Bearer atoken'
    raw = base64.urlsafe_b64decode(json.loads(send_body)['raw'])
    assert b'To: ananya@nagarro.com' in raw


def test_access_token_is_reused_until_it_nearly_expires() -> None:
    now = [1000.0]
    http = FakeHttp((200, {'access_token': 'a1', 'expires_in': 3600}), (200, {}), (200, {}),
                    (200, {'access_token': 'a2', 'expires_in': 3600}), (200, {}))
    sender = GmailApiSender(TOKEN, http=http, clock=lambda: now[0])
    sender.send(_message())
    sender.send(_message())
    now[0] += 3600
    sender.send(_message())
    urls = [url for url, _body, _headers in http.requests]
    assert urls.count('https://oauth2.googleapis.com/token') == 2


def test_api_errors_raise_with_googles_reason() -> None:
    http = FakeHttp((200, {'access_token': 'a', 'expires_in': 3600}),
                    (403, {'error': {'message': 'Daily user sending limit exceeded.'}}))
    with pytest.raises(GmailApiError, match='Daily user sending limit exceeded'):
        GmailApiSender(TOKEN, http=http, clock=lambda: 0.0).send(_message())


def test_revoked_refresh_token_raises_a_clear_error() -> None:
    http = FakeHttp((400, {'error': 'invalid_grant', 'error_description': 'Token has been expired or revoked.'}))
    with pytest.raises(GmailApiError, match='re-run the Gmail authorization'):
        GmailApiSender(TOKEN, http=http, clock=lambda: 0.0).send(_message())


def test_authorization_url_requests_send_only_offline_access_with_pkce() -> None:
    verifier, challenge = pkce_pair()
    assert 43 <= len(verifier) <= 128
    url = urlparse(authorization_url('cid', 'http://127.0.0.1:8765/', challenge, state='s1'))
    query = {key: values[0] for key, values in parse_qs(url.query).items()}
    assert url.netloc == 'accounts.google.com'
    assert query['scope'] == GMAIL_SEND_SCOPE
    assert query['access_type'] == 'offline'
    assert query['prompt'] == 'consent'
    assert query['code_challenge'] == challenge
    assert query['code_challenge_method'] == 'S256'
    assert query['redirect_uri'] == 'http://127.0.0.1:8765/'


def test_exchange_code_returns_the_refresh_token() -> None:
    http = FakeHttp((200, {'access_token': 'a', 'refresh_token': 'r-new', 'expires_in': 3600}))
    assert exchange_code('cid', 'cs', 'code123', 'verifier', 'http://127.0.0.1:8765/', http=http) == 'r-new'
    assert parse_qs(http.requests[0][1].decode())['grant_type'] == ['authorization_code']


def test_client_secret_file_from_google_cloud_is_parsed(tmp_path: Path) -> None:
    from app.game.gmail_authorize import read_client_secret

    path = tmp_path / 'client_secret.json'
    path.write_text(json.dumps({'installed': {'client_id': 'cid', 'client_secret': 'cs'}}), encoding='utf-8')
    assert read_client_secret(path) == ('cid', 'cs')


def test_web_client_secret_is_rejected_with_a_hint(tmp_path: Path) -> None:
    from app.game.gmail_authorize import read_client_secret

    path = tmp_path / 'client_secret.json'
    path.write_text(json.dumps({'web': {'client_id': 'cid', 'client_secret': 'cs'}}), encoding='utf-8')
    with pytest.raises(SystemExit, match='Desktop app'):
        read_client_secret(path)


def test_callback_query_must_carry_the_matching_state() -> None:
    from app.game.gmail_authorize import code_from_callback

    assert code_from_callback('/?state=s1&code=abc', 's1') == 'abc'
    with pytest.raises(SystemExit, match='state'):
        code_from_callback('/?state=other&code=abc', 's1')
    with pytest.raises(SystemExit, match='access_denied'):
        code_from_callback('/?state=s1&error=access_denied', 's1')


def test_game_prefers_the_gmail_api_when_a_token_exists(tmp_path: Path, monkeypatch) -> None:
    from app.game import routes

    token_path = tmp_path / 'gmail_token.json'
    TOKEN.save(token_path)
    monkeypatch.setattr(routes.settings, 'gmail_token_path', str(token_path))
    monkeypatch.setattr(routes.settings, 'takeaway_log_path', str(tmp_path / 'log.csv'))
    dispatcher = routes._create_takeaway()
    assert dispatcher.can_send is True
    assert type(dispatcher._sender).__name__ == 'GmailApiSender'
    assert dispatcher._settings.from_address == 'flo.demo@gmail.com'
