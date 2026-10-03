from app.game.leaderboard import all_boards, fastest_builders, overall_ranks, podium_ids
from app.game.models import GameState, Player


def _state(*players: Player) -> GameState:
    state = GameState()
    for player in players:
        state.players[player.id] = player
    return state


def test_overall_board_sorts_by_points_then_name_and_skips_kicked_and_zero() -> None:
    state = _state(
        Player('a', 'ta', 'Zed', predict_points=500),
        Player('b', 'tb', 'amy', predict_points=500),
        Player('c', 'tc', 'Cat', hack_points=900, kicked=True),
        Player('d', 'td', 'Dan'),
    )
    assert all_boards(state)['overall'] == [{'name': 'amy', 'points': 500}, {'name': 'Zed', 'points': 500}]


def test_fastest_builders_follow_finish_order() -> None:
    state = _state(Player('a', 'ta', 'Ada', race_finished_at=160.0), Player('b', 'tb', 'Bob', race_finished_at=130.0))
    state.race_started_at = 100.0
    state.race_finishers = ['b', 'a']
    assert fastest_builders(state) == [{'name': 'Bob', 'seconds': 30}, {'name': 'Ada', 'seconds': 60}]


def test_podium_ids_per_category() -> None:
    state = _state(Player('a', 'ta', 'Ada', predict_points=900), Player('b', 'tb', 'Bob', hack_points=300))
    state.race_started_at = 0.0
    state.race_finishers = ['b']
    assert podium_ids(state) == {'overall': ['a', 'b'], 'predictor': ['a'], 'hacker': ['b'], 'builder': ['b']}


def test_overall_ranks_are_one_based_and_exclude_kicked() -> None:
    state = _state(Player('a', 'ta', 'Ada', predict_points=10), Player('b', 'tb', 'Bob', predict_points=20), Player('k', 'tk', 'Kim', kicked=True))
    assert overall_ranks(state) == {'b': 1, 'a': 2}
