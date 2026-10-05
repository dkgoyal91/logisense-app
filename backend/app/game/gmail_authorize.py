"""One-time Gmail API authorization for the takeaway email (run from the backend folder):

    ../.venv/bin/python -m app.game.gmail_authorize --client-secret ~/Downloads/client_secret_XXX.json \\
        --sender your.address@gmail.com

Opens your browser; you sign in to Google yourself and allow "Send email on your behalf". The send-only
refresh token is saved to backend/data/gmail_token.json (git-ignored). Nothing here ever sees your password.
"""
from __future__ import annotations

import argparse
import json
import secrets
import socket
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app.config import resolve_backend_path, settings
from app.game.gmail_api import GmailToken, authorization_url, exchange_code, pkce_pair

DONE_PAGE = b'<h2>LogiSense: Gmail connected. You can close this tab.</h2>'


def read_client_secret(path: Path) -> tuple[str, str]:
    data = json.loads(path.expanduser().read_text(encoding='utf-8'))
    if 'installed' not in data:
        raise SystemExit('This client secret is not for a "Desktop app" OAuth client. Create one of type Desktop app.')
    return data['installed']['client_id'], data['installed']['client_secret']


def code_from_callback(path: str, expected_state: str) -> str:
    query = {key: values[0] for key, values in parse_qs(urlparse(path).query).items()}
    if 'error' in query:
        raise SystemExit(f'Google returned an error: {query["error"]}')
    if query.get('state') != expected_state:
        raise SystemExit('The authorization response state did not match; please try again.')
    return query['code']


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


def _wait_for_callback(port: int) -> str:
    captured: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 (http.server naming)
            captured['path'] = self.path
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(DONE_PAGE)

        def log_message(self, *_args) -> None:
            return None

    with HTTPServer(('127.0.0.1', port), Handler) as server:
        while 'path' not in captured:
            server.handle_request()
    return captured['path']


def authorize(client_secret: Path, sender: str, token_path: Path) -> None:
    client_id, client_secret_value = read_client_secret(client_secret)
    port = _free_port()
    redirect_uri = f'http://127.0.0.1:{port}/'
    verifier, challenge = pkce_pair()
    state = secrets.token_urlsafe(16)
    url = authorization_url(client_id, redirect_uri, challenge, state)
    print('Opening your browser to authorize Gmail sending. If it does not open, visit:\n' + url, flush=True)
    webbrowser.open(url)
    code = code_from_callback(_wait_for_callback(port), state)
    refresh_token = exchange_code(client_id, client_secret_value, code, verifier, redirect_uri)
    GmailToken(client_id, client_secret_value, refresh_token, sender).save(token_path)
    print(f'Saved send-only Gmail token to {token_path}. Restart the backend to start sending as {sender}.')


def main() -> None:
    parser = argparse.ArgumentParser(description='Authorize LogiSense to send takeaway emails from your Gmail.')
    parser.add_argument('--client-secret', required=True, type=Path, help='Desktop-app OAuth client JSON from Google Cloud')
    parser.add_argument('--sender', required=True, help='The Gmail address you will sign in with')
    args = parser.parse_args()
    authorize(args.client_secret, args.sender, resolve_backend_path(settings.gmail_token_path))


if __name__ == '__main__':
    main()
