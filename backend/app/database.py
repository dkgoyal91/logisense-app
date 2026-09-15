from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.config import settings

TABLE_CACHE_FILENAME = 'tables_cache.json'


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


def _generate_logistics_records() -> list[dict[str, Any]]:
    client_names = [
        'Sage Homes Limited',
        'Test Client UK UAT1',
        'Client_Tanveer1',
        'UAT_TestAcc_0609',
        'Test - Deutsche Bank AG, Filiale London',
        'Crestline Logistics',
        'Northgate Properties',
        'Westfield Capital',
        'Crimson Estates',
        'BluePeak Housing',
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
    stages = ['In Progress', 'Due to close', 'Portfolio review', 'Awaiting data', 'On hold']

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
    stages = ['Planning', 'Under review', 'Valuation in progress', 'Awaiting approval', 'Completed']
    regions = ['London', 'Manchester', 'Birmingham', 'Leeds', 'Glasgow', 'Bristol', 'Edinburgh']
    client_names = [
        'Sage Homes Limited',
        'Test Client UK UAT1',
        'Client_Tanveer1',
        'UAT_TestAcc_0609',
        'Northgate Properties',
        'Westfield Capital',
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
    customers = ['Sage Homes Limited', 'Crestline Logistics', 'BluePeak Housing', 'Test Client UK UAT1', 'Northgate Properties']
    routes = ['Southampton -> Birmingham', 'Leeds -> London', 'Manchester -> Bristol', 'Birmingham -> Glasgow', 'London -> Edinburgh', 'Leeds -> Manchester']
    statuses = ['In transit', 'Delayed', 'Delivered', 'Exception', 'Planned']
    rows: list[dict[str, Any]] = []
    for index in range(1, 661):
        customer = customers[(index - 1) % len(customers)]
        origin, destination = routes[(index - 1) % len(routes)].split(' -> ')
        status = statuses[(index - 1) % len(statuses)]
        delivery_day = 1 + ((index * 5) % 28)
        delivery_month = 1 + ((index * 2) % 12)
        delivery_year = 2024 + (index % 2)
        rows.append(
            {
                'shipment_id': f'SHP-{5000 + index}',
                'customer': customer,
                'route': routes[(index - 1) % len(routes)],
                'origin': origin,
                'destination': destination,
                'status': status,
                'delivery_date': f'{delivery_year}-{delivery_month:02d}-{delivery_day:02d}',
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


def load_table_cache() -> dict[str, list[dict[str, Any]]]:
    """Load all seed table rows from a single JSON cache file, building it once if absent."""
    cache_path = _resolve_table_cache_path()
    if cache_path.exists():
        with cache_path.open('r', encoding='utf-8') as handle:
            cache = json.load(handle)

        logistics_rows = cache.get('logistics_records', cache.get('opportunities', []))
        if logistics_rows and not any('record_ref' in row for row in logistics_rows[:1]):
            cache = _build_table_cache()
            with cache_path.open('w', encoding='utf-8') as handle:
                json.dump(cache, handle, indent=2)
            return cache
        return cache

    cache = _build_table_cache()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open('w', encoding='utf-8') as handle:
        json.dump(cache, handle, indent=2)
    return cache


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
            status,
            delivery_date,
            weight_kg,
            value_usd
        ) VALUES (
            :shipment_id,
            :customer,
            :route,
            :origin,
            :destination,
            :status,
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
                status TEXT NOT NULL,
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

        needs_reseed = any(current_counts[table] < target for table, target in minimum_targets.items())
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

