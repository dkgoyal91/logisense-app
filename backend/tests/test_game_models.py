from app.game.models import GameState, Phase, Player


def test_player_total_sums_every_category() -> None:
    player = Player(id='p', token='t', name='Ada', predict_points=100, hack_points=50, race_points=3000, demo_points=500)
    assert player.total == 3650


def test_new_game_starts_in_lobby_without_players() -> None:
    state = GameState()
    assert state.phase is Phase.LOBBY
    assert state.question_index == -1
    assert state.players == {}
