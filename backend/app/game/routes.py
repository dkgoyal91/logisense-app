"""WebSocket endpoints for the projector, phones and the host remote."""
from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import resolve_backend_path, settings
from app.database import get_connection
from app.game.host_pin import resolve_host_pin
from app.game.hub import Connection
from app.game.persistence import SnapshotStore
from app.game.questions import build_questions, load_shipment_counts
from app.game.reveal import run_copilot
from app.game.service import GameService
from app.game.takeaway import Sender, TakeawayDispatcher, TakeawayLog
from app.game.takeaway_batch import TakeawayBroadcaster
from app.game.gmail_api import GmailApiSender, GmailToken
from app.game.takeaway_mail import MailSettings, SmtpSender

POLICY_VIOLATION = 1008

router = APIRouter()
_service: GameService | None = None

Handler = Callable[[Connection, dict[str, Any]], Awaitable[None]]


def get_service() -> GameService:
    global _service
    if _service is None:
        _service = create_service()
    return _service


def use_service(service: GameService | None) -> None:
    global _service
    _service = service


def create_service() -> GameService:
    pin = resolve_host_pin(settings.game_host_pin)
    print(f'[game] Host remote: /host?pin={pin}', flush=True)
    return GameService(
        questions=_load_questions(),
        store=SnapshotStore(resolve_backend_path(settings.game_snapshot_path)),
        run_copilot=run_copilot,
        host_pin=pin,
        join_url=_join_url(),
        takeaway=_create_takeaway(),
        broadcaster=_create_broadcaster(),
    )


def _create_takeaway() -> TakeawayDispatcher:
    """Collect by default (one email from the host button); with TAKEAWAY_DELIVERY=instant send on request."""
    log = _takeaway_log()
    mail, sender, via = _resolve_sender()
    if settings.takeaway_delivery == 'instant' and sender is not None:
        print(f'[game] Takeaway email: sending instantly via {via}', flush=True)
        return TakeawayDispatcher(mail, log, sender)
    print(f'[game] Takeaway email: collecting addresses for one email ({log.path})', flush=True)
    return TakeawayDispatcher(mail, log, None)


def _create_broadcaster() -> TakeawayBroadcaster:
    mail, sender, via = _resolve_sender()
    if sender is None:
        print('[game] Send-email button: no sender set up (run python -m app.game.gmail_authorize)', flush=True)
    else:
        print(f'[game] Send-email button: ready, sends via {via}', flush=True)
    return TakeawayBroadcaster(mail, _takeaway_log(), sender)


def _takeaway_log() -> TakeawayLog:
    return TakeawayLog(resolve_backend_path(settings.takeaway_log_path))


def _resolve_sender() -> tuple[MailSettings, Sender | None, str]:
    """Prefer the Gmail API (HTTPS, works behind corporate SMTP blocks), then SMTP, else none."""
    gmail_token = GmailToken.load(resolve_backend_path(settings.gmail_token_path))
    if gmail_token is not None:
        return _mail_settings(from_address=gmail_token.sender), GmailApiSender(gmail_token), f'the Gmail API as {gmail_token.sender}'
    mail = _mail_settings()
    if mail.is_configured:
        return mail, SmtpSender(mail), f'{mail.host} as {mail.from_address}'
    return mail, None, ''


def _mail_settings(from_address: str | None = None) -> MailSettings:
    return MailSettings(
        host=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username,
        password=settings.smtp_password,
        from_address=from_address or settings.mail_from or settings.smtp_username,
        from_name=settings.mail_from_name,
        repo_url=settings.takeaway_repo_url,
    )


def _load_questions():
    with get_connection() as connection:
        counts = load_shipment_counts(connection)
    return build_questions(run_copilot, counts)


def _join_url() -> str:
    base = settings.game_public_url.rstrip('/')
    return f'{base}/play' if base else ''


@router.websocket('/ws/game/show')
async def show_socket(websocket: WebSocket) -> None:
    await _serve(websocket, Connection(websocket, 'show'), _ignore)


@router.websocket('/ws/game/play')
async def play_socket(websocket: WebSocket) -> None:
    await _serve(websocket, Connection(websocket, 'play'), get_service().handle_player)


@router.websocket('/ws/game/host')
async def host_socket(websocket: WebSocket) -> None:
    service = get_service()
    if not service.is_host_pin(websocket.query_params.get('pin')):
        await _reject(websocket)
        return
    await _serve(websocket, Connection(websocket, 'host'), service.handle_host)


async def _serve(websocket: WebSocket, connection: Connection, handle: Handler) -> None:
    service = get_service()
    await websocket.accept()
    await service.connect(connection)
    try:
        while True:
            await _receive_one(websocket, connection, handle)
    except WebSocketDisconnect:
        pass
    finally:
        service.disconnect(connection)


async def _receive_one(websocket: WebSocket, connection: Connection, handle: Handler) -> None:
    message = _parse(await _receive_text(websocket))
    if message is None:
        await get_service().hub.send_error(connection, 'Malformed message.')
        return
    await handle(connection, message)


async def _receive_text(websocket: WebSocket) -> str:
    try:
        return await websocket.receive_text()
    except RuntimeError as exc:  # Starlette's signal that a failed send already closed this socket.
        raise WebSocketDisconnect() from exc


def _parse(raw: str) -> dict[str, Any] | None:
    try:
        message = json.loads(raw)
    except ValueError:
        return None
    return message if isinstance(message, dict) else None


async def _reject(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.close(code=POLICY_VIOLATION)


async def _ignore(_connection: Connection, _message: dict[str, Any]) -> None:
    return None
