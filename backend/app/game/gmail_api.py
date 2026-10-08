"""Send takeaway emails through the Gmail API over HTTPS (OAuth, send-only scope), using only the stdlib.

Gmail's SMTP login is blocked on some corporate laptops; the HTTPS API is not. The one-time browser
authorization lives in `app.game.gmail_authorize`; this module refreshes access tokens and sends.
"""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlencode

GMAIL_SEND_SCOPE = 'https://www.googleapis.com/auth/gmail.send'
AUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN_ENDPOINT = 'https://oauth2.googleapis.com/token'
SEND_ENDPOINT = 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send'
EXPIRY_MARGIN_SECONDS = 60
HTTP_TIMEOUT_SECONDS = 20

Http = Callable[[str, bytes, dict], tuple[int, dict]]


class GmailApiError(RuntimeError):
    """Raised when Google refuses a token refresh or a send."""


@dataclass(frozen=True)
class GmailToken:
    client_id: str
    client_secret: str
    refresh_token: str
    sender: str

    @classmethod
    def load(cls, path: Path) -> GmailToken | None:
        if not path.is_file():
            return None
        return cls(**json.loads(path.read_text(encoding='utf-8')))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding='utf-8')
        path.chmod(0o600)


def post(url: str, body: bytes, headers: dict) -> tuple[int, dict]:
    request = urllib.request.Request(url, data=body, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            return response.status, _json(response.read())
    except urllib.error.HTTPError as error:
        return error.code, _json(error.read())


def _json(raw: bytes) -> dict:
    try:
        return json.loads(raw or b'{}')
    except ValueError:
        return {}


# Sending ---------------------------------------------------------------------------------

class GmailApiSender:
    def __init__(self, token: GmailToken, http: Http = post, clock: Callable[[], float] = time.time) -> None:
        self._token = token
        self._http = http
        self._clock = clock
        self._access_token: str | None = None
        self._expires_at = 0.0

    def send(self, message: EmailMessage) -> None:
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode('ascii')
        headers = {'Authorization': f'Bearer {self._current_access_token()}', 'Content-Type': 'application/json'}
        status, payload = self._http(SEND_ENDPOINT, json.dumps({'raw': raw}).encode(), headers)
        if status >= 300:
            raise GmailApiError(f'Gmail API refused the send ({status}): {_reason(payload)}')

    def _current_access_token(self) -> str:
        if self._access_token is None or self._clock() >= self._expires_at - EXPIRY_MARGIN_SECONDS:
            self._refresh()
        return self._access_token or ''

    def _refresh(self) -> None:
        status, payload = _token_request(self._http, {
            'client_id': self._token.client_id,
            'client_secret': self._token.client_secret,
            'refresh_token': self._token.refresh_token,
            'grant_type': 'refresh_token',
        })
        if status >= 300 or 'access_token' not in payload:
            raise GmailApiError(f'Token refresh failed ({_reason(payload)}); re-run the Gmail authorization.')
        self._access_token = payload['access_token']
        self._expires_at = self._clock() + float(payload.get('expires_in', 3600))


def _token_request(http: Http, fields: dict) -> tuple[int, dict]:
    return http(TOKEN_ENDPOINT, urlencode(fields).encode(), {'Content-Type': 'application/x-www-form-urlencoded'})


def _reason(payload: dict) -> str:
    error = payload.get('error')
    if isinstance(error, dict):
        return str(error.get('message', error))
    return str(payload.get('error_description') or error or 'unknown error')


# One-time authorization helpers ----------------------------------------------------------

def pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)[:96]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    return verifier, challenge


def authorization_url(client_id: str, redirect_uri: str, challenge: str, state: str) -> str:
    return AUTH_ENDPOINT + '?' + urlencode({
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': GMAIL_SEND_SCOPE,
        'access_type': 'offline',
        'prompt': 'consent',
        'code_challenge': challenge,
        'code_challenge_method': 'S256',
        'state': state,
    })


def exchange_code(client_id: str, client_secret: str, code: str, verifier: str, redirect_uri: str,
                  http: Http = post) -> str:
    status, payload = _token_request(http, {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'code_verifier': verifier,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
    })
    if status >= 300 or 'refresh_token' not in payload:
        raise GmailApiError(f'Authorization failed: {_reason(payload)}')
    return payload['refresh_token']
