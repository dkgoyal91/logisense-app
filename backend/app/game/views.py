"""Role-specific projections of the game. Shared, expensive work happens once per broadcast in build_context."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from app.game import leaderboard
from app.game.models import OPTIONS_PER_QUESTION, Answer, Attack, BonusQuestion, GameState, Phase, Player, Question
from app.game.scoring import QUESTION_WINDOW_SECONDS

LOBBY_NAME_LIMIT = 60
ATTACK_FEED_LIMIT = 30
MY_ATTACK_LIMIT = 5
BONUS_BOARD_LIMIT = 8
RACE_FINISHER_LIMIT = 10
QUESTION_PHASES = (Phase.QUESTION_OPEN, Phase.QUESTION_REVEALED)

View = dict[str, Any]


@dataclass(frozen=True)
class ViewContext:
    state: GameState
    questions: list[Question]
    now: float
    join_url: str
    ranks: dict[str, int]
    boards: dict[str, list[dict[str, Any]]]
    podium_ids: dict[str, list[str]]


def build_context(state: GameState, questions: list[Question], now: float, join_url: str) -> ViewContext:
    return ViewContext(
        state=state,
        questions=questions,
        now=now,
        join_url=join_url,
        ranks=leaderboard.overall_ranks(state),
        boards=leaderboard.all_boards(state),
        podium_ids=leaderboard.podium_ids(state),
    )


def show_view(ctx: ViewContext) -> View:
    return {
        'phase': ctx.state.phase.value,
        'hands_mode': ctx.state.hands_mode,
        'join_url': ctx.join_url,
        'lobby': _lobby(ctx.state),
        'question': _question(ctx),
        'reveal': _reveal(ctx),
        'race': _race(ctx),
        'attacks': _attack_feed(ctx.state),
        'boards': ctx.boards,
        'bonus': _bonus(ctx.state, viewer_id=None),
    }


def host_view(ctx: ViewContext) -> View:
    return {**show_view(ctx), 'players': _roster(ctx.state), 'answer_key': _answer_key(ctx),
            'takeaway_counts': _takeaway_counts(ctx.state)}


def player_view(ctx: ViewContext, player_id: str | None) -> View:
    player = ctx.state.players.get(player_id) if player_id else None
    if player is None:
        return _anonymous_player_view(ctx)
    return {
        'phase': ctx.state.phase.value,
        'me': _me(ctx, player),
        'question': _question(ctx),
        'my_answer': _my_answer(ctx.state, player),
        'result': _my_result(ctx, player),
        'my_attacks': _my_attacks(ctx.state, player),
        'race_started': ctx.state.race_started_at is not None,
        'bonus': _bonus(ctx.state, viewer_id=player.id),
        'awards': _awards(ctx, player.id),
    }


def _anonymous_player_view(ctx: ViewContext) -> View:
    return {
        'phase': ctx.state.phase.value,
        'me': None,
        'question': None,
        'my_answer': None,
        'result': None,
        'my_attacks': [],
        'race_started': ctx.state.race_started_at is not None,
        'bonus': None,
        'awards': [],
    }


# Lobby and questions ---------------------------------------------------------------------

def _lobby(state: GameState) -> View:
    names = [player.name for player in leaderboard.active_players(state)]
    return {'count': len(names), 'names': names[-LOBBY_NAME_LIMIT:]}


def _current_question(ctx: ViewContext) -> Question | None:
    if ctx.state.phase not in QUESTION_PHASES:
        return None
    return ctx.questions[ctx.state.question_index]


def _current_answers(state: GameState) -> dict[str, Answer]:
    return state.answers.get(state.question_index, {})


def _question(ctx: ViewContext) -> View | None:
    question = _current_question(ctx)
    if question is None:
        return None
    return {
        'index': ctx.state.question_index,
        'total': len(ctx.questions),
        'text': question.text,
        'copilot_prompt': question.copilot_prompt,
        'concept': question.concept,
        'options': list(question.options),
        'seconds_left': _seconds_left(ctx),
        'answered_count': len(_current_answers(ctx.state)),
    }


def _seconds_left(ctx: ViewContext) -> float:
    opened_at = ctx.state.question_opened_at
    if ctx.state.phase is not Phase.QUESTION_OPEN or opened_at is None:
        return 0.0
    return round(max(0.0, QUESTION_WINDOW_SECONDS - (ctx.now - opened_at)), 1)


def _reveal(ctx: ViewContext) -> View | None:
    question = _current_question(ctx)
    if question is None or ctx.state.phase is not Phase.QUESTION_REVEALED:
        return None
    return {
        'correct_index': question.correct_index,
        'distribution': _distribution(_current_answers(ctx.state)),
        'copilot': ctx.state.copilot_results.get(ctx.state.question_index),
    }


def _distribution(answers: dict[str, Answer]) -> list[int]:
    counts = Counter(answer.option for answer in answers.values())
    return [counts.get(option, 0) for option in range(OPTIONS_PER_QUESTION)]


def _answer_key(ctx: ViewContext) -> str | None:
    question = _current_question(ctx)
    return None if question is None else question.options[question.correct_index]


# Race, attacks, bonus --------------------------------------------------------------------

def _race(ctx: ViewContext) -> View:
    started_at = ctx.state.race_started_at
    return {
        'started': started_at is not None,
        'elapsed_seconds': 0 if started_at is None else round(ctx.now - started_at),
        'finishers': leaderboard.fastest_builders(ctx.state, limit=RACE_FINISHER_LIMIT),
    }


def _attack_feed(state: GameState) -> list[View]:
    visible = [attack for attack in state.attacks if not state.players[attack.player_id].kicked]
    return [_attack_entry(state, attack) for attack in reversed(visible[-ATTACK_FEED_LIMIT:])]


def _attack_entry(state: GameState, attack: Attack) -> View:
    return {**_attack_summary(attack), 'name': state.players[attack.player_id].name}


def _attack_summary(attack: Attack) -> View:
    return {'id': attack.id, 'text': attack.text, 'layer': attack.layer, 'message': attack.message, 'starred': attack.starred}


def _my_attacks(state: GameState, player: Player) -> list[View]:
    mine = [attack for attack in state.attacks if attack.player_id == player.id][-MY_ATTACK_LIMIT:]
    return [_attack_summary(attack) for attack in reversed(mine)]


def _bonus(state: GameState, viewer_id: str | None) -> View | None:
    if state.phase is not Phase.BONUS:
        return None
    visible = [question for question in state.bonus_questions if not state.players[question.player_id].kicked]
    ranked = sorted(visible, key=lambda question: -len(question.voters))[:BONUS_BOARD_LIMIT]
    return {'questions': [_bonus_entry(state, question, viewer_id) for question in ranked], 'answer': state.bonus_answer}


def _bonus_entry(state: GameState, question: BonusQuestion, viewer_id: str | None) -> View:
    return {
        'id': question.id,
        'text': question.text,
        'name': state.players[question.player_id].name,
        'votes': len(question.voters),
        'voted': viewer_id in question.voters,
        'mine': question.player_id == viewer_id,
    }


# Players ---------------------------------------------------------------------------------

def _me(ctx: ViewContext, player: Player) -> View:
    return {
        'id': player.id,
        'name': player.name,
        'token': player.token,
        'total': player.total,
        'rank': ctx.ranks.get(player.id),
        'race_done': player.race_finished_at is not None,
        'kicked': player.kicked,
        'takeaway': _takeaway(player),
    }


def _takeaway(player: Player) -> View | None:
    if player.takeaway_status is None:
        return None
    return {'status': player.takeaway_status, 'email_hint': player.takeaway_hint}


def _takeaway_counts(state: GameState) -> dict[str, int]:
    return dict(Counter(p.takeaway_status for p in state.players.values() if p.takeaway_status))


def _my_answer(state: GameState, player: Player) -> int | None:
    if state.phase not in QUESTION_PHASES:
        return None
    answer = _current_answers(state).get(player.id)
    return None if answer is None else answer.option


def _my_result(ctx: ViewContext, player: Player) -> View | None:
    question = _current_question(ctx)
    if question is None or ctx.state.phase is not Phase.QUESTION_REVEALED:
        return None
    answer = _current_answers(ctx.state).get(player.id)
    return {
        'answered': answer is not None,
        'correct': answer is not None and answer.option == question.correct_index,
        'points': 0 if answer is None else answer.points,
        'correct_option': question.options[question.correct_index],
    }


def _awards(ctx: ViewContext, player_id: str) -> list[View]:
    return [
        {'category': category, 'place': ids.index(player_id) + 1}
        for category, ids in ctx.podium_ids.items()
        if player_id in ids
    ]


def _roster(state: GameState) -> list[View]:
    players = sorted(state.players.values(), key=lambda player: player.name.lower())
    return [
        {
            'id': player.id,
            'name': player.name,
            'total': player.total,
            'kicked': player.kicked,
            'race_done': player.race_finished_at is not None,
            'demo_awarded': player.demo_points > 0,
        }
        for player in players
    ]
