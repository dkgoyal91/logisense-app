from app.config import settings
from app.database import initialize_database
from app.game import reveal
from app.game.reveal import run_copilot


def test_run_copilot_returns_display_ready_result() -> None:
    initialize_database()
    result = run_copilot('List vehicles in maintenance')
    assert result['table'] == 'vehicles'
    assert 'WHERE status = ?' in result['sql']
    assert 0 < result['row_count'] <= settings.row_limit
    assert 0 < len(result['sample_rows']) <= 3
    assert 'latitude' not in result['sample_rows'][0]
    assert result['error'] is None


def test_run_copilot_reports_out_of_scope_questions() -> None:
    initialize_database()
    result = run_copilot("What's the CEO's salary?")
    assert result['table'] is None
    assert result['sql'] is None
    assert result['row_count'] == 0


def test_run_copilot_reports_validator_rejection(monkeypatch) -> None:
    def reject(_message: str) -> dict:
        raise ValueError('Unsafe SQL detected.')

    monkeypatch.setattr(reveal, 'execute_safe_query', reject)
    result = run_copilot('anything')
    assert result == {
        'table': None, 'sql': None, 'row_count': 0, 'sample_rows': [], 'summary': 'Blocked.', 'error': 'Unsafe SQL detected.',
    }
