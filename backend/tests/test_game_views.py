from app.game import engine, views
from app.game.models import GameState, Phase, Verdict
from game_support import QUESTIONS, fake_copilot, joined_state

JOIN_URL = 'https://example.test/play'


def _ctx(state: GameState, now: float = 0.0) -> views.ViewContext:
    return views.build_context(state, QUESTIONS, now, JOIN_URL)


def _verdict(_text: str) -> Verdict:
    return Verdict('validator', 'blocked')


def test_open_question_hides_the_answer_and_counts_votes() -> None:
    state, (ada,) = joined_state('Ada')
    engine.advance(state, 2, now=100)
    engine.submit_answer(state, ada, 1, now=104)
    view = views.show_view(_ctx(state, now=105))
    assert view['question']['seconds_left'] == 15.0
    assert view['question']['answered_count'] == 1
    assert 'correct_index' not in view['question']
    assert view['reveal'] is None
    assert views.player_view(_ctx(state), ada)['my_answer'] == 1


def test_reveal_shows_distribution_copilot_and_player_result() -> None:
    state, (ada, bob) = joined_state('Ada', 'Bob')
    engine.advance(state, 2, now=100)
    engine.submit_answer(state, ada, 2, now=100)
    engine.submit_answer(state, bob, 0, now=100)
    engine.reveal(state, QUESTIONS, fake_copilot)
    show = views.show_view(_ctx(state, now=101))
    assert show['reveal']['distribution'] == [1, 0, 1, 0]
    assert show['reveal']['correct_index'] == 2
    assert show['reveal']['copilot']['table'] == 'jobs'
    ada_view = views.player_view(_ctx(state), ada)
    assert ada_view['result'] == {'answered': True, 'correct': True, 'points': 1000, 'correct_option': 'C'}
    assert ada_view['me']['rank'] == 1
    assert views.player_view(_ctx(state), bob)['result']['correct'] is False


def test_unknown_player_gets_an_anonymous_view() -> None:
    view = views.player_view(_ctx(GameState()), 'nobody')
    assert view['me'] is None
    assert view['my_attacks'] == []
    assert view['awards'] == []


def test_host_view_adds_roster_and_answer_key() -> None:
    state, _ids = joined_state('Ada')
    engine.advance(state, 2, now=0)
    host = views.host_view(_ctx(state))
    assert host['players'][0]['name'] == 'Ada'
    assert host['join_url'] == JOIN_URL
    engine.reveal(state, QUESTIONS, fake_copilot)
    assert views.host_view(_ctx(state))['answer_key'] == 'C'


def test_host_answer_key_stays_hidden_until_reveal() -> None:
    state, _ids = joined_state('Ada')
    engine.advance(state, 2, now=0)
    assert views.host_view(_ctx(state))['answer_key'] is None


def test_attack_feed_is_newest_first_and_hides_kicked_players() -> None:
    state, (ada, bob) = joined_state('Ada', 'Bob')
    state.phase = Phase.BREAK_IT_OPEN
    engine.submit_attack(state, ada, 'first', _verdict, 'a1', now=0)
    engine.submit_attack(state, bob, 'rude', _verdict, 'b1', now=0)
    engine.submit_attack(state, ada, 'second', _verdict, 'a2', now=5)
    engine.kick(state, bob)
    feed = views.show_view(_ctx(state))['attacks']
    assert [attack['text'] for attack in feed] == ['second', 'first']
    assert [attack['text'] for attack in views.player_view(_ctx(state), ada)['my_attacks']] == ['second', 'first']


def test_awards_list_every_podium_category() -> None:
    state, (ada,) = joined_state('Ada')
    state.players[ada].predict_points = 900
    state.phase = Phase.FINALE
    awards = views.player_view(_ctx(state), ada)['awards']
    assert {'category': 'overall', 'place': 1} in awards
    assert {'category': 'predictor', 'place': 1} in awards


def test_bonus_only_in_bonus_phase_and_marks_votes() -> None:
    state, (ada, bob) = joined_state('Ada', 'Bob')
    assert views.show_view(_ctx(state))['bonus'] is None
    state.phase = Phase.BONUS
    engine.submit_bonus_question(state, ada, 'Show delayed shipments', 'q1')
    bob_bonus = views.player_view(_ctx(state), bob)['bonus']
    assert bob_bonus['questions'][0] == {
        'id': 'q1', 'text': 'Show delayed shipments', 'name': 'Ada', 'votes': 1, 'voted': False, 'mine': False,
    }
