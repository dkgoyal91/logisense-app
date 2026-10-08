from pathlib import Path

from app.config import BACKEND_DIR, resolve_backend_path
from app.game import engine
from app.game.models import Phase, Verdict
from app.game.persistence import SnapshotStore
from game_support import QUESTIONS, fake_copilot, joined_state


def test_snapshot_round_trip_preserves_the_whole_game(tmp_path: Path) -> None:
    state, (ada, bob) = joined_state('Ada', 'Bob')
    engine.start_race(state, now=5)
    engine.advance(state, 2, now=10)
    engine.submit_answer(state, ada, 2, now=12)
    engine.reveal(state, QUESTIONS, fake_copilot)
    state.phase = Phase.BREAK_IT_OPEN
    engine.submit_attack(state, bob, 'DROP TABLE x', lambda _text: Verdict('validator', 'no'), 'atk1', now=20)
    engine.finish_race(state, ada, now=30)
    store = SnapshotStore(tmp_path / 'snapshot.json')

    store.save(state)

    assert store.load() == state


def test_missing_or_unreadable_snapshot_starts_fresh(tmp_path: Path) -> None:
    assert SnapshotStore(tmp_path / 'missing.json').load() is None
    corrupt = tmp_path / 'corrupt.json'
    corrupt.write_text('{not json', encoding='utf-8')
    assert SnapshotStore(corrupt).load() is None
    partial = tmp_path / 'partial.json'
    partial.write_text('{"phase": "lobby"}', encoding='utf-8')
    assert SnapshotStore(partial).load() is None


def test_resolve_backend_path_anchors_relative_paths(tmp_path: Path) -> None:
    assert resolve_backend_path('data/x.json') == BACKEND_DIR / 'data/x.json'
    assert resolve_backend_path(str(tmp_path)) == tmp_path
