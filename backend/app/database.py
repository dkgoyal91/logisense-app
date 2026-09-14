from __future__ import annotations

import sqlite3
from pathlib import Path

from app.config import settings


def _resolve_database_path() -> Path:
    candidate = Path(settings.database_path)
    if candidate.is_absolute():
        return candidate
    return Path(__file__).resolve().parent.parent / candidate


def get_connection() -> sqlite3.Connection:
    database_path = _resolve_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def _seed_opportunities(connection: sqlite3.Connection) -> None:
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
    job_directors = [
        'James Harris',
        'Andrew Parling',
        'Rupert Driver',
        'John Barham',
        'Genine Terry',
        'Sarah Collins',
        'Michael Turner',
        'Priya Nair',
    ]
    owners = [
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

    rows: list[tuple] = []
    for index in range(1, 431):
        client_name = client_names[(index - 1) % len(client_names)]
        job_director = job_directors[(index - 1) % len(job_directors)]
        owner = owners[(index - 1) % len(owners)]
        region = regions[(index - 1) % len(regions)]
        status = stages[(index - 1) % len(stages)]
        number_of_properties = 8 + ((index * 13) % 211)
        value_usd = 150000 + (index * 18750)
        valuation_year = 2024 + (index % 3)
        month = 1 + ((index * 3) % 12)
        day = 1 + ((index * 7) % 27)
        valuation_date = f'{valuation_year}-{month:02d}-{day:02d}'
        rows.append(
            (
                f'SF-{24000 + index}',
                client_name,
                job_director,
                owner,
                number_of_properties,
                valuation_date,
                status,
                region,
                value_usd,
            )
        )

    connection.executemany(
        """
        INSERT INTO opportunities (
            salesforce_number,
            client_name,
            job_director,
            opportunity_owner,
            number_of_properties,
            valuation_date,
            status,
            region,
            value_usd
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _seed_jobs(connection: sqlite3.Connection) -> None:
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
    rows: list[tuple] = []
    for index in range(1, 281):
        client_name = client_names[(index - 1) % len(client_names)]
        opportunity_ref = f'SF-{24000 + index}'
        region = regions[(index - 1) % len(regions)]
        status = stages[(index - 1) % len(stages)]
        progress_pct = 18 + ((index * 17) % 82)
        days_open = 3 + ((index * 11) % 220)
        total_properties = 12 + ((index * 7) % 320)
        current_stage = stages[(index + 1) % len(stages)]
        rows.append((f'JOB-{1000 + index}', opportunity_ref, client_name, region, status, progress_pct, days_open, total_properties, current_stage))
    connection.executemany(
        """
        INSERT INTO jobs (
            job_id,
            opportunity_ref,
            client_name,
            region,
            status,
            progress_pct,
            days_open,
            total_properties,
            current_stage
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _seed_shipments(connection: sqlite3.Connection) -> None:
    customers = ['Sage Homes Limited', 'Crestline Logistics', 'BluePeak Housing', 'Test Client UK UAT1', 'Northgate Properties']
    routes = ['Southampton -> Birmingham', 'Leeds -> London', 'Manchester -> Bristol', 'Birmingham -> Glasgow', 'London -> Edinburgh', 'Leeds -> Manchester']
    statuses = ['In transit', 'Delayed', 'Delivered', 'Exception', 'Planned']
    rows: list[tuple] = []
    for index in range(1, 521):
        customer = customers[(index - 1) % len(customers)]
        origin, destination = routes[(index - 1) % len(routes)].split(' -> ')
        status = statuses[(index - 1) % len(statuses)]
        delivery_day = 1 + ((index * 5) % 28)
        delivery_month = 1 + ((index * 2) % 12)
        delivery_year = 2024 + (index % 2)
        rows.append(
            (
                f'SHP-{5000 + index}',
                customer,
                routes[(index - 1) % len(routes)],
                origin,
                destination,
                status,
                f'{delivery_year}-{delivery_month:02d}-{delivery_day:02d}',
                180 + ((index * 37) % 2260),
                1500 + ((index * 213) % 85000),
            )
        )
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
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _seed_vehicles(connection: sqlite3.Connection) -> None:
    depots = ['London Central', 'Manchester North', 'Birmingham Yard', 'Leeds Depot', 'Glasgow Hub']
    statuses = ['Available', 'In use', 'Maintenance', 'Idle']
    rows: list[tuple] = []
    for index in range(1, 96):
        depot = depots[(index - 1) % len(depots)]
        status = statuses[(index - 1) % len(statuses)]
        utilization = 36 + ((index * 7) % 64)
        service_month = 1 + ((index * 2) % 12)
        service_year = 2023 + (index % 3)
        rows.append(
            (
                f'VEH-{800 + index}',
                depot,
                status,
                utilization,
                f'{service_year}-{service_month:02d}-15',
            )
        )
    connection.executemany(
        """
        INSERT INTO vehicles (
            vehicle_id,
            depot,
            status,
            utilization_pct,
            last_service_date
        ) VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )


def initialize_database() -> None:
    database_path = _resolve_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                salesforce_number TEXT UNIQUE NOT NULL,
                client_name TEXT NOT NULL,
                job_director TEXT NOT NULL,
                opportunity_owner TEXT NOT NULL,
                number_of_properties INTEGER NOT NULL,
                valuation_date TEXT NOT NULL,
                status TEXT NOT NULL,
                region TEXT NOT NULL,
                value_usd INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE NOT NULL,
                opportunity_ref TEXT NOT NULL,
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
            'opportunities': 430,
            'jobs': 280,
            'shipments': 520,
            'vehicles': 95,
        }
        current_counts = {
            table: connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
            for table in minimum_targets
        }

        needs_reseed = any(current_counts[table] < target for table, target in minimum_targets.items())
        if needs_reseed:
            connection.execute('DELETE FROM opportunities')
            connection.execute('DELETE FROM jobs')
            connection.execute('DELETE FROM shipments')
            connection.execute('DELETE FROM vehicles')
            connection.execute("DELETE FROM sqlite_sequence WHERE name IN ('opportunities', 'jobs', 'shipments', 'vehicles')")

        if needs_reseed or current_counts['opportunities'] == 0:
            _seed_opportunities(connection)
        if needs_reseed or current_counts['jobs'] == 0:
            _seed_jobs(connection)
        if needs_reseed or current_counts['shipments'] == 0:
            _seed_shipments(connection)
        if needs_reseed or current_counts['vehicles'] == 0:
            _seed_vehicles(connection)

        connection.commit()
    finally:
        connection.close()
