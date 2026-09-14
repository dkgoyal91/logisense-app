from app.database import initialize_database
from app.sql_service import execute_safe_query


def test_database_initializes_with_realistic_logistics_rows() -> None:
    initialize_database()
    result = execute_safe_query('Which projects have a valuation date in 2025?')

    assert result['table'] == 'opportunities'
    assert result['rows']
    assert len(result['rows']) <= 20
    assert any('2025' in str(row.get('valuation_date', '')) for row in result['rows'])


def test_safe_query_handles_job_director_filter() -> None:
    initialize_database()
    result = execute_safe_query('Show only opportunities managed by James Harris')

    assert result['table'] == 'opportunities'
    assert result['rows']
    assert all(row['job_director'] == 'James Harris' for row in result['rows'])
