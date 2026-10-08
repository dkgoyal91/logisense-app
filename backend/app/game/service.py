"""Turn socket messages into engine calls, persist, then publish fresh views."""
from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Callable
from typing import Any

from app.game import engine, views
from app.game.guard import classify_attack
from app.game.host_pin import HostPinGuard
from app.game.hub import Audience, Connection, Hub
from app.game.models import GameError, GameState, Question
from app.game.persistence import SnapshotStore
from app.game.takeaway import TakeawayDispatcher
from app.game.takeaway_batch import TakeawayBroadcaster
from app.game.takeaway_mail import mask_email, normalize_email

RESET_CONFIRMATION = 'RESET'
SEND_CONFIRMATION = 'SEND'
BROADCAST_INTERVAL_SECONDS = 0.3
MALFORMED_MESSAGE = 'Malformed message.'

Message = dict[str, Any]
PlayerHandler = Callable[[str | None, Message], None]
HostHandler = Callable[[Message], None]


def _new_id() -> str:
    return uuid.uuid4().hex


class GameService:
    def __init__(
        self,
        questions: list[Question],
        store: SnapshotStore,
        run_copilot: engine.CopilotRunner,
        host_pin: str,
        join_url: str,
        clock: Callable[[], float] = time.time,
        new_id: Callable[[], str] = _new_id,
        broadcast_interval: float = BROADCAST_INTERVAL_SECONDS,
        takeaway: TakeawayDispatcher | None = None,
        broadcaster: TakeawayBroadcaster | None = None,
    ) -> None:
        self.hub = Hub()
        self.state = store.load() or GameState()
        self._questions = questions
        self._store = store
        self._run_copilot = run_copilot
        self._host_pin = HostPinGuard(host_pin, clock)
        self._join_url = join_url
        self._clock = clock
        self._new_id = new_id
        self._lock = asyncio.Lock()
        self._broadcast_interval = broadcast_interval
        self._audience_publish: asyncio.Task[None] | None = None
        self._takeaway = takeaway
        self._broadcaster = broadcaster
        self._deliveries: set[asyncio.Task[None]] = set()

    # Connections ---------------------------------------------------------------------------

    def is_host_pin(self, pin: str | None) -> bool:
        return self._host_pin.accepts(pin)

    async def connect(self, connection: Connection) -> None:
        self.hub.add(connection)
        await self.hub.send_view(connection, self._render(self._context(), connection))

    def disconnect(self, connection: Connection) -> None:
        self.hub.remove(connection)

    async def handle_player(self, connection: Connection, message: Message) -> None:
        if message.get('type') == 'takeaway':
            await self._handle_takeaway(connection, message)
            return
        if await self._apply(connection, lambda: self._dispatch_player(connection, message), _only(connection)):
            self._schedule_audience_publish()

    async def handle_host(self, connection: Connection, message: Message) -> None:
        if message.get('action') == 'send_takeaway':
            await self._handle_takeaway_broadcast(connection, message)
            return
        await self._apply(connection, lambda: self._dispatch_host(message), _everyone)

    # Apply + publish -----------------------------------------------------------------------

    async def _apply(self, connection: Connection, mutate: Callable[[], None], audience: Audience) -> bool:
        error = await self._mutate_and_save(mutate)
        if error is not None:
            await self.hub.send_error(connection, error)
            return False
        await self._publish(audience)
        return True

    async def _publish(self, audience: Audience) -> None:
        ctx = self._context()
        await self.hub.publish(lambda target: self._render(ctx, target), audience)

    def _schedule_audience_publish(self) -> None:
        """Coalesce projector and host updates after player actions: one publish per interval, latest state wins."""
        if self._audience_publish is None or self._audience_publish.done():
            self._audience_publish = asyncio.create_task(self._publish_audience_after_interval())

    async def _publish_audience_after_interval(self) -> None:
        await asyncio.sleep(self._broadcast_interval)
        await self._publish(_show_and_host)

    async def _mutate_and_save(self, mutate: Callable[[], None]) -> str | None:
        async with self._lock:
            try:
                mutate()
            except GameError as exc:
                return str(exc)
            except (KeyError, TypeError, ValueError):
                return MALFORMED_MESSAGE
            self._store.save(self.state)
        return None

    def _context(self) -> views.ViewContext:
        return views.build_context(self.state, self._questions, self._clock(), self._join_url)

    def _render(self, ctx: views.ViewContext, connection: Connection) -> dict[str, Any]:
        if connection.role == 'show':
            return views.show_view(ctx)
        if connection.role == 'host':
            return views.host_view(ctx)
        return views.player_view(ctx, connection.player_id)

    # Takeaway email ------------------------------------------------------------------------

    async def _handle_takeaway(self, connection: Connection, message: Message) -> None:
        request: dict[str, str] = {}
        queued = await self._apply(connection, lambda: request.update(self._queue_takeaway(connection, message)),
                                   _only(connection))
        if queued:
            self._schedule_audience_publish()
            self._start_delivery(connection, request)

    def _queue_takeaway(self, connection: Connection, message: Message) -> dict[str, str]:
        if self._takeaway is None:
            raise GameError('Email takeaway is not available right now.')
        if message.get('consent') is not True:
            raise GameError('Please tick the consent box first.')
        email = normalize_email(message.get('email', ''))
        player = engine.request_takeaway(self.state, connection.player_id, mask_email(email))
        return {'player_id': player.id, 'name': player.name, 'email': email}

    def _start_delivery(self, connection: Connection, request: dict[str, str]) -> None:
        task = asyncio.create_task(self._deliver_takeaway(connection, request))
        self._deliveries.add(task)
        task.add_done_callback(self._deliveries.discard)

    async def _deliver_takeaway(self, connection: Connection, request: dict[str, str]) -> None:
        status = await self._takeaway.deliver(request['name'], request['email'])
        player_id = request['player_id']
        await self._apply(connection, lambda: engine.record_takeaway_result(self.state, player_id, status),
                          _only(connection))
        self._schedule_audience_publish()

    async def _handle_takeaway_broadcast(self, connection: Connection, message: Message) -> None:
        recipients: list[str] = []
        started = await self._apply(connection, lambda: recipients.extend(self._start_broadcast(message)), _everyone)
        if not started:
            return
        status, detail = await self._broadcaster.send(recipients)
        count = len(recipients)
        await self._apply(connection, lambda: engine.finish_takeaway_broadcast(self.state, status, count, detail), _everyone)

    def _start_broadcast(self, message: Message) -> list[str]:
        if message.get('confirm') != SEND_CONFIRMATION:
            raise GameError('Tap the button twice to confirm sending.')
        if self._broadcaster is None or not self._broadcaster.can_send:
            raise GameError('No email sender is set up. Run the Gmail authorization first.')
        recipients = self._broadcaster.pending()
        engine.start_takeaway_broadcast(self.state, len(recipients))
        return recipients

    # Player messages -----------------------------------------------------------------------

    def _dispatch_player(self, connection: Connection, message: Message) -> None:
        kind = message.get('type')
        if kind == 'join':
            self._join(connection, message)
            return
        handler = self._player_handlers().get(str(kind))
        if handler is None:
            raise GameError('Unknown message type.')
        handler(connection.player_id, message)

    def _player_handlers(self) -> dict[str, PlayerHandler]:
        return {
            'answer': self._answer,
            'attack': self._attack,
            'race_done': self._race_done,
            'bonus_question': self._bonus_question,
            'bonus_vote': self._bonus_vote,
        }

    def _join(self, connection: Connection, message: Message) -> None:
        if self._is_bound_to_active_player(connection):
            return
        token = message.get('token')
        player = engine.join(
            self.state, str(message.get('name', '')), token if isinstance(token, str) else None, self._new_id(), self._new_id(),
        )
        connection.player_id = player.id

    def _is_bound_to_active_player(self, connection: Connection) -> bool:
        """A repeated join on a connection that already has a player must not create a second one."""
        player = self.state.players.get(connection.player_id or '')
        return player is not None and not player.kicked

    def _answer(self, player_id: str | None, message: Message) -> None:
        engine.submit_answer(self.state, player_id, int(message['option']), self._clock())

    def _attack(self, player_id: str | None, message: Message) -> None:
        engine.submit_attack(self.state, player_id, str(message['text']), classify_attack, self._new_id(), self._clock())

    def _race_done(self, player_id: str | None, _message: Message) -> None:
        engine.finish_race(self.state, player_id, self._clock())

    def _bonus_question(self, player_id: str | None, message: Message) -> None:
        engine.submit_bonus_question(self.state, player_id, str(message['text']), self._new_id())

    def _bonus_vote(self, player_id: str | None, message: Message) -> None:
        engine.vote_bonus(self.state, player_id, str(message['question_id']))

    # Host messages -------------------------------------------------------------------------

    def _dispatch_host(self, message: Message) -> None:
        handler = self._host_handlers().get(str(message.get('action')))
        if handler is None:
            raise GameError('Unknown host action.')
        self._check_expected_phase(message)
        handler(message)

    def _check_expected_phase(self, message: Message) -> None:
        """A double-tapped Next/Reveal/Skip carries the phase it was tapped in; reject it once the game moved on."""
        expected = message.get('expected_phase')
        if expected is not None and expected != self.state.phase.value:
            raise GameError('The game already moved on.')

    def _host_handlers(self) -> dict[str, HostHandler]:
        question_count = len(self._questions)
        return {
            'start_race': lambda _m: engine.start_race(self.state, self._clock()),
            'next': lambda _m: engine.advance(self.state, question_count, self._clock()),
            'reveal': lambda _m: engine.reveal(self.state, self._questions, self._run_copilot),
            'skip': lambda _m: engine.skip(self.state, question_count, self._clock()),
            'kick': lambda m: engine.kick(self.state, str(m['player_id'])),
            'star_attack': lambda m: engine.star_attack(self.state, str(m['attack_id'])),
            'award_demo': lambda m: engine.award_demo(self.state, str(m['player_id'])),
            'ask_bonus': lambda m: engine.answer_bonus(self.state, str(m['question_id']), self._run_copilot),
            'hands_mode': lambda _m: engine.toggle_hands_mode(self.state),
            'reset': self._reset,
        }

    def _reset(self, message: Message) -> None:
        if message.get('confirm') != RESET_CONFIRMATION:
            raise GameError(f'Type {RESET_CONFIRMATION} to confirm.')
        self.state = GameState()


def _everyone(_connection: Connection) -> bool:
    return True


def _show_and_host(connection: Connection) -> bool:
    return connection.role != 'play'


def _only(actor: Connection) -> Audience:
    def audience(connection: Connection) -> bool:
        return connection is actor
    return audience
