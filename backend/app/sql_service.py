from __future__ import annotations

import re
import sqlite3
from typing import Any

from app.config import settings
from app.database import get_connection

ALLOWED_TABLES: dict[str, set[str]] = {
    'logistics_records': {
        'record_ref',
        'client_name',
        'operations_lead',
        'logistics_owner',
        'route_count',
        'review_date',
        'status',
        'region',
        'value_usd',
    },
    'jobs': {
        'job_id',
        'record_ref',
        'client_name',
        'region',
        'status',
        'progress_pct',
        'days_open',
        'total_properties',
        'current_stage',
    },
    'shipments': {
        'shipment_id',
        'customer',
        'route',
        'origin',
        'destination',
        'source_location',
        'destination_location',
        'status',
        'route_start_date',
        'planned_delivery_date',
        'actual_delivery_date',
        'delivery_date',
        'weight_kg',
        'value_usd',
    },
    'vehicles': {
        'vehicle_id',
        'depot',
        'status',
        'utilization_pct',
        'last_service_date',
    },
}

TABLE_DEFAULT_ORDER: dict[str, str] = {
    'logistics_records': 'review_date DESC',
    'jobs': 'days_open DESC',
    'shipments': 'COALESCE(actual_delivery_date, planned_delivery_date, delivery_date) DESC',
    'vehicles': 'utilization_pct DESC',
}

# Columns exposed as dashboard filter dropdowns, restricted to low-cardinality categorical fields.
FILTERABLE_COLUMNS: dict[str, list[str]] = {
    'logistics_records': ['status', 'region'],
    'jobs': ['status', 'region', 'current_stage'],
    'shipments': ['status', 'source_location', 'destination_location'],
    'vehicles': ['status', 'depot'],
}

MAX_PAGE_SIZE = 200

READ_ONLY_SQL_PATTERN = re.compile(r'^\s*SELECT\b', re.IGNORECASE)
FORBIDDEN_SQL_PATTERN = re.compile(
    r'(?i)\b(drop|delete|update|insert|alter|truncate|grant|revoke|create|attach|detach|replace|execute|pragma|vacuum)\b'
)
TABLE_REFERENCE_PATTERN = re.compile(r'\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)', re.IGNORECASE)

# Approximate UK city centroids used to plot map markers for location-bearing rows.
CITY_COORDINATES: dict[str, tuple[float, float]] = {
    'london': (51.5072, -0.1276),
    'manchester': (53.4808, -2.2426),
    'birmingham': (52.4862, -1.8904),
    'leeds': (53.8008, -1.5491),
    'glasgow': (55.8642, -4.2518),
    'bristol': (51.4545, -2.5879),
    'edinburgh': (55.9533, -3.1883),
    'southampton': (50.9097, -1.4044),
}

LOCATION_COLUMN_BY_TABLE: dict[str, str] = {
    'shipments': 'destination_location',
    'logistics_records': 'region',
    'jobs': 'region',
    'vehicles': 'depot',
}


def _coordinates_for_location(location: str | None) -> tuple[float, float] | None:
    if not location:
        return None
    normalized = location.strip().lower()
    if normalized in CITY_COORDINATES:
        return CITY_COORDINATES[normalized]
    for city, coordinates in CITY_COORDINATES.items():
        if city in normalized:
            return coordinates
    return None


def _attach_coordinates(table_name: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    location_column = LOCATION_COLUMN_BY_TABLE.get(table_name)
    if not location_column:
        return rows

    for row in rows:
        coordinates = _coordinates_for_location(row.get(location_column))
        if coordinates:
            row['latitude'], row['longitude'] = coordinates
    return rows


def _extract_name(message: str) -> str | None:
    match = re.search(r"(?:managed by|operations lead|logistics owner|owned by|owner is|by\s+)([A-Z][A-Za-z' .-]+)", message, re.IGNORECASE)
    if not match:
        return None
    name = match.group(1).strip()
    return name if name else None


def _extract_record_ref(message: str) -> str | None:
    match = re.search(r'(?i)\b(?:record\s+ref|record\s+reference|ref)\b\s*["\']?([A-Za-z0-9-]+)["\']?', message)
    if not match:
        return None
    ref = match.group(1).strip()
    return ref if ref else None


def _extract_shipment_id(message: str) -> str | None:
    patterns = [
        r'(?i)\bshipment\s+id\s*[:=]?\s*([A-Z]+-\d+)\b',
        r'(?i)\bshipment\s+([A-Z]+-\d+)\b',
        r'(?i)\b(?:shipment|delivery)\s+(?:details?|info|record|data)\s+(?:for|of|on)\s*([A-Z]+-\d+)\b',
        r'(?i)\b(?:show|list|display|get|find|search)\s+(?:me\s+)?(?:detail|details)\s+(?:for|of|on)\s+(?:shipment|delivery)\s+([A-Z]+-\d+)\b',
        r'(?i)\b(?:show|list|display|get|find|search)\s+(?:me\s+)?(?:shipment|delivery)\s+([A-Z]+-\d+)\b',
    ]

    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            shipment_id = match.group(1).strip()
            if shipment_id:
                return shipment_id
    return None


def _resolve_runtime_table_name(table_name: str) -> str:
    return table_name


def _extract_route_direction(message: str) -> tuple[str | None, str | None]:
    pattern = re.compile(
        r'(?i)\b(?:route|shipment|shipments)?\s*(?:from|origin)\s+([A-Za-z][A-Za-z .-]+?)\s+(?:to|->|destination|for|and)\s+([A-Za-z][A-Za-z .-]+)'
    )
    match = pattern.search(message)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    pattern = re.compile(
        r'(?i)\b(?:from|origin)\s+([A-Za-z][A-Za-z .-]+)\s*(?:to|->|destination)\s+([A-Za-z][A-Za-z .-]+)'
    )
    match = pattern.search(message)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return None, None


def _extract_customer_filter(message: str) -> str | None:
    patterns = [
        r'(?i)\b(?:for|customer|customer is|customer name|related to|associated with)\s+([A-Z][A-Za-z0-9\' .-]+(?:\s+[A-Z][A-Za-z0-9\' .-]+)*)',
        r'(?i)\b(?:show|list|display|find|get)\s+(?:all\s+)?(?:shipments?|deliveries?|loads?)?\s*(?:related to|associated with|for|by)\s+([A-Z][A-Za-z0-9\' .-]+(?:\s+[A-Z][A-Za-z0-9\' .-]+)*)',
    ]
    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            value = match.group(1).strip()
            lowered = value.lower()
            if lowered in {'route', 'shipment', 'shipments', 'delivery', 'deliveries', 'customer'}:
                return None
            if any(token in lowered for token in ['source', 'destination', 'location', 'route']):
                return None
            return value
    return None


def _extract_generic_search_term(message: str) -> str | None:
    patterns = [
        r'(?i)\b(?:show\s+(?:me\s+)?|list\s+|display\s+|find\s+|get\s+|search\s+)\s*(?:all\s+)?(?:data|records?|shipments?|jobs?|vehicles?|logistics(?:\s+records)?)?\s*(?:for|related to|associated with|owned by|managed by|by)\s+([A-Z][A-Za-z0-9\' .-]+(?:\s+[A-Z][A-Za-z0-9\' .-]+)*)',
        r'(?i)\b(?:for|related to|associated with|owned by|managed by|by)\s+([A-Z][A-Za-z0-9\' .-]+(?:\s+[A-Z][A-Za-z0-9\' .-]+)*)',
    ]

    for pattern in patterns:
        match = re.search(pattern, message)
        if not match:
            continue

        value = match.group(1).strip()
        lowered = value.lower()
        if not value or value.lower() in {'route', 'shipment', 'shipments', 'delivery', 'deliveries', 'customer', 'data', 'records'}:
            continue
        if any(token in lowered for token in [' to ', ' from ', ' and ', 'route', 'source', 'destination', 'location']):
            continue
        return value

    return None


def _extract_field_search(message: str) -> tuple[str, str] | None:
    field_patterns = [
        (r'(?i)\b(?:show\s+(?:me\s+)?|list\s+|display\s+|find\s+|get\s+|search\s+)\s*(?:all\s+)?(?:client|customer)\s*(?:data)?\s*(?:for|related to|associated with|by)\s+([A-Z][A-Za-z0-9\' .-]+(?:\s+[A-Z][A-Za-z0-9\' .-]+)*)', 'client_name'),
        (r'(?i)\b(?:show\s+(?:me\s+)?|list\s+|display\s+|find\s+|get\s+|search\s+)\s*(?:all\s+)?(?:logistics\s+owner|owner)\s*(?:data)?\s*(?:for|related to|associated with|by)\s+([A-Z][A-Za-z0-9\' .-]+(?:\s+[A-Z][A-Za-z0-9\' .-]+)*)', 'logistics_owner'),
        (r'(?i)\b(?:show\s+(?:me\s+)?|list\s+|display\s+|find\s+|get\s+|search\s+)\s*(?:all\s+)?(?:operations\s+lead|lead)\s*(?:data)?\s*(?:for|related to|associated with|by)\s+([A-Z][A-Za-z0-9\' .-]+(?:\s+[A-Z][A-Za-z0-9\' .-]+)*)', 'operations_lead'),
    ]

    for pattern, field_name in field_patterns:
        match = re.search(pattern, message)
        if match:
            value = match.group(1).strip()
            if value:
                return field_name, value
    return None


def _build_generic_search_query(table_name: str, search_term: str) -> tuple[str, list[Any]]:
    resolved_table_name = _resolve_runtime_table_name(table_name)
    columns = sorted(ALLOWED_TABLES[table_name])
    like_value = f'%{search_term.strip()}%'
    sql = (
        f"SELECT {', '.join(columns)} FROM {resolved_table_name} WHERE "
        + ' OR '.join(f'CAST({column} AS TEXT) LIKE ?' for column in columns)
        + f' ORDER BY {TABLE_DEFAULT_ORDER[table_name]} LIMIT ?'
    )
    return sql, [like_value] * len(columns) + [settings.row_limit]


def _build_query_for_intent(message: str, table_name: str) -> tuple[str, list[Any]]:
    resolved_table_name = _resolve_runtime_table_name(table_name)
    columns = ', '.join(sorted(ALLOWED_TABLES[table_name]))
    lower_message = message.lower()
    params: list[Any] = []

    if table_name == 'logistics_records':
        record_ref = _extract_record_ref(message)
        if record_ref:
            return (
                f"SELECT {columns} FROM {resolved_table_name} WHERE record_ref = ? ORDER BY review_date DESC LIMIT ?",
                [record_ref, settings.row_limit],
            )

        if re.search(r'(?i)\b(?:show|list|display|get|find|search)\s+(?:me\s+)?(?:all\s+)?(?:data|records?)\s+(?:for\s+)?(?:each|all)\s+columns?\b', message):
            return (
                f"SELECT {columns} FROM {resolved_table_name} ORDER BY review_date DESC LIMIT ?",
                [settings.row_limit],
            )

        field_search = _extract_field_search(message)
        if field_search:
            field_name, field_value = field_search
            return (
                f"SELECT {columns} FROM {resolved_table_name} WHERE {field_name} LIKE ? ORDER BY review_date DESC LIMIT ?",
                [f'%{field_value}%', settings.row_limit],
            )

        if 'managed by' in lower_message or 'operations lead' in lower_message or 'job director' in lower_message:
            name = _extract_name(message)
            if name:
                return (
                    f"SELECT {columns} FROM {resolved_table_name} WHERE operations_lead = ? ORDER BY review_date DESC LIMIT ?",
                    [name, settings.row_limit],
                )
        if 'owner' in lower_message and ('logistics_owner' in lower_message or 'record_owner' in lower_message):
            name = _extract_name(message)
            if name:
                return (
                    f"SELECT {columns} FROM {resolved_table_name} WHERE logistics_owner = ? ORDER BY review_date DESC LIMIT ?",
                    [name, settings.row_limit],
                )
        if '2025' in lower_message or 'review date in 2025' in lower_message or 'valuation date in 2025' in lower_message:
            return (
                f"SELECT {columns} FROM {resolved_table_name} WHERE review_date LIKE ? ORDER BY review_date DESC LIMIT ?",
                ['2025%', settings.row_limit],
            )
        if 'test client uk uat1' in lower_message or 'test client' in lower_message:
            return (
                f"SELECT {columns} FROM {resolved_table_name} WHERE client_name LIKE ? ORDER BY review_date DESC LIMIT ?",
                ['%Test Client%', settings.row_limit],
            )

        if re.search(r'(?i)\b(?:show|list|display|get|find|search)\s+(?:me\s+)?(?:all\s+)?(?:data|records?)\s+(?:for\s+)?(?:each|all)\s+columns?\b', message):
            return (
                f"SELECT {columns} FROM {resolved_table_name} ORDER BY review_date DESC LIMIT ?",
                [settings.row_limit],
            )

        generic_search = _extract_generic_search_term(message)
        if generic_search:
            return _build_generic_search_query(table_name, generic_search)

        return (
            f"SELECT {columns} FROM {resolved_table_name} ORDER BY review_date DESC LIMIT ?",
            [settings.row_limit],
        )

    if table_name == 'jobs':
        if 'open' in lower_message:
            return (
                f"SELECT {columns} FROM jobs WHERE status != 'Completed' ORDER BY days_open DESC LIMIT ?",
                [settings.row_limit],
            )
        if 'progress' in lower_message:
            return (
                f"SELECT {columns} FROM jobs ORDER BY progress_pct DESC LIMIT ?",
                [settings.row_limit],
            )

        generic_search = _extract_generic_search_term(message)
        if generic_search:
            return _build_generic_search_query(table_name, generic_search)

        return (
            f"SELECT {columns} FROM jobs ORDER BY progress_pct DESC LIMIT ?",
            [settings.row_limit],
        )

    if table_name == 'shipments':
        shipment_id = _extract_shipment_id(message)
        if shipment_id:
            return (
                f"SELECT {columns} FROM shipments WHERE shipment_id = ? ORDER BY COALESCE(actual_delivery_date, planned_delivery_date, delivery_date) DESC LIMIT ?",
                [shipment_id.upper(), settings.row_limit],
            )

        origin, destination = _extract_route_direction(message)
        if origin and destination:
            return (
                f"SELECT {columns} FROM shipments WHERE origin = ? AND destination = ? ORDER BY COALESCE(actual_delivery_date, planned_delivery_date, delivery_date) ASC LIMIT ?",
                [origin.strip().title(), destination.strip().title(), settings.row_limit],
            )

        customer_filter = _extract_customer_filter(message)
        if customer_filter:
            generic_search = _extract_generic_search_term(message)
            if generic_search:
                return _build_generic_search_query(table_name, generic_search)
            return (
                f"SELECT {columns} FROM shipments WHERE customer = ? ORDER BY COALESCE(actual_delivery_date, planned_delivery_date, delivery_date) DESC LIMIT ?",
                [customer_filter, settings.row_limit],
            )

        generic_search = _extract_generic_search_term(message)
        if generic_search:
            return _build_generic_search_query(table_name, generic_search)

        if 'delayed' in lower_message:
            return (
                f"SELECT {columns} FROM shipments WHERE status = ? ORDER BY COALESCE(actual_delivery_date, planned_delivery_date, delivery_date) ASC LIMIT ?",
                ['Delayed', settings.row_limit],
            )
        if 'delivered' in lower_message:
            return (
                f"SELECT {columns} FROM shipments WHERE status = ? ORDER BY COALESCE(actual_delivery_date, planned_delivery_date, delivery_date) DESC LIMIT ?",
                ['Delivered', settings.row_limit],
            )
        if 'source' in lower_message and 'destination' in lower_message:
            generic_view_request = (
                'source location' in lower_message
                and 'destination location' in lower_message
                and ' and ' in lower_message
                and not any(term in lower_message for term in [' from ', ' to ', ' is ', 'between'])
            )
            if not generic_view_request:
                source_match = re.search(r'source(?:\s+location)?\s+(?:is\s+)?([A-Za-z ]+?)(?:\s+to\s+|\s+destination|$)', lower_message)
                destination_match = re.search(r'destination(?:\s+location)?\s+(?:is\s+)?([A-Za-z ]+?)(?:\s+for\s+|\s+from\s+|$)', lower_message)
                source_value = source_match.group(1).strip() if source_match else ''
                destination_value = destination_match.group(1).strip() if destination_match else ''
                if source_value and destination_value and source_value.lower() not in {'and', 'to', 'from'} and destination_value.lower() not in {'and', 'to', 'from'}:
                    return (
                        f"SELECT {columns} FROM shipments WHERE source_location = ? AND destination_location = ? ORDER BY COALESCE(actual_delivery_date, planned_delivery_date, delivery_date) ASC LIMIT ?",
                        [source_value.title(), destination_value.title(), settings.row_limit],
                    )
        if 'route start' in lower_message or 'start date' in lower_message:
            return (
                f"SELECT {columns} FROM shipments ORDER BY route_start_date ASC LIMIT ?",
                [settings.row_limit],
            )
        if 'actual delivery' in lower_message or 'delivery date' in lower_message:
            return (
                f"SELECT {columns} FROM shipments ORDER BY COALESCE(actual_delivery_date, planned_delivery_date, delivery_date) ASC LIMIT ?",
                [settings.row_limit],
            )
        if 'route' in lower_message:
            return (
                f"SELECT {columns} FROM shipments ORDER BY COALESCE(actual_delivery_date, planned_delivery_date, delivery_date) ASC LIMIT ?",
                [settings.row_limit],
            )
        return (
            f"SELECT {columns} FROM shipments ORDER BY COALESCE(actual_delivery_date, planned_delivery_date, delivery_date) ASC LIMIT ?",
            [settings.row_limit],
        )

    if table_name == 'vehicles':
        if 'maintenance' in lower_message:
            return (
                f"SELECT {columns} FROM vehicles WHERE status = ? ORDER BY utilization_pct DESC LIMIT ?",
                ['Maintenance', settings.row_limit],
            )
        return (
            f"SELECT {columns} FROM vehicles ORDER BY utilization_pct DESC LIMIT ?",
            [settings.row_limit],
        )

    return (
        f"SELECT {columns} FROM {table_name} LIMIT ?",
        [settings.row_limit],
    )


def detect_table_from_message(message: str) -> str | None:
    lower_message = message.lower()

    if any(
        term in lower_message
        for term in [
            'add route',
            'create route',
            'new route',
            'plan route',
            'schedule route',
            'route from',
            'route to',
            'route between',
        ]
    ):
        return 'shipments'

    if re.search(r'(?i)\b(?:show|list|display|get|find|search)\s+(?:me\s+)?(?:all\s+)?(?:data|records?|client|logistics\s+owner|owner|operations\s+lead|lead|logistics(?:\s+records)?)?\s*(?:for|related to|associated with|managed by|owned by|by)\s+[A-Z]', message):
        return 'logistics_records'

    if re.search(r'(?i)\b(?:show|list|display|get|find|search)\s+(?:me\s+)?(?:detail|details)?\s*(?:for\s+)?(?:record\s+ref|record\s+reference|ref)\b', message):
        return 'logistics_records'

    if re.search(r'(?i)\b(?:show|list|display|get|find|search)\s+(?:me\s+)?(?:all\s+)?(?:data|records?)\s+(?:for\s+)?(?:each|all)\s+columns?\b', message):
        return 'logistics_records'

    if any(
        term in lower_message
        for term in [
            'pipeline',
            'logistics pipeline',
            'record',
            'records',
            'projects',
            'client',
            'valuation',
            'review date',
            'operations lead',
            'logistics owner',
            'salesforce',
            'properties',
            'route count',
            'logistics records',
            'record set',
        ]
    ):
        return 'logistics_records'

    if any(term in lower_message for term in ['job', 'jobs', 'work order', 'work orders', 'stage', 'progress', 'days open', 'current stage']):
        return 'jobs'

    if any(
        term in lower_message
        for term in ['shipment', 'shipments', 'delivery', 'route', 'origin', 'destination', 'source location', 'destination location', 'route start date', 'actual delivery date', 'cargo']
    ):
        return 'shipments'

    if any(term in lower_message for term in ['vehicle', 'vehicles', 'fleet', 'depot', 'maintenance', 'utilization']):
        return 'vehicles'

    return None


def _validate_sql(sql: str) -> None:
    normalized_sql = (sql or '').strip()

    if not normalized_sql or ';' in normalized_sql:
        raise ValueError('Only a single read-only statement is allowed.')

    if not READ_ONLY_SQL_PATTERN.match(normalized_sql):
        raise ValueError('Only SELECT statements are allowed.')

    if '--' in normalized_sql or '/*' in normalized_sql or '*/' in normalized_sql:
        raise ValueError('SQL comments are not allowed.')

    if FORBIDDEN_SQL_PATTERN.search(normalized_sql):
        raise ValueError('Unsafe SQL detected.')

    table_names = {match.group(1).lower() for match in TABLE_REFERENCE_PATTERN.finditer(normalized_sql)}
    if not table_names:
        raise ValueError('Missing table reference in query.')

    disallowed_tables = sorted(table_name for table_name in table_names if table_name not in ALLOWED_TABLES)
    if disallowed_tables:
        raise ValueError(f'Table {disallowed_tables[0]} is not allowed.')


def execute_safe_query(message: str, table_hint: str | None = None) -> dict[str, Any]:
    table_name = detect_table_from_message(message) or (table_hint if table_hint in ALLOWED_TABLES else None)
    if table_name is None:
        return {'table': None, 'sql': None, 'rows': [], 'summary': 'This question is outside the approved logistics data model.'}

    sql, params = _build_query_for_intent(message, table_name)
    _validate_sql(sql)

    with get_connection() as connection:
        cursor = connection.execute(sql, params)
        rows = [dict(row) for row in cursor.fetchall()]

    rows = _attach_coordinates(table_name, rows)

    return {
        'table': table_name,
        'sql': sql,
        'rows': rows,
        'summary': f'Fetched {len(rows)} logistics records.',
    }


def get_dashboard_snapshot() -> dict[str, Any]:
    with get_connection() as connection:
        totals = {
            'active_shipments': connection.execute(
                "SELECT COUNT(*) FROM shipments WHERE status IN ('In transit', 'Planned', 'Delayed')"
            ).fetchone()[0],
            'delayed_shipments': connection.execute("SELECT COUNT(*) FROM shipments WHERE status = 'Delayed'").fetchone()[0],
            'fleet_utilization_avg': connection.execute("SELECT ROUND(AVG(utilization_pct), 1) FROM vehicles").fetchone()[0] or 0,
            'open_jobs': connection.execute("SELECT COUNT(*) FROM jobs WHERE status != 'Completed'").fetchone()[0],
            'active_records': connection.execute(f"SELECT COUNT(*) FROM {_resolve_runtime_table_name('logistics_records')}").fetchone()[0],
        }

        route_risks = [
            dict(row)
            for row in connection.execute(
                """
                SELECT route, COUNT(*) AS delayed_count
                FROM shipments
                WHERE status = 'Delayed'
                GROUP BY route
                ORDER BY delayed_count DESC
                LIMIT 5
                """
            ).fetchall()
        ]

        live_shipments = [
            dict(row)
            for row in connection.execute(
                """
                SELECT shipment_id, customer, source_location, destination_location, route_start_date,
                       planned_delivery_date, actual_delivery_date, status, delivery_date, weight_kg, value_usd
                FROM shipments
                ORDER BY COALESCE(actual_delivery_date, planned_delivery_date, delivery_date) DESC
                LIMIT 12
                """
            ).fetchall()
        ]

    return {
        'kpis': totals,
        'risk_routes': route_risks,
        'live_shipments': live_shipments,
    }


def get_live_table_rows(
    table_name: str,
    page: int = 1,
    page_size: int = 50,
    search: str | None = None,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fetch one page of a dashboard table, optionally narrowed by free-text search and column filters.

    Search and filter columns are always validated against ALLOWED_TABLES before being
    interpolated into SQL — values are never concatenated, only bound as parameters.
    """
    safe_table = table_name.lower().strip()
    if safe_table not in ALLOWED_TABLES:
        raise ValueError(f'Table {safe_table} is not allowed.')

    allowed_columns = ALLOWED_TABLES[safe_table]
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, MAX_PAGE_SIZE))
    sorted_columns = sorted(allowed_columns)
    columns = ', '.join(sorted_columns)
    order_clause = TABLE_DEFAULT_ORDER[safe_table]

    where_clauses: list[str] = []
    params: list[Any] = []

    search_term = (search or '').strip()
    if search_term:
        like_term = f'%{search_term}%'
        search_conditions = [f'CAST({column} AS TEXT) LIKE ?' for column in sorted_columns]
        where_clauses.append('(' + ' OR '.join(search_conditions) + ')')
        params.extend([like_term] * len(search_conditions))

    for column, value in (filters or {}).items():
        if column not in allowed_columns:
            raise ValueError(f'Filter column {column} is not allowed for {safe_table}.')
        if value in (None, ''):
            continue
        where_clauses.append(f'{column} = ?')
        params.append(value)

    where_sql = f' WHERE {" AND ".join(where_clauses)}' if where_clauses else ''

    with get_connection() as connection:
        total = connection.execute(f'SELECT COUNT(*) FROM {safe_table}{where_sql}', params).fetchone()[0]
        offset = (safe_page - 1) * safe_page_size
        sql = f'SELECT {columns} FROM {safe_table}{where_sql} ORDER BY {order_clause} LIMIT ? OFFSET ?'
        cursor = connection.execute(sql, [*params, safe_page_size, offset])
        rows = [dict(row) for row in cursor.fetchall()]

    rows = _attach_coordinates(safe_table, rows)
    total_pages = max(1, -(-total // safe_page_size)) if total else 1

    return {
        'table': safe_table,
        'rows': rows,
        'summary': f'Fetched {len(rows)} of {total} records from {safe_table}.',
        'page': safe_page,
        'page_size': safe_page_size,
        'total': total,
        'total_pages': total_pages,
    }


def get_filter_options(table_name: str) -> dict[str, list[Any]]:
    """Return distinct values for each dashboard-filterable column, for building filter dropdowns."""
    safe_table = table_name.lower().strip()
    if safe_table not in ALLOWED_TABLES:
        raise ValueError(f'Table {safe_table} is not allowed.')

    options: dict[str, list[Any]] = {}
    with get_connection() as connection:
        for column in FILTERABLE_COLUMNS.get(safe_table, []):
            rows = connection.execute(
                f'SELECT DISTINCT {column} FROM {safe_table} WHERE {column} IS NOT NULL ORDER BY {column}'
            ).fetchall()
            options[column] = [row[0] for row in rows]

    return options
