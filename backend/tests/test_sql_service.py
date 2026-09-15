from app.database import initialize_database
from app.sql_service import execute_safe_query


def test_database_initializes_with_realistic_logistics_rows() -> None:
    initialize_database()
    result = execute_safe_query('Which logistics pipeline records have a review date in 2025?')

    assert result['table'] == 'opportunities'
    assert result['rows']
    assert len(result['rows']) <= 20
    assert any('2025' in str(row.get('review_date', '')) for row in result['rows'])


def test_safe_query_handles_operations_lead_filter() -> None:
    initialize_database()
    result = execute_safe_query('Show only logistics pipeline records managed by James Harris')

    assert result['table'] == 'opportunities'
    assert result['rows']
    assert all(row['operations_lead'] == 'James Harris' for row in result['rows'])
