import pytest

from app.game import engine
from app.game.models import GameError, Phase, Verdict
from game_support import fake_copilot, joined_state


def blocked(text: str) -> Verdict:
    return Verdict('validator', f'blocked {text}')


def _in_phase(phase: Phase, *names: str):
    state, ids = joined_state(*names)
    state.phase = phase
    return state, ids


def test_attacks_are_cleaned_classified_and_scored_up_to_five() -> None:
    state, (ada,) = _in_phase(Phase.BREAK_IT_OPEN, 'Ada')
    for index in range(6):
        engine.submit_attack(state, ada, f' drop   {index} ', blocked, f'a{index}', now=index * 3)
    assert state.attacks[0].text == 'drop 0'
    assert state.attacks[0].message == 'blocked drop 0'
    assert len(state.attacks) == 6
    assert state.players[ada].hack_points == 250


def test_attack_cooldown_rejects_spam() -> None:
    state, (ada,) = _in_phase(Phase.BREAK_IT_OPEN, 'Ada')
    engine.submit_attack(state, ada, 'one', blocked, 'a1', now=10)
    with pytest.raises(GameError, match='Slow down'):
        engine.submit_attack(state, ada, 'two', blocked, 'a2', now=12)


def test_attacks_only_while_break_it_is_open() -> None:
    state, (ada,) = _in_phase(Phase.BREAK_IT_CLOSED, 'Ada')
    with pytest.raises(GameError, match='Cannot attack during break_it_closed'):
        engine.submit_attack(state, ada, 'one', blocked, 'a1', now=10)


def test_star_attack_awards_owner_once() -> None:
    state, (ada,) = _in_phase(Phase.BREAK_IT_OPEN, 'Ada')
    engine.submit_attack(state, ada, 'one', blocked, 'a1', now=10)
    engine.star_attack(state, 'a1')
    assert state.players[ada].hack_points == 1050
    with pytest.raises(GameError, match='already starred'):
        engine.star_attack(state, 'a1')
    with pytest.raises(GameError, match='Unknown attack'):
        engine.star_attack(state, 'nope')


def test_race_finish_order_awards_places() -> None:
    state, (ada, bob, cat, dan) = joined_state('Ada', 'Bob', 'Cat', 'Dan')
    engine.start_race(state, now=100)
    for offset, player_id in enumerate([cat, ada, dan, bob]):
        engine.finish_race(state, player_id, now=200 + offset)
    assert [state.players[pid].race_points for pid in (cat, ada, dan, bob)] == [3000, 2000, 1000, 500]
    assert state.race_finishers == [cat, ada, dan, bob]


def test_race_rules() -> None:
    state, (ada,) = joined_state('Ada')
    with pytest.raises(GameError, match='not started'):
        engine.finish_race(state, ada, now=1)
    engine.start_race(state, now=1)
    with pytest.raises(GameError, match='already started'):
        engine.start_race(state, now=2)
    engine.finish_race(state, ada, now=3)
    with pytest.raises(GameError, match='already finished'):
        engine.finish_race(state, ada, now=4)


def test_race_is_closed_at_finale() -> None:
    state, (ada,) = joined_state('Ada')
    engine.start_race(state, now=1)
    state.phase = Phase.FINALE
    with pytest.raises(GameError, match='race is over'):
        engine.finish_race(state, ada, now=2)


def test_bonus_questions_votes_and_answer() -> None:
    state, (ada, bob) = _in_phase(Phase.BONUS, 'Ada', 'Bob')
    question = engine.submit_bonus_question(state, ada, 'Show delayed shipments', 'q1')
    assert question.voters == [ada]
    engine.vote_bonus(state, bob, 'q1')
    with pytest.raises(GameError, match='already voted'):
        engine.vote_bonus(state, bob, 'q1')
    engine.submit_bonus_question(state, ada, 'Second question', 'q2')
    with pytest.raises(GameError, match='up to 2'):
        engine.submit_bonus_question(state, ada, 'Third question', 'q3')
    engine.answer_bonus(state, 'q1', fake_copilot)
    assert state.bonus_answer is not None
    assert state.bonus_answer['question_id'] == 'q1'
    assert state.bonus_answer['prompt_seen'] == 'Show delayed shipments'


def test_bonus_actions_need_bonus_phase() -> None:
    state, (ada,) = joined_state('Ada')
    with pytest.raises(GameError, match='Cannot ask a question during lobby'):
        engine.submit_bonus_question(state, ada, 'hello', 'q1')
