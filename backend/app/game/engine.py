"""Deterministic game rules. Functions mutate the given state; time and ids are injected by the caller."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.game import scoring
from app.game.models import (
    OPTIONS_PER_QUESTION,
    Answer,
    Attack,
    BonusQuestion,
    GameError,
    GameState,
    Phase,
    Player,
    Question,
    Verdict,
)
from app.game.sanitize import clean_free_text, clean_name, unique_name

ANSWER_GRACE_SECONDS = 1.5
REMOVED_MESSAGE = 'You were removed by the host.'
MAX_PLAYERS = 500
ATTACK_COOLDOWN_SECONDS = 3.0
MAX_ATTACK_LENGTH = 200
MAX_BONUS_LENGTH = 120
MAX_BONUS_QUESTIONS_PER_PLAYER = 2

CopilotRunner = Callable[[str], dict[str, Any]]
Classifier = Callable[[str], Verdict]
Transition = Callable[[GameState, int, float], None]


# Players ---------------------------------------------------------------------------------

def join(state: GameState, raw_name: str, token: str | None, new_id: str, new_token: str) -> Player:
    existing = _player_by_token(state, token)
    if existing is not None:
        return _ensure_not_kicked(existing)
    return _add_player(state, raw_name, new_id, new_token)


def kick(state: GameState, player_id: str) -> None:
    _lookup_player(state, player_id).kicked = True


def award_demo(state: GameState, player_id: str) -> None:
    player = _lookup_player(state, player_id)
    if player.demo_points:
        raise GameError(f'{player.name} already has demo points.')
    player.demo_points = scoring.DEMO_POINTS


def _add_player(state: GameState, raw_name: str, new_id: str, new_token: str) -> Player:
    if len(state.players) >= MAX_PLAYERS:
        raise GameError('The game is full.')
    taken = {player.name for player in state.players.values()}
    player = Player(id=new_id, token=new_token, name=unique_name(clean_name(raw_name), taken))
    state.players[player.id] = player
    return player


def _player_by_token(state: GameState, token: str | None) -> Player | None:
    if not token:
        return None
    return next((player for player in state.players.values() if player.token == token), None)


def _lookup_player(state: GameState, player_id: str) -> Player:
    player = state.players.get(player_id)
    if player is None:
        raise GameError('Unknown player.')
    return player


def _require_player(state: GameState, player_id: str | None) -> Player:
    if not player_id or player_id not in state.players:
        raise GameError('Join the game first.')
    return _ensure_not_kicked(state.players[player_id])


def _ensure_not_kicked(player: Player) -> Player:
    if player.kicked:
        raise GameError(REMOVED_MESSAGE)
    return player


# Flow ------------------------------------------------------------------------------------

def advance(state: GameState, question_count: int, now: float) -> None:
    transition = _NEXT_TRANSITIONS.get(state.phase)
    if transition is None:
        raise GameError(_cannot(state, 'go next'))
    transition(state, question_count, now)


def skip(state: GameState, question_count: int, now: float) -> None:
    if state.phase is Phase.QUESTION_OPEN:
        state.phase = Phase.QUESTION_REVEALED
        return
    if state.phase is Phase.RACE_PODIUM:
        state.phase = Phase.FINALE
        return
    advance(state, question_count, now)


def toggle_hands_mode(state: GameState) -> None:
    state.hands_mode = not state.hands_mode


def _open_first_question(state: GameState, _question_count: int, now: float) -> None:
    _open_question(state, 0, now)


def _after_reveal(state: GameState, question_count: int, now: float) -> None:
    next_index = state.question_index + 1
    if next_index < question_count:
        _open_question(state, next_index, now)
    else:
        state.phase = Phase.BREAK_IT_OPEN


def _open_question(state: GameState, index: int, now: float) -> None:
    state.phase = Phase.QUESTION_OPEN
    state.question_index = index
    state.question_opened_at = now
    state.answers[index] = {}


def _move_to(phase: Phase) -> Transition:
    def transition(state: GameState, _question_count: int, _now: float) -> None:
        state.phase = phase
    return transition


_NEXT_TRANSITIONS: dict[Phase, Transition] = {
    Phase.LOBBY: _open_first_question,
    Phase.QUESTION_REVEALED: _after_reveal,
    Phase.BREAK_IT_OPEN: _move_to(Phase.BREAK_IT_CLOSED),
    Phase.BREAK_IT_CLOSED: _move_to(Phase.RACE_PODIUM),
    Phase.RACE_PODIUM: _move_to(Phase.BONUS),
    Phase.BONUS: _move_to(Phase.FINALE),
}


def _require_phase(state: GameState, phase: Phase, action: str) -> None:
    if state.phase is not phase:
        raise GameError(_cannot(state, action))


def _cannot(state: GameState, action: str) -> str:
    return f'Cannot {action} during {state.phase.value}.'


# Round 1: predictions --------------------------------------------------------------------

def submit_answer(state: GameState, player_id: str | None, option: int, now: float) -> None:
    _require_phase(state, Phase.QUESTION_OPEN, 'answer')
    player = _require_player(state, player_id)
    answers = state.answers[state.question_index]
    _check_answer_allowed(state, player, answers, option, now)
    answers[player.id] = Answer(option=option, elapsed=_seconds_since_open(state, now))


def reveal(state: GameState, questions: list[Question], run_copilot: CopilotRunner) -> None:
    _require_phase(state, Phase.QUESTION_OPEN, 'reveal')
    question = questions[state.question_index]
    state.copilot_results[state.question_index] = run_copilot(question.copilot_prompt)
    _score_answers(state, question.correct_index)
    state.phase = Phase.QUESTION_REVEALED


def _check_answer_allowed(state: GameState, player: Player, answers: dict[str, Answer], option: int, now: float) -> None:
    if player.id in answers:
        raise GameError('You already answered.')
    if not 0 <= option < OPTIONS_PER_QUESTION:
        raise GameError('Unknown option.')
    if _seconds_since_open(state, now) > scoring.QUESTION_WINDOW_SECONDS + ANSWER_GRACE_SECONDS:
        raise GameError("Time's up!")


def _seconds_since_open(state: GameState, now: float) -> float:
    opened_at = state.question_opened_at
    return 0.0 if opened_at is None else now - opened_at


def _score_answers(state: GameState, correct_index: int) -> None:
    answers = state.answers[state.question_index]
    for player in state.players.values():
        _score_answer(player, answers.get(player.id), correct_index)


def _score_answer(player: Player, answer: Answer | None, correct_index: int) -> None:
    if answer is None or answer.option != correct_index:
        player.streak = 0
        return
    player.streak += 1
    answer.points = scoring.prediction_points(answer.elapsed) + scoring.streak_bonus(player.streak)
    player.predict_points += answer.points


# Round 2: Break It -----------------------------------------------------------------------

def submit_attack(
    state: GameState, player_id: str | None, raw_text: str, classify: Classifier, attack_id: str, now: float,
) -> Attack:
    _require_phase(state, Phase.BREAK_IT_OPEN, 'attack')
    player = _require_player(state, player_id)
    _check_attack_cooldown(player, now)
    text = clean_free_text(raw_text, MAX_ATTACK_LENGTH)
    verdict = classify(text)
    attack = Attack(id=attack_id, player_id=player.id, text=text, layer=verdict.layer, message=verdict.message)
    state.attacks.append(attack)
    _record_attack_points(player, now)
    return attack


def star_attack(state: GameState, attack_id: str) -> None:
    attack = _lookup_attack(state, attack_id)
    if attack.starred:
        raise GameError('That attack is already starred.')
    attack.starred = True
    state.players[attack.player_id].hack_points += scoring.STAR_ATTACK_POINTS


def _check_attack_cooldown(player: Player, now: float) -> None:
    if player.last_attack_at is not None and now - player.last_attack_at < ATTACK_COOLDOWN_SECONDS:
        raise GameError(f'Slow down: one attack every {ATTACK_COOLDOWN_SECONDS:g} seconds.')


def _record_attack_points(player: Player, now: float) -> None:
    player.last_attack_at = now
    if player.attacks_scored < scoring.MAX_SCORED_ATTACKS:
        player.attacks_scored += 1
        player.hack_points += scoring.ATTACK_POINTS


def _lookup_attack(state: GameState, attack_id: str) -> Attack:
    attack = next((candidate for candidate in state.attacks if candidate.id == attack_id), None)
    if attack is None:
        raise GameError('Unknown attack.')
    return attack


# Build race ------------------------------------------------------------------------------

def start_race(state: GameState, now: float) -> None:
    if state.race_started_at is not None:
        raise GameError('The build race has already started.')
    if state.phase is Phase.FINALE:
        raise GameError(_cannot(state, 'start the race'))
    state.race_started_at = now


def finish_race(state: GameState, player_id: str | None, now: float) -> None:
    player = _require_player(state, player_id)
    _check_race_open(state, player)
    player.race_finished_at = now
    state.race_finishers.append(player.id)
    player.race_points = scoring.race_points(len(state.race_finishers))


def _check_race_open(state: GameState, player: Player) -> None:
    if state.race_started_at is None:
        raise GameError('The build race has not started yet.')
    if state.phase is Phase.FINALE:
        raise GameError('The build race is over.')
    if player.race_finished_at is not None:
        raise GameError('You already finished!')


# Bonus: Ask Anything ---------------------------------------------------------------------

def submit_bonus_question(state: GameState, player_id: str | None, raw_text: str, question_id: str) -> BonusQuestion:
    _require_phase(state, Phase.BONUS, 'ask a question')
    player = _require_player(state, player_id)
    _check_bonus_quota(state, player)
    question = BonusQuestion(
        id=question_id, player_id=player.id, text=clean_free_text(raw_text, MAX_BONUS_LENGTH), voters=[player.id],
    )
    state.bonus_questions.append(question)
    return question


def vote_bonus(state: GameState, player_id: str | None, question_id: str) -> None:
    _require_phase(state, Phase.BONUS, 'vote')
    player = _require_player(state, player_id)
    question = _lookup_bonus_question(state, question_id)
    if player.id in question.voters:
        raise GameError('You already voted for that one.')
    question.voters.append(player.id)


def answer_bonus(state: GameState, question_id: str, run_copilot: CopilotRunner) -> None:
    _require_phase(state, Phase.BONUS, 'ask the copilot')
    question = _lookup_bonus_question(state, question_id)
    state.bonus_answer = {'question_id': question.id, 'text': question.text, **run_copilot(question.text)}


def _check_bonus_quota(state: GameState, player: Player) -> None:
    asked = sum(1 for question in state.bonus_questions if question.player_id == player.id)
    if asked >= MAX_BONUS_QUESTIONS_PER_PLAYER:
        raise GameError(f'You can ask up to {MAX_BONUS_QUESTIONS_PER_PLAYER} questions.')


def _lookup_bonus_question(state: GameState, question_id: str) -> BonusQuestion:
    question = next((candidate for candidate in state.bonus_questions if candidate.id == question_id), None)
    if question is None:
        raise GameError('Unknown question.')
    return question


# Takeaway email --------------------------------------------------------------------------

TAKEAWAY_IN_PROGRESS_OR_DONE = ('queued', 'sent', 'saved')


def request_takeaway(state: GameState, player_id: str | None, email_hint: str) -> Player:
    player = _require_player(state, player_id)
    if player.takeaway_status in TAKEAWAY_IN_PROGRESS_OR_DONE:
        raise GameError('Your email is already on its way.')
    player.takeaway_status = 'queued'
    player.takeaway_hint = email_hint
    return player


def record_takeaway_result(state: GameState, player_id: str, status: str) -> None:
    player = state.players.get(player_id)
    if player is not None:
        player.takeaway_status = status
