from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from app.config import settings

TABLE_CACHE_FILENAME = 'tables_cache.json'

LEGACY_DATA_MARKERS = (
    'deutsche bank',
    'northgate properties',
    'westfield capital',
    'crimson estates',
    'portfolio review',
    'valuation in progress',
    'awaiting approval',
    'sage homes limited',
)


def _resolve_database_path() -> Path:
    candidate = Path(settings.database_path)
    if candidate.is_absolute():
        return candidate
    return Path(__file__).resolve().parent.parent / candidate


def _resolve_table_cache_path() -> Path:
    return _resolve_database_path().parent / TABLE_CACHE_FILENAME


def get_connection() -> sqlite3.Connection:
    database_path = _resolve_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def _contains_legacy_terms(value: Any) -> bool:
    if isinstance(value, str):
        normalized = value.lower()
        return any(marker in normalized for marker in LEGACY_DATA_MARKERS)
    if isinstance(value, dict):
        return any(_contains_legacy_terms(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_legacy_terms(item) for item in value)
    return False


def _generate_logistics_records() -> list[dict[str, Any]]:
    client_names = [
        'Northstar Freight',
        'BluePeak Retail Logistics',
        'HarborSpan Distribution',
        'Summit Cold Chain',
        'Apex Route Services',
        'Crestline Logistics',
        'MetroLane Warehousing',
        'TransOrbital Cargo',
        'Crimson Fleet Services',
        'BluePeak Housing Logistics',
    ]
    operations_leads = [
        'James Harris',
        'Andrew Parling',
        'Rupert Driver',
        'John Barham',
        'Genine Terry',
        'Sarah Collins',
        'Michael Turner',
        'Priya Nair',
    ]
    logistics_owners = [
        'Anju Munjal',
        'Swati Jadhav',
        'Ailish Humphries-Griffiths',
        'Jonathan Crossan',
        'Mike Jones',
        'Elena Brooks',
        'Oliver Patel',
    ]
    regions = ['London', 'Manchester', 'Birmingham', 'Leeds', 'Glasgow', 'Bristol', 'Edinburgh']
    stages = ['In Progress', 'Due this week', 'Capacity review', 'Awaiting manifest', 'On hold']

    rows: list[dict[str, Any]] = []
    for index in range(1, 621):
        client_name = client_names[(index - 1) % len(client_names)]
        operations_lead = operations_leads[(index - 1) % len(operations_leads)]
        logistics_owner = logistics_owners[(index - 1) % len(logistics_owners)]
        region = regions[(index - 1) % len(regions)]
        status = stages[(index - 1) % len(stages)]
        route_count = 8 + ((index * 13) % 211)
        value_usd = 150000 + (index * 18750)
        review_year = 2024 + (index % 3)
        month = 1 + ((index * 3) % 12)
        day = 1 + ((index * 7) % 27)
        review_date = f'{review_year}-{month:02d}-{day:02d}'
        rows.append(
            {
                'record_ref': f'SF-{24000 + index}',
                'client_name': client_name,
                'operations_lead': operations_lead,
                'logistics_owner': logistics_owner,
                'route_count': route_count,
                'review_date': review_date,
                'status': status,
                'region': region,
                'value_usd': value_usd,
            }
        )

    return rows


def _generate_jobs() -> list[dict[str, Any]]:
    stages = ['Planning', 'Route review', 'Dispatch in progress', 'Awaiting carrier', 'Completed']
    regions = ['London', 'Manchester', 'Birmingham', 'Leeds', 'Glasgow', 'Bristol', 'Edinburgh']
    client_names = [
        'Northstar Freight',
        'BluePeak Retail Logistics',
        'HarborSpan Distribution',
        'Summit Cold Chain',
        'MetroLane Warehousing',
        'TransOrbital Cargo',
    ]
    rows: list[dict[str, Any]] = []
    for index in range(1, 561):
        client_name = client_names[(index - 1) % len(client_names)]
        record_ref = f'SF-{24000 + index}'
        region = regions[(index - 1) % len(regions)]
        status = stages[(index - 1) % len(stages)]
        progress_pct = 18 + ((index * 17) % 82)
        days_open = 3 + ((index * 11) % 220)
        total_properties = 12 + ((index * 7) % 320)
        current_stage = stages[(index + 1) % len(stages)]
        rows.append(
            {
                'job_id': f'JOB-{1000 + index}',
                'record_ref': record_ref,
                'client_name': client_name,
                'region': region,
                'status': status,
                'progress_pct': progress_pct,
                'days_open': days_open,
                'total_properties': total_properties,
                'current_stage': current_stage,
            }
        )
    return rows


def _generate_shipments() -> list[dict[str, Any]]:
    customers = ['Northstar Freight', 'Crestline Logistics', 'BluePeak Housing Logistics', 'HarborSpan Distribution', 'MetroLane Warehousing']
    route_pairs = [
        ('Southampton', 'Birmingham'),
        ('Leeds', 'London'),
        ('Manchester', 'Bristol'),
        ('Birmingham', 'Glasgow'),
        ('London', 'Edinburgh'),
        ('Leeds', 'Manchester'),
    ]
    route_stop_options = {
        'Southampton': ['Bristol', 'Leeds', 'Birmingham'],
        'Leeds': ['Bradford', 'Manchester', 'Birmingham'],
        'Manchester': ['Bradford', 'Leeds', 'Bristol'],
        'Birmingham': ['Leeds', 'Wolverhampton', 'Glasgow'],
        'London': ['Birmingham', 'Leeds', 'Peterborough'],
        'Glasgow': ['Edinburgh', 'Manchester', 'Leeds'],
        'Bristol': ['Southampton', 'Birmingham', 'Leeds'],
        'Edinburgh': ['Glasgow', 'Manchester', 'Leeds'],
    }
    statuses = ['In transit', 'Delayed', 'Delivered', 'Exception', 'Planned']
    rows: list[dict[str, Any]] = []
    for index in range(1, 661):
        customer = customers[(index - 1) % len(customers)]
        source_location, destination_location = route_pairs[(index - 1) % len(route_pairs)]
        status_cycle = (index % 10)
        if status_cycle in {0, 1, 2}:
            status = 'Delayed'
        elif status_cycle in {3, 4}:
            status = 'Exception'
        elif status_cycle == 5:
            status = 'Planned'
        elif status_cycle in {6, 7}:
            status = 'In transit'
        else:
            status = 'Delivered'

        route_waypoints = [
            city
            for city in route_stop_options.get(source_location, [destination_location])
            if city not in {source_location, destination_location}
        ]
        route_path = [source_location, *route_waypoints[:2], destination_location]
        route = ' -> '.join(route_path)

        route_start_year = 2024 + (index % 2)
        route_start_month = 1 + ((index * 3) % 12)
        route_start_day = 1 + ((index * 5) % 28)
        route_start_date = date(route_start_year, route_start_month, route_start_day)

        delivery_day = 1 + ((index * 5) % 28)
        delivery_month = 1 + ((index * 2) % 12)
        delivery_year = 2024 + (index % 2)
        delivery_date = date(delivery_year, delivery_month, delivery_day)
        planned_offset = 2 + ((index * 3) % 12)
        planned_delivery_date = delivery_date + timedelta(days=planned_offset)

        if status == 'Delivered':
            actual_delivery_date = delivery_date
        elif status == 'Delayed':
            actual_delivery_date = planned_delivery_date + timedelta(days=1 + (index % 4))
        elif status == 'Exception':
            actual_delivery_date = planned_delivery_date + timedelta(days=3 + (index % 5))
        else:
            actual_delivery_date = planned_delivery_date

        rows.append(
            {
                'shipment_id': f'SHP-{5000 + index}',
                'customer': customer,
                'route': route,
                'origin': source_location,
                'destination': destination_location,
                'source_location': source_location,
                'destination_location': destination_location,
                'status': status,
                'route_start_date': route_start_date.isoformat(),
                'planned_delivery_date': planned_delivery_date.isoformat(),
                'actual_delivery_date': actual_delivery_date.isoformat(),
                'delivery_date': delivery_date.isoformat(),
                'weight_kg': 180 + ((index * 37) % 2260),
                'value_usd': 1500 + ((index * 213) % 85000),
            }
        )
    return rows


def _generate_vehicles() -> list[dict[str, Any]]:
    depots = ['London Central', 'Manchester North', 'Birmingham Yard', 'Leeds Depot', 'Glasgow Hub']
    statuses = ['Available', 'In use', 'Maintenance', 'Idle']
    rows: list[dict[str, Any]] = []
    for index in range(1, 541):
        depot = depots[(index - 1) % len(depots)]
        status = statuses[(index - 1) % len(statuses)]
        utilization = 36 + ((index * 7) % 64)
        service_month = 1 + ((index * 2) % 12)
        service_year = 2023 + (index % 3)
        rows.append(
            {
                'vehicle_id': f'VEH-{800 + index}',
                'depot': depot,
                'status': status,
                'utilization_pct': utilization,
                'last_service_date': f'{service_year}-{service_month:02d}-15',
            }
        )
    return rows


def _build_table_cache() -> dict[str, list[dict[str, Any]]]:
    return {
        'logistics_records': _generate_logistics_records(),
        'jobs': _generate_jobs(),
        'shipments': _generate_shipments(),
        'vehicles': _generate_vehicles(),
    }


def _write_table_cache(cache_path: Path, cache: dict[str, list[dict[str, Any]]]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open('w', encoding='utf-8') as handle:
        json.dump(cache, handle, indent=2)


def load_table_cache() -> dict[str, list[dict[str, Any]]]:
    """Load all seed table rows from a single JSON cache file, building it once if absent."""
    cache_path = _resolve_table_cache_path()
    if cache_path.exists():
        with cache_path.open('r', encoding='utf-8') as handle:
            cache = json.load(handle)

        logistics_rows = cache.get('logistics_records', cache.get('opportunities', []))
        shipments_rows = cache.get('shipments', [])
        if (
            logistics_rows
            and not any('record_ref' in row for row in logistics_rows[:1])
            or shipments_rows
            and not any('source_location' in row and 'route_start_date' in row and 'actual_delivery_date' in row for row in shipments_rows[:1])
        ):
            cache = _build_table_cache()
            _write_table_cache(cache_path, cache)
            return cache
        if _contains_legacy_terms(cache):
            cache = _build_table_cache()
            _write_table_cache(cache_path, cache)
            return cache
        return cache

    cache = _build_table_cache()
    _write_table_cache(cache_path, cache)
    return cache


def _table_contains_legacy_terms(connection: sqlite3.Connection, table_name: str, text_columns: tuple[str, ...]) -> bool:
    for column in text_columns:
        query = f'SELECT {column} FROM {table_name} LIMIT 50'
        for row in connection.execute(query).fetchall():
            if _contains_legacy_terms(row[0]):
                return True
    return False


def _seed_logistics_records(connection: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    connection.executemany(
        """
        INSERT INTO logistics_records (
            record_ref,
            client_name,
            operations_lead,
            logistics_owner,
            route_count,
            review_date,
            status,
            region,
            value_usd
        ) VALUES (
            :record_ref,
            :client_name,
            :operations_lead,
            :logistics_owner,
            :route_count,
            :review_date,
            :status,
            :region,
            :value_usd
        )
        """,
        rows,
    )


def _seed_jobs(connection: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    connection.executemany(
        """
        INSERT INTO jobs (
            job_id,
            record_ref,
            client_name,
            region,
            status,
            progress_pct,
            days_open,
            total_properties,
            current_stage
        ) VALUES (
            :job_id,
            :record_ref,
            :client_name,
            :region,
            :status,
            :progress_pct,
            :days_open,
            :total_properties,
            :current_stage
        )
        """,
        rows,
    )


def _seed_shipments(connection: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    connection.executemany(
        """
        INSERT INTO shipments (
            shipment_id,
            customer,
            route,
            origin,
            destination,
            source_location,
            destination_location,
            status,
            route_start_date,
            planned_delivery_date,
            actual_delivery_date,
            delivery_date,
            weight_kg,
            value_usd
        ) VALUES (
            :shipment_id,
            :customer,
            :route,
            :origin,
            :destination,
            :source_location,
            :destination_location,
            :status,
            :route_start_date,
            :planned_delivery_date,
            :actual_delivery_date,
            :delivery_date,
            :weight_kg,
            :value_usd
        )
        """,
        rows,
    )


def _seed_vehicles(connection: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    connection.executemany(
        """
        INSERT INTO vehicles (
            vehicle_id,
            depot,
            status,
            utilization_pct,
            last_service_date
        ) VALUES (
            :vehicle_id,
            :depot,
            :status,
            :utilization_pct,
            :last_service_date
        )
        """,
        rows,
    )


def initialize_database() -> None:
    database_path = _resolve_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    try:
        legacy_table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'opportunities'"
        ).fetchone() is not None

        if legacy_table_exists:
            legacy_columns = {row[1] for row in connection.execute('PRAGMA table_info(opportunities)').fetchall()}
            if legacy_columns & {'job_director', 'opportunity_owner', 'salesforce_number', 'valuation_date', 'number_of_properties'}:
                connection.execute('ALTER TABLE opportunities RENAME TO opportunities_legacy')

        legacy_logistics_table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'logistics_records'"
        ).fetchone() is not None
        if legacy_logistics_table_exists:
            current_columns = {row[1] for row in connection.execute('PRAGMA table_info(logistics_records)').fetchall()}
            if 'record_ref' not in current_columns:
                connection.execute('ALTER TABLE logistics_records RENAME TO logistics_records_legacy')

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS logistics_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_ref TEXT UNIQUE NOT NULL,
                client_name TEXT NOT NULL,
                operations_lead TEXT NOT NULL,
                logistics_owner TEXT NOT NULL,
                route_count INTEGER NOT NULL,
                review_date TEXT NOT NULL,
                status TEXT NOT NULL,
                region TEXT NOT NULL,
                value_usd INTEGER NOT NULL
            )
            """
        )

        if legacy_table_exists and connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'opportunities_legacy'"
        ).fetchone() is not None:
            connection.execute(
                """
                INSERT OR IGNORE INTO logistics_records (
                    record_ref,
                    client_name,
                    operations_lead,
                    logistics_owner,
                    route_count,
                    review_date,
                    status,
                    region,
                    value_usd
                )
                SELECT
                    salesforce_number,
                    client_name,
                    job_director,
                    opportunity_owner,
                    number_of_properties,
                    valuation_date,
                    status,
                    region,
                    value_usd
                FROM opportunities_legacy
                """
            )
            connection.execute('DROP TABLE opportunities_legacy')

        if connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'logistics_records_legacy'"
        ).fetchone() is not None:
            connection.execute(
                """
                INSERT OR IGNORE INTO logistics_records (
                    record_ref,
                    client_name,
                    operations_lead,
                    logistics_owner,
                    route_count,
                    review_date,
                    status,
                    region,
                    value_usd
                )
                SELECT
                    pipeline_ref,
                    client_name,
                    operations_lead,
                    logistics_owner,
                    route_count,
                    review_date,
                    status,
                    region,
                    value_usd
                FROM logistics_records_legacy
                """
            )
            connection.execute('DROP TABLE logistics_records_legacy')

        legacy_jobs_table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'jobs'"
        ).fetchone() is not None
        if legacy_jobs_table_exists:
            current_job_columns = {row[1] for row in connection.execute('PRAGMA table_info(jobs)').fetchall()}
            if 'record_ref' not in current_job_columns:
                connection.execute('ALTER TABLE jobs RENAME TO jobs_legacy')

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE NOT NULL,
                record_ref TEXT NOT NULL,
                client_name TEXT NOT NULL,
                region TEXT NOT NULL,
                status TEXT NOT NULL,
                progress_pct INTEGER NOT NULL,
                days_open INTEGER NOT NULL,
                total_properties INTEGER NOT NULL,
                current_stage TEXT NOT NULL
            )
            """
        )

        if connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'jobs_legacy'"
        ).fetchone() is not None:
            connection.execute(
                """
                INSERT OR IGNORE INTO jobs (
                    job_id,
                    record_ref,
                    client_name,
                    region,
                    status,
                    progress_pct,
                    days_open,
                    total_properties,
                    current_stage
                )
                SELECT
                    job_id,
                    opportunity_ref,
                    client_name,
                    region,
                    status,
                    progress_pct,
                    days_open,
                    total_properties,
                    current_stage
                FROM jobs_legacy
                """
            )
            connection.execute('DROP TABLE jobs_legacy')
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS shipments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shipment_id TEXT UNIQUE NOT NULL,
                customer TEXT NOT NULL,
                route TEXT NOT NULL,
                origin TEXT NOT NULL,
                destination TEXT NOT NULL,
                source_location TEXT,
                destination_location TEXT,
                status TEXT NOT NULL,
                route_start_date TEXT,
                planned_delivery_date TEXT,
                actual_delivery_date TEXT,
                delivery_date TEXT NOT NULL,
                weight_kg INTEGER NOT NULL,
                value_usd INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id TEXT UNIQUE NOT NULL,
                depot TEXT NOT NULL,
                status TEXT NOT NULL,
                utilization_pct INTEGER NOT NULL,
                last_service_date TEXT NOT NULL
            )
            """
        )

        minimum_targets = {
            'logistics_records': 620,
            'jobs': 560,
            'shipments': 660,
            'vehicles': 540,
        }
        current_counts = {
            table: connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
            for table in minimum_targets
        }

        shipment_columns = {row[1] for row in connection.execute('PRAGMA table_info(shipments)').fetchall()}
        missing_shipment_columns = {
            'source_location',
            'destination_location',
            'route_start_date',
            'planned_delivery_date',
            'actual_delivery_date',
        } - shipment_columns
        for column_name in sorted(missing_shipment_columns):
            connection.execute(f'ALTER TABLE shipments ADD COLUMN {column_name} TEXT')

        shipment_metadata_missing = connection.execute(
            "SELECT 1 FROM shipments WHERE source_location IS NULL OR destination_location IS NULL OR route_start_date IS NULL OR planned_delivery_date IS NULL OR actual_delivery_date IS NULL LIMIT 1"
        ).fetchone() is not None

        legacy_content_present = any(
            [
                _table_contains_legacy_terms(connection, 'logistics_records', ('client_name', 'status')),
                _table_contains_legacy_terms(connection, 'jobs', ('client_name', 'status', 'current_stage')),
                _table_contains_legacy_terms(connection, 'shipments', ('customer', 'status')),
            ]
        )

        needs_reseed = (
            legacy_content_present
            or shipment_metadata_missing
            or bool(missing_shipment_columns)
            or any(current_counts[table] < target for table, target in minimum_targets.items())
        )
        if needs_reseed:
            connection.execute('DELETE FROM logistics_records')
            connection.execute('DELETE FROM jobs')
            connection.execute('DELETE FROM shipments')
            connection.execute('DELETE FROM vehicles')
            connection.execute("DELETE FROM sqlite_sequence WHERE name IN ('logistics_records', 'jobs', 'shipments', 'vehicles')")

        if needs_reseed or current_counts['logistics_records'] == 0 or current_counts['jobs'] == 0 or current_counts['shipments'] == 0 or current_counts['vehicles'] == 0:
            table_cache = load_table_cache()
        else:
            table_cache = None

        if needs_reseed or current_counts['logistics_records'] == 0:
            _seed_logistics_records(connection, table_cache['logistics_records'])
        if needs_reseed or current_counts['jobs'] == 0:
            _seed_jobs(connection, table_cache['jobs'])
        if needs_reseed or current_counts['shipments'] == 0:
            _seed_shipments(connection, table_cache['shipments'])
        if needs_reseed or current_counts['vehicles'] == 0:
            _seed_vehicles(connection, table_cache['vehicles'])

        connection.commit()
    finally:
        connection.close()

