import pytest

from app.game import engine
from app.game.models import GameError, GameState, Phase, Question
from game_support import QUESTIONS, fake_copilot, joined_state


def test_join_dedupes_names_and_rejoin_by_token_returns_same_player() -> None:
    state = GameState()
    first = engine.join(state, 'Ada', None, 'id1', 'tok1')
    second = engine.join(state, 'ada', None, 'id2', 'tok2')
    again = engine.join(state, 'Whatever', 'tok1', 'id3', 'tok3')
    assert second.name == 'ada2'
    assert again is first
    assert len(state.players) == 2


def test_unknown_token_joins_as_new_player() -> None:
    state = GameState()
    player = engine.join(state, 'Ada', 'stale-token', 'id1', 'tok1')
    assert player.token == 'tok1'


def test_kicked_player_cannot_rejoin_or_answer() -> None:
    state, (ada,) = joined_state('Ada')
    engine.kick(state, ada)
    with pytest.raises(GameError, match='removed'):
        engine.join(state, 'Ada', 'tok-Ada', 'x', 'y')
    engine.advance(state, 2, now=0)
    with pytest.raises(GameError, match='removed'):
        engine.submit_answer(state, ada, 0, now=1)


def test_next_walks_through_every_phase() -> None:
    state = GameState()
    engine.advance(state, 2, now=0)
    assert (state.phase, state.question_index) == (Phase.QUESTION_OPEN, 0)
    engine.reveal(state, QUESTIONS, fake_copilot)
    engine.advance(state, 2, now=30)
    assert (state.phase, state.question_index) == (Phase.QUESTION_OPEN, 1)
    engine.reveal(state, QUESTIONS, fake_copilot)
    phases = []
    for _ in range(5):
        engine.advance(state, 2, now=60)
        phases.append(state.phase)
    assert phases == [Phase.BREAK_IT_OPEN, Phase.BREAK_IT_CLOSED, Phase.RACE_PODIUM, Phase.BONUS, Phase.FINALE]
    with pytest.raises(GameError, match='Cannot go next during finale'):
        engine.advance(state, 2, now=60)


def test_double_tap_next_and_reveal_are_rejected() -> None:
    state = GameState()
    engine.advance(state, 2, now=0)
    with pytest.raises(GameError):
        engine.advance(state, 2, now=0)
    engine.reveal(state, QUESTIONS, fake_copilot)
    with pytest.raises(GameError):
        engine.reveal(state, QUESTIONS, fake_copilot)
    assert state.question_index == 0


def test_reveal_scores_correct_answers_and_resets_streak_on_miss() -> None:
    state, (ada, bob) = joined_state('Ada', 'Bob')
    engine.advance(state, 2, now=100)
    engine.submit_answer(state, ada, 2, now=105)
    engine.submit_answer(state, bob, 1, now=101)
    engine.reveal(state, QUESTIONS, fake_copilot)
    assert state.players[ada].predict_points == 875
    assert state.players[ada].streak == 1
    assert state.players[bob].predict_points == 0
    assert state.players[bob].streak == 0
    assert state.copilot_results[0]['prompt_seen'] == 'prompt one'


def test_streak_bonus_applies_from_third_correct_answer() -> None:
    questions = [Question(f'p{index}', 't', 'c', ('A', 'B', 'C', 'D'), 0) for index in range(3)]
    state, (ada,) = joined_state('Ada')
    for _ in questions:
        engine.advance(state, 3, now=0)
        engine.submit_answer(state, ada, 0, now=0)
        engine.reveal(state, questions, fake_copilot)
    assert state.players[ada].predict_points == 3 * 1000 + 200


def test_answer_rules_reject_duplicates_bad_options_and_late_answers() -> None:
    state, (ada, bob, cat) = joined_state('Ada', 'Bob', 'Cat')
    engine.advance(state, 2, now=0)
    engine.submit_answer(state, ada, 0, now=1)
    with pytest.raises(GameError, match='already answered'):
        engine.submit_answer(state, ada, 1, now=2)
    with pytest.raises(GameError, match='Unknown option'):
        engine.submit_answer(state, bob, 4, now=2)
    with pytest.raises(GameError, match="Time's up"):
        engine.submit_answer(state, cat, 0, now=22)
    engine.submit_answer(state, bob, 0, now=21)
    assert set(state.answers[0]) == {ada, bob}


def test_answers_need_an_open_question_and_a_joined_player() -> None:
    state, (ada,) = joined_state('Ada')
    with pytest.raises(GameError, match='Cannot answer during lobby'):
        engine.submit_answer(state, ada, 0, now=0)
    engine.advance(state, 2, now=0)
    with pytest.raises(GameError, match='Join the game first'):
        engine.submit_answer(state, None, 0, now=0)


def test_skip_closes_question_without_points_and_skips_bonus() -> None:
    state, (ada,) = joined_state('Ada')
    engine.advance(state, 2, now=0)
    engine.submit_answer(state, ada, 2, now=0)
    engine.skip(state, 2, now=1)
    assert state.phase is Phase.QUESTION_REVEALED
    assert state.players[ada].predict_points == 0
    state.phase = Phase.RACE_PODIUM
    engine.skip(state, 2, now=2)
    assert state.phase is Phase.FINALE


def test_hands_mode_toggles() -> None:
    state = GameState()
    engine.toggle_hands_mode(state)
    assert state.hands_mode is True
    engine.toggle_hands_mode(state)
    assert state.hands_mode is False


def test_award_demo_once_per_player() -> None:
    state, (ada,) = joined_state('Ada')
    engine.award_demo(state, ada)
    assert state.players[ada].demo_points == 500
    with pytest.raises(GameError, match='already has demo points'):
        engine.award_demo(state, ada)
