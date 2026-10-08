from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.game.models import GameState, Player

OVERALL_BOARD_SIZE = 10
PODIUM_SIZE = 3
PointsOf = Callable[[Player], int]


def active_players(state: GameState) -> list[Player]:
    return [player for player in state.players.values() if not player.kicked]


def total_points(player: Player) -> int:
    return player.total


def predictor_points(player: Player) -> int:
    return player.predict_points


def hacker_points(player: Player) -> int:
    return player.hack_points


def ranked_by(state: GameState, points_of: PointsOf) -> list[Player]:
    return sorted(active_players(state), key=lambda player: (-points_of(player), player.name.lower()))


def scorers(state: GameState, points_of: PointsOf, limit: int) -> list[Player]:
    return [player for player in ranked_by(state, points_of) if points_of(player) > 0][:limit]


def board(state: GameState, points_of: PointsOf, limit: int) -> list[dict[str, Any]]:
    return [{'name': player.name, 'points': points_of(player)} for player in scorers(state, points_of, limit)]


def finishers(state: GameState) -> list[Player]:
    return [state.players[player_id] for player_id in state.race_finishers if not state.players[player_id].kicked]


def fastest_builders(state: GameState, limit: int = PODIUM_SIZE) -> list[dict[str, Any]]:
    started_at = state.race_started_at or 0.0
    return [
        {'name': player.name, 'seconds': round((player.race_finished_at or started_at) - started_at)}
        for player in finishers(state)[:limit]
    ]


def overall_ranks(state: GameState) -> dict[str, int]:
    return {player.id: index + 1 for index, player in enumerate(ranked_by(state, total_points))}


def all_boards(state: GameState) -> dict[str, list[dict[str, Any]]]:
    return {
        'overall': board(state, total_points, OVERALL_BOARD_SIZE),
        'predictor': board(state, predictor_points, PODIUM_SIZE),
        'hacker': board(state, hacker_points, PODIUM_SIZE),
        'builder': fastest_builders(state),
    }


def podium_ids(state: GameState) -> dict[str, list[str]]:
    return {
        'overall': [player.id for player in scorers(state, total_points, PODIUM_SIZE)],
        'predictor': [player.id for player in scorers(state, predictor_points, PODIUM_SIZE)],
        'hacker': [player.id for player in scorers(state, hacker_points, PODIUM_SIZE)],
        'builder': [player.id for player in finishers(state)[:PODIUM_SIZE]],
    }
