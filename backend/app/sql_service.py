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
        'status',
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
    'shipments': 'delivery_date DESC',
    'vehicles': 'utilization_pct DESC',
}

# Columns exposed as dashboard filter dropdowns, restricted to low-cardinality categorical fields.
FILTERABLE_COLUMNS: dict[str, list[str]] = {
    'logistics_records': ['status', 'region'],
    'jobs': ['status', 'region', 'current_stage'],
    'shipments': ['status', 'origin', 'destination'],
    'vehicles': ['status', 'depot'],
}

MAX_PAGE_SIZE = 200

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
    'shipments': 'destination',
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


def _resolve_runtime_table_name(table_name: str) -> str:
    return table_name


def _build_query_for_intent(message: str, table_name: str) -> tuple[str, list[Any]]:
    resolved_table_name = _resolve_runtime_table_name(table_name)
    columns = ', '.join(sorted(ALLOWED_TABLES[table_name]))
    lower_message = message.lower()
    params: list[Any] = []

    if table_name == 'logistics_records':
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
        return (
            f"SELECT {columns} FROM jobs ORDER BY progress_pct DESC LIMIT ?",
            [settings.row_limit],
        )

    if table_name == 'shipments':
        if 'delayed' in lower_message:
            return (
                f"SELECT {columns} FROM shipments WHERE status = ? ORDER BY delivery_date ASC LIMIT ?",
                ['Delayed', settings.row_limit],
            )
        if 'delivered' in lower_message:
            return (
                f"SELECT {columns} FROM shipments WHERE status = ? ORDER BY delivery_date DESC LIMIT ?",
                ['Delivered', settings.row_limit],
            )
        if 'route' in lower_message:
            return (
                f"SELECT {columns} FROM shipments ORDER BY delivery_date ASC LIMIT ?",
                [settings.row_limit],
            )
        return (
            f"SELECT {columns} FROM shipments ORDER BY delivery_date ASC LIMIT ?",
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
    if any(term in lower_message for term in ['pipeline', 'logistics pipeline', 'record', 'records', 'projects', 'client', 'valuation', 'review date', 'operations lead', 'logistics owner', 'salesforce', 'properties', 'route count', 'logistics records', 'record set']):
        return 'logistics_records'
    if any(term in lower_message for term in ['job', 'jobs', 'work order', 'work orders', 'stage', 'progress', 'days open', 'current stage']):
        return 'jobs'
    if any(term in lower_message for term in ['shipment', 'shipments', 'delivery', 'route', 'origin', 'destination', 'cargo']):
        return 'shipments'
    if any(term in lower_message for term in ['vehicle', 'vehicles', 'fleet', 'depot', 'maintenance', 'utilization']):
        return 'vehicles'
    return None


def _validate_sql(sql: str) -> None:
    if not sql or ';' in sql:
        raise ValueError('Only a single read-only statement is allowed.')
    forbidden = re.compile(r'(?i)\b(drop|delete|update|insert|alter|truncate|grant|revoke|create|attach|detach|replace|execute)\b')
    if forbidden.search(sql):
        raise ValueError('Unsafe SQL detected.')
    match = re.search(r'\bFROM\s+([A-Za-z_]+)', sql, flags=re.IGNORECASE)
    if not match:
        raise ValueError('Missing table reference in query.')
    table_name = match.group(1).lower()
    if table_name not in ALLOWED_TABLES:
        raise ValueError(f'Table {table_name} is not allowed.')


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
                SELECT shipment_id, customer, origin, destination, status, delivery_date, weight_kg, value_usd
                FROM shipments
                ORDER BY delivery_date DESC
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
