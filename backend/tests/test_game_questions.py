import pytest

from app.config import settings
from app.database import get_connection, initialize_database
from app.game.questions import (
    BLOCK_WITH_ERROR,
    QUESTION_SPECS,
    REFUSE,
    SAFE_SELECT,
    QuestionBuildError,
    ShipmentCounts,
    build_questions,
    load_shipment_counts,
)
from app.game.reveal import run_copilot


def _real_questions():
    initialize_database()
    with get_connection() as connection:
        counts = load_shipment_counts(connection)
    return build_questions(run_copilot, counts)


def test_questions_are_answered_by_the_real_copilot() -> None:
    questions = _real_questions()
    answers = [question.options[question.correct_index] for question in questions]
    assert answers == ['jobs', str(settings.row_limit), REFUSE, 'status', SAFE_SELECT]
    assert all(len(set(question.options)) == 4 for question in questions)


def test_question_option_order_is_deterministic() -> None:
    assert [q.options for q in _real_questions()] == [q.options for q in _real_questions()]


def test_colliding_row_count_options_fail_fast() -> None:
    def fake(_prompt: str) -> dict:
        return {'table': 'jobs', 'sql': 'SELECT x FROM jobs WHERE status = ?', 'row_count': 20, 'sample_rows': [], 'summary': '', 'error': None}

    with pytest.raises(QuestionBuildError, match='distinct'):
        build_questions(fake, ShipmentCounts(delayed=20, total=600))


def test_injection_question_reports_block_when_copilot_errors() -> None:
    blocked = {'table': None, 'sql': None, 'row_count': 0, 'sample_rows': [], 'summary': '', 'error': 'Unsafe SQL detected.'}
    _options, correct = QUESTION_SPECS[4].build_options(blocked, ShipmentCounts(delayed=132, total=660))
    assert correct == BLOCK_WITH_ERROR
