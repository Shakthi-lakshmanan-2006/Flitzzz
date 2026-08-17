
import os
import sys
from pathlib import Path
from datetime import time

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from psycopg2.extras import execute_values


# ============================================================
# FLITZZ - ROBUST CSV -> POSTGRESQL LOADER
# ============================================================
#
# This version fixes the NaN source_row_id problem by:
#   1. Filtering invalid flight rows FIRST.
#   2. reset_index(drop=True) after filtering.
#   3. Re-creating source_row_id AFTER filtering.
#   4. Never converting a NaN source_row_id to int.
#
# It also:
#   - Uses small execute_values batches instead of to_sql(method="multi")
#   - Handles negative delays required by the supplied schema
#   - Maps generated PostgreSQL flight_id safely
#   - Avoids route_history / airline_history UNIQUE conflicts with
#     ON CONFLICT DO UPDATE
# ============================================================


# -----------------------------
# ENVIRONMENT
# -----------------------------

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv(
    "DB_NAME",
    "airline_disruption_management"
)
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(
    os.getenv(
        "FLITZZ_DATA_DIR",
        str(BASE_DIR / "data")
    )
)

AIRLINES_FILE = DATA_DIR / "airlines.csv"
AIRPORTS_FILE = DATA_DIR / "airports.csv"
FLIGHTS_FILE = DATA_DIR / "flights.csv"

CHUNK_SIZE = int(
    os.getenv("FLITZZ_CHUNK_SIZE", "25000")
)

INSERT_PAGE_SIZE = int(
    os.getenv("FLITZZ_INSERT_PAGE_SIZE", "250")
)

DATABASE_URL = (
    f"postgresql+psycopg2://"
    f"{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

if not DB_PASSWORD:
    raise RuntimeError(
        "DB_PASSWORD is missing from .env"
    )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)


# ============================================================
# LOGGING
# ============================================================

def info(message):
    print(f"[INFO] {message}")


def ok(message):
    print(f"[OK]   {message}")


def warn(message):
    print(f"[WARN] {message}")


# ============================================================
# HELPERS
# ============================================================

def clean_text(series):
    return (
        series.astype("string")
        .str.strip()
        .replace({
            "": pd.NA,
            "nan": pd.NA,
            "NaN": pd.NA,
            "NULL": pd.NA,
            "null": pd.NA,
        })
    )


def numeric(series):
    return pd.to_numeric(
        series,
        errors="coerce"
    )


def to_bool(series):
    return (
        series.astype("string")
        .str.strip()
        .str.lower()
        .map({
            "true": True,
            "false": False,
            "1": True,
            "0": False,
            "yes": True,
            "no": False,
        })
        .fillna(False)
    )


def hhmm_to_time(value):
    if pd.isna(value):
        return None

    try:
        value = int(float(value))

        hour = value // 100
        minute = value % 100

        if not (
            0 <= hour <= 23
            and 0 <= minute <= 59
        ):
            return None

        return time(
            hour,
            minute
        )

    except (
        ValueError,
        TypeError
    ):
        return None


def safe_value(value):
    if value is None:
        return None

    if isinstance(value, float):
        if np.isnan(value) or np.isinf(value):
            return None

    if isinstance(value, np.generic):
        return value.item()

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    return value


# ============================================================
# DATABASE
# ============================================================

def test_database():

    with engine.connect() as conn:

        version = conn.execute(
            text("SELECT version();")
        ).scalar()

    ok(
        "PostgreSQL connection successful."
    )

    print(version)


def check_files():

    files = [
        AIRLINES_FILE,
        AIRPORTS_FILE,
        FLIGHTS_FILE,
    ]

    for file in files:

        if not file.exists():

            raise FileNotFoundError(
                f"File not found:\n{file}"
            )

        size_mb = (
            file.stat().st_size
            / (1024 * 1024)
        )

        ok(
            f"{file.name} found "
            f"({size_mb:.2f} MB)"
        )


REQUIRED_TABLES = [
    "aircraft",
    "airline_history",
    "airlines",
    "airports",
    "bookings",
    "crew_assignments",
    "crew_members",
    "disruption_policies",
    "flight_delay",
    "flight_inventory",
    "flight_predictions",
    "flights",
    "notifications",
    "passengers",
    "rebooking_recommendations",
    "route_history",
]


def check_tables():

    query = text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
    """)

    with engine.connect() as conn:

        existing = {
            row[0]
            for row in conn.execute(query)
        }

    missing = [
        table
        for table in REQUIRED_TABLES
        if table not in existing
    ]

    if missing:

        raise RuntimeError(
            "These required tables are missing:\n"
            + "\n".join(
                f"  - {x}"
                for x in missing
            )
        )

    ok(
        "All required tables exist."
    )


# ============================================================
# CLEAR SOURCE DATA
# ============================================================

def clear_source_tables():

    answer = input(
        "\nThis will delete existing source data from:\n"
        "airlines, airports, aircraft, flights,\n"
        "flight_delay, route_history and airline_history.\n\n"
        "Type YES to continue: "
    )

    if answer.strip().upper() != "YES":

        print("Cancelled.")
        sys.exit(0)

    with engine.begin() as conn:

        conn.execute(
            text("""
                TRUNCATE TABLE
                    flight_delay,
                    route_history,
                    airline_history,
                    flights,
                    aircraft,
                    airlines,
                    airports
                RESTART IDENTITY CASCADE;
            """)
        )

    ok(
        "Source tables cleared."
    )


# ============================================================
# INSERT HELPERS
# ============================================================

def insert_rows(
    table,
    columns,
    rows,
    page_size=INSERT_PAGE_SIZE
):

    if not rows:
        return 0

    column_sql = ", ".join(
        f'"{column}"'
        for column in columns
    )

    sql = (
        f'INSERT INTO "{table}" '
        f'({column_sql}) VALUES %s'
    )

    prepared = [
        tuple(
            safe_value(value)
            for value in row
        )
        for row in rows
    ]

    raw = engine.raw_connection()

    try:

        cursor = raw.cursor()

        execute_values(
            cursor,
            sql,
            prepared,
            page_size=page_size
        )

        raw.commit()

        cursor.close()

    except Exception:

        raw.rollback()
        raise

    finally:

        raw.close()

    return len(prepared)


# ============================================================
# AIRLINES
# ============================================================

def load_airlines():

    info(
        "Loading airlines.csv..."
    )

    df = pd.read_csv(
        AIRLINES_FILE,
        dtype="string"
    )

    df.columns = [
        column.strip().upper()
        for column in df.columns
    ]

    required = [
        "IATA_CODE",
        "AIRLINE",
    ]

    for column in required:

        if column not in df.columns:

            raise RuntimeError(
                f"airlines.csv missing {column}"
            )

    df["IATA_CODE"] = clean_text(
        df["IATA_CODE"]
    )

    df["AIRLINE"] = clean_text(
        df["AIRLINE"]
    )

    df = (
        df.dropna(
            subset=[
                "IATA_CODE",
                "AIRLINE",
            ]
        )
        .drop_duplicates(
            subset=["IATA_CODE"]
        )
    )

    rows = []

    for row in df.itertuples(
        index=False
    ):

        rows.append((
            str(row.IATA_CODE)[:3],
            str(row.AIRLINE)[:150],
            "USA",
            True,
        ))

    insert_rows(
        "airlines",
        [
            "iata_code",
            "airline_name",
            "country",
            "is_active",
        ],
        rows,
    )

    ok(
        f"Loaded {len(rows):,} airlines."
    )


def airline_map():

    with engine.connect() as conn:

        rows = conn.execute(
            text("""
                SELECT
                    airline_id,
                    iata_code
                FROM airlines
            """)
        ).fetchall()

    return {
        str(row.iata_code):
            row.airline_id
        for row in rows
    }


# ============================================================
# AIRPORTS
# ============================================================

def load_airports():

    info(
        "Loading airports.csv..."
    )

    df = pd.read_csv(
        AIRPORTS_FILE,
        dtype="string"
    )

    df.columns = [
        column.strip().upper()
        for column in df.columns
    ]

    required = [
        "IATA_CODE",
        "AIRPORT",
        "CITY",
        "STATE",
        "COUNTRY",
        "LATITUDE",
        "LONGITUDE",
    ]

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:

        raise RuntimeError(
            "airports.csv missing: "
            + ", ".join(missing)
        )

    for column in [
        "IATA_CODE",
        "AIRPORT",
        "CITY",
        "STATE",
        "COUNTRY",
    ]:

        df[column] = clean_text(
            df[column]
        )

    df["LATITUDE"] = numeric(
        df["LATITUDE"]
    )

    df["LONGITUDE"] = numeric(
        df["LONGITUDE"]
    )

    # Keep only values allowed by schema.
    df.loc[
        ~df["LATITUDE"].between(
            -90,
            90
        ),
        "LATITUDE"
    ] = np.nan

    df.loc[
        ~df["LONGITUDE"].between(
            -180,
            180
        ),
        "LONGITUDE"
    ] = np.nan

    df = (
        df.dropna(
            subset=[
                "IATA_CODE",
                "AIRPORT",
            ]
        )
        .drop_duplicates(
            subset=["IATA_CODE"]
        )
    )

    rows = []

    for row in df.itertuples(
        index=False
    ):

        rows.append((
            str(row.IATA_CODE)[:3],
            str(row.AIRPORT)[:200],
            None if pd.isna(row.CITY)
            else str(row.CITY)[:100],
            None if pd.isna(row.STATE)
            else str(row.STATE)[:100],
            None if pd.isna(row.COUNTRY)
            else str(row.COUNTRY)[:100],
            None if pd.isna(row.LATITUDE)
            else float(row.LATITUDE),
            None if pd.isna(row.LONGITUDE)
            else float(row.LONGITUDE),
        ))

    insert_rows(
        "airports",
        [
            "iata_code",
            "airport_name",
            "city",
            "state",
            "country",
            "latitude",
            "longitude",
        ],
        rows,
    )

    ok(
        f"Loaded {len(rows):,} airports."
    )


def airport_map():

    with engine.connect() as conn:

        rows = conn.execute(
            text("""
                SELECT
                    airport_id,
                    iata_code
                FROM airports
            """)
        ).fetchall()

    return {
        str(row.iata_code):
            row.airport_id
        for row in rows
    }


# ============================================================
# AIRCRAFT
# ============================================================

def load_aircraft():

    info(
        "Loading aircraft from flights.csv..."
    )

    df = pd.read_csv(
        FLIGHTS_FILE,
        usecols=[
            "TAIL_NUMBER",
            "AIRLINE",
        ],
        dtype={
            "TAIL_NUMBER": "string",
            "AIRLINE": "string",
        }
    )

    df["TAIL_NUMBER"] = clean_text(
        df["TAIL_NUMBER"]
    )

    df["AIRLINE"] = clean_text(
        df["AIRLINE"]
    )

    df = (
        df.dropna(
            subset=["TAIL_NUMBER"]
        )
        .drop_duplicates(
            subset=["TAIL_NUMBER"]
        )
    )

    a_map = airline_map()

    rows = []

    for row in df.itertuples(
        index=False
    ):

        rows.append((
            str(row.TAIL_NUMBER)[:20],
            a_map.get(
                str(row.AIRLINE)
            ),
            "ACTIVE",
        ))

    insert_rows(
        "aircraft",
        [
            "tail_number",
            "airline_id",
            "status",
        ],
        rows,
    )

    ok(
        f"Loaded {len(rows):,} aircraft."
    )


def aircraft_map():

    with engine.connect() as conn:

        rows = conn.execute(
            text("""
                SELECT
                    aircraft_id,
                    tail_number
                FROM aircraft
            """)
        ).fetchall()

    return {
        str(row.tail_number):
            row.aircraft_id
        for row in rows
    }


# ============================================================
# FLIGHT PREPARATION
# ============================================================

def prepare_chunk(
    chunk,
    a_map,
    ap_map,
    ac_map,
    source_start,
):

    # --------------------------------------------------------
    # Normalize CSV column names
    # --------------------------------------------------------

    chunk.columns = [
        column.strip().upper()
        for column in chunk.columns
    ]

    # --------------------------------------------------------
    # Clean text fields
    # --------------------------------------------------------

    for column in [
        "AIRLINE",
        "FLIGHT_NUMBER",
        "TAIL_NUMBER",
        "ORIGIN_AIRPORT",
        "DESTINATION_AIRPORT",
    ]:

        chunk[column] = clean_text(
            chunk[column]
        )

    # --------------------------------------------------------
    # Numeric date fields
    # --------------------------------------------------------

    for column in [
        "YEAR",
        "MONTH",
        "DAY",
        "DAY_OF_WEEK",
        "SCHEDULED_DEPARTURE",
        "SCHEDULED_ARRIVAL",
        "DEPARTURE_TIME",
        "ARRIVAL_TIME",
        "WHEELS_OFF",
        "WHEELS_ON",
        "SCHEDULED_TIME",
        "ELAPSED_TIME",
        "AIR_TIME",
        "TAXI_OUT",
        "TAXI_IN",
        "DISTANCE",
        "DEPARTURE_DELAY",
        "ARRIVAL_DELAY",
    ]:

        if column in chunk.columns:

            chunk[column] = numeric(
                chunk[column]
            )

    # --------------------------------------------------------
    # Foreign key mapping
    # --------------------------------------------------------

    chunk["airline_id"] = (
        chunk["AIRLINE"].map(a_map)
    )

    chunk["origin_airport_id"] = (
        chunk["ORIGIN_AIRPORT"].map(ap_map)
    )

    chunk["destination_airport_id"] = (
        chunk["DESTINATION_AIRPORT"].map(ap_map)
    )

    chunk["aircraft_id"] = (
        chunk["TAIL_NUMBER"].map(ac_map)
    )

    # --------------------------------------------------------
    # Date
    # --------------------------------------------------------

    chunk["flight_date"] = pd.to_datetime(
        dict(
            year=chunk["YEAR"],
            month=chunk["MONTH"],
            day=chunk["DAY"],
        ),
        errors="coerce"
    ).dt.date

    # --------------------------------------------------------
    # IMPORTANT FIX:
    #
    # Filter FIRST.
    # Reset the index.
    # THEN create source_row_id.
    #
    # The previous version created source_row_id before
    # filtering and later hit NaN during the flight-id lookup.
    # --------------------------------------------------------

    required_mask = (
        chunk["airline_id"].notna()
        & chunk["origin_airport_id"].notna()
        & chunk["destination_airport_id"].notna()
        & chunk["FLIGHT_NUMBER"].notna()
        & chunk["flight_date"].notna()
    )

    dropped = int(
        (~required_mask).sum()
    )

    if dropped:

        warn(
            f"Dropping {dropped:,} invalid "
            "flight rows in this chunk."
        )

    chunk = (
        chunk.loc[required_mask]
        .reset_index(drop=True)
    )

    # NOW source_row_id can never be NaN.
    chunk["source_row_id"] = np.arange(
        source_start,
        source_start + len(chunk),
        dtype=np.int64
    )

    # --------------------------------------------------------
    # Boolean values
    # --------------------------------------------------------

    chunk["DIVERTED"] = to_bool(
        chunk["DIVERTED"]
    )

    chunk["CANCELLED"] = to_bool(
        chunk["CANCELLED"]
    )

    # --------------------------------------------------------
    # Route
    # --------------------------------------------------------

    chunk["ROUTE"] = (
        chunk["ORIGIN_AIRPORT"]
        + "_"
        + chunk["DESTINATION_AIRPORT"]
    )

    # --------------------------------------------------------
    # Time fields
    # --------------------------------------------------------

    chunk["scheduled_departure"] = (
        chunk["SCHEDULED_DEPARTURE"]
        .map(hhmm_to_time)
    )

    chunk["scheduled_arrival"] = (
        chunk["SCHEDULED_ARRIVAL"]
        .map(hhmm_to_time)
    )

    chunk["departure_time"] = (
        chunk["DEPARTURE_TIME"]
        .map(hhmm_to_time)
    )

    chunk["arrival_time"] = (
        chunk["ARRIVAL_TIME"]
        .map(hhmm_to_time)
    )

    chunk["wheels_off"] = (
        chunk["WHEELS_OFF"]
        .map(hhmm_to_time)
    )

    chunk["wheels_on"] = (
        chunk["WHEELS_ON"]
        .map(hhmm_to_time)
    )

    # --------------------------------------------------------
    # Time features
    # --------------------------------------------------------

    chunk["departure_hour"] = (
        chunk["SCHEDULED_DEPARTURE"]
        // 100
    )

    chunk["departure_minute"] = (
        chunk["SCHEDULED_DEPARTURE"]
        % 100
    )

    chunk["arrival_hour"] = (
        chunk["SCHEDULED_ARRIVAL"]
        // 100
    )

    chunk["arrival_minute"] = (
        chunk["SCHEDULED_ARRIVAL"]
        % 100
    )

    chunk["is_weekend"] = (
        chunk["DAY_OF_WEEK"].isin(
            [6, 7]
        )
    )

    def get_season(month):

        if pd.isna(month):
            return None

        month = int(month)

        if month in [12, 1, 2]:
            return "Winter"

        if month in [3, 4, 5]:
            return "Spring"

        if month in [6, 7, 8]:
            return "Summer"

        return "Autumn"

    def get_period(hour):

        if pd.isna(hour):
            return None

        hour = int(hour)

        if 5 <= hour <= 11:
            return "Morning"

        if 12 <= hour <= 16:
            return "Afternoon"

        if 17 <= hour <= 20:
            return "Evening"

        return "Night"

    chunk["season"] = (
        chunk["MONTH"].map(
            get_season
        )
    )

    chunk["departure_period"] = (
        chunk["departure_hour"]
        .map(get_period)
    )

    # --------------------------------------------------------
    # Flight datetime
    # --------------------------------------------------------

    base_datetime = pd.to_datetime(
        dict(
            year=chunk["YEAR"],
            month=chunk["MONTH"],
            day=chunk["DAY"],
        ),
        errors="coerce"
    )

    hours = (
        chunk["SCHEDULED_DEPARTURE"]
        // 100
    )

    minutes = (
        chunk["SCHEDULED_DEPARTURE"]
        % 100
    )

    chunk["flight_datetime"] = (
        base_datetime
        + pd.to_timedelta(
            hours,
            unit="h"
        )
        + pd.to_timedelta(
            minutes,
            unit="m"
        )
    )

    # --------------------------------------------------------
    # Delay values
    #
    # DB schema requires >= 0.
    # The raw CSV contains negative values for early flights.
    # --------------------------------------------------------

    departure_delay = (
        chunk["DEPARTURE_DELAY"]
        .fillna(0)
        .clip(lower=0)
        .round()
        .astype(np.int64)
    )

    arrival_delay = (
        chunk["ARRIVAL_DELAY"]
        .fillna(0)
        .clip(lower=0)
        .round()
        .astype(np.int64)
    )

    delayed_15 = (
        chunk["ARRIVAL_DELAY"]
        .fillna(0)
        > 15
    )

    def status(row):

        if row["cancelled"]:
            return "CANCELLED"

        if row["diverted"]:
            return "DIVERTED"

        if row["arrival_delay"] <= 0:
            return "ON_TIME"

        if row["arrival_delay"] <= 15:
            return "MINOR_DELAY"

        return "MAJOR_DELAY"

    status_df = pd.DataFrame({
        "cancelled":
            chunk["CANCELLED"],
        "diverted":
            chunk["DIVERTED"],
        "arrival_delay":
            arrival_delay,
    })

    delay_status = (
        status_df
        .apply(status, axis=1)
    )

    # --------------------------------------------------------
    # Flights table
    # --------------------------------------------------------

    flights = pd.DataFrame({
        "source_row_id":
            chunk["source_row_id"].astype(np.int64),

        "airline_id":
            chunk["airline_id"].astype(np.int64),

        "aircraft_id":
            chunk["aircraft_id"].astype(
                "Int64"
            ),

        "flight_number":
            chunk["FLIGHT_NUMBER"],

        "flight_date":
            chunk["flight_date"],

        "year":
            chunk["YEAR"].astype(np.int64),

        "month":
            chunk["MONTH"].astype(np.int64),

        "day":
            chunk["DAY"].astype(np.int64),

        "day_of_week":
            chunk["DAY_OF_WEEK"].astype(np.int64),

        "origin_airport_id":
            chunk["origin_airport_id"].astype(np.int64),

        "destination_airport_id":
            chunk["destination_airport_id"].astype(np.int64),

        "scheduled_departure":
            chunk["scheduled_departure"],

        "scheduled_arrival":
            chunk["scheduled_arrival"],

        "departure_time":
            chunk["departure_time"],

        "arrival_time":
            chunk["arrival_time"],

        "scheduled_time_minutes":
            chunk["SCHEDULED_TIME"],

        "elapsed_time_minutes":
            chunk["ELAPSED_TIME"],

        "air_time_minutes":
            chunk["AIR_TIME"],

        "taxi_out_minutes":
            chunk["TAXI_OUT"],

        "taxi_in_minutes":
            chunk["TAXI_IN"],

        "wheels_off":
            chunk["wheels_off"],

        "wheels_on":
            chunk["wheels_on"],

        "distance_miles":
            chunk["DISTANCE"],

        "diverted":
            chunk["DIVERTED"],

        "cancelled":
            chunk["CANCELLED"],

        "departure_hour":
            chunk["departure_hour"],

        "departure_minute":
            chunk["departure_minute"],

        "arrival_hour":
            chunk["arrival_hour"],

        "arrival_minute":
            chunk["arrival_minute"],

        "is_weekend":
            chunk["is_weekend"],

        "season":
            chunk["season"],

        "departure_period":
            chunk["departure_period"],

        "route":
            chunk["ROUTE"],

        "flight_datetime":
            chunk["flight_datetime"],
    })

    # --------------------------------------------------------
    # Delay table
    # --------------------------------------------------------

    flight_delay = pd.DataFrame({
        "source_row_id":
            chunk["source_row_id"].astype(np.int64),

        "departure_delay_minutes":
            departure_delay,

        "arrival_delay_minutes":
            arrival_delay,

        "delayed_15":
            delayed_15.astype(bool),

        "delay_status":
            delay_status,

        "delay_category":
            delay_status,
    })

    # --------------------------------------------------------
    # Route history
    #
    # Build one row per route/date.
    # This is necessary because the supplied schema has a UNIQUE
    # constraint on origin + destination + observation_date.
    # --------------------------------------------------------

    route_previous_flights = (
        numeric(
            chunk["ROUTE_PREVIOUS_FLIGHTS"]
        )
        .fillna(0)
        .clip(lower=0)
        .astype(np.int64)
    )

    route_previous_delays = (
        numeric(
            chunk["ROUTE_PREVIOUS_DELAYS"]
        )
        .fillna(0)
        .clip(lower=0)
    )

    route_previous_delays = np.minimum(
        route_previous_delays,
        route_previous_flights
    ).astype(np.int64)

    route_rate = (
        numeric(
            chunk["ROUTE_DELAY_RATE"]
        )
        .fillna(0)
        .clip(0, 1)
    )

    route_history = pd.DataFrame({
        "origin_airport_id":
            chunk["origin_airport_id"],

        "destination_airport_id":
            chunk["destination_airport_id"],

        "route_code":
            chunk["ROUTE"],

        "observation_date":
            chunk["flight_date"],

        "previous_flights":
            route_previous_flights,

        "previous_delays":
            route_previous_delays,

        "delay_rate":
            route_rate,

        "average_delay_minutes":
            arrival_delay,
    })

    route_history = (
        route_history
        .groupby(
            [
                "origin_airport_id",
                "destination_airport_id",
                "observation_date",
            ],
            as_index=False
        )
        .agg({
            "route_code": "first",
            "previous_flights": "max",
            "previous_delays": "max",
            "delay_rate": "mean",
            "average_delay_minutes": "mean",
        })
    )

    # --------------------------------------------------------
    # Airline history
    # --------------------------------------------------------

    airline_previous_flights = (
        numeric(
            chunk["AIRLINE_PREVIOUS_FLIGHTS"]
        )
        .fillna(0)
        .clip(lower=0)
        .astype(np.int64)
    )

    airline_previous_delays = (
        numeric(
            chunk["AIRLINE_PREVIOUS_DELAYS"]
        )
        .fillna(0)
        .clip(lower=0)
    )

    airline_previous_delays = np.minimum(
        airline_previous_delays,
        airline_previous_flights
    ).astype(np.int64)

    airline_rate = (
        numeric(
            chunk["AIRLINE_DELAY_RATE"]
        )
        .fillna(0)
        .clip(0, 1)
    )

    airline_history = pd.DataFrame({
        "airline_id":
            chunk["airline_id"],

        "observation_date":
            chunk["flight_date"],

        "previous_flights":
            airline_previous_flights,

        "previous_delays":
            airline_previous_delays,

        "delay_rate":
            airline_rate,

        "average_delay_minutes":
            arrival_delay,
    })

    airline_history = (
        airline_history
        .groupby(
            [
                "airline_id",
                "observation_date",
            ],
            as_index=False
        )
        .agg({
            "previous_flights": "max",
            "previous_delays": "max",
            "delay_rate": "mean",
            "average_delay_minutes": "mean",
        })
    )

    return (
        flights,
        flight_delay,
        route_history,
        airline_history,
    )


# ============================================================
# INSERT FLIGHT CHUNK
# ============================================================

def insert_flight_chunk(
    flights,
    flight_delay,
    route_history,
    airline_history,
):

    if flights.empty:
        return 0

    # --------------------------------------------------------
    # HARD SAFETY CHECK
    # --------------------------------------------------------

    if flights["source_row_id"].isna().any():

        raise RuntimeError(
            "Internal error: source_row_id contains NaN "
            "after filtering. This should never happen."
        )

    # --------------------------------------------------------
    # Insert flights
    # --------------------------------------------------------

    flight_columns = list(
        flights.columns
    )

    flight_rows = [
        tuple(row)
        for row in flights.itertuples(
            index=False,
            name=None
        )
    ]

    insert_rows(
        "flights",
        flight_columns,
        flight_rows,
    )

    # --------------------------------------------------------
    # Resolve generated PostgreSQL flight IDs
    #
    # IMPORTANT:
    # Never do int(NaN).
    # --------------------------------------------------------

    source_ids = [
        int(value)
        for value in
        flights["source_row_id"]
        .tolist()
        if pd.notna(value)
    ]

    id_map = {}

    for start in range(
        0,
        len(source_ids),
        1000
    ):

        batch = source_ids[
            start:start + 1000
        ]

        placeholders = ", ".join(
            f":p{i}"
            for i in range(
                len(batch)
            )
        )

        params = {
            f"p{i}": value
            for i, value
            in enumerate(batch)
        }

        query = text(
            f"""
            SELECT
                flight_id,
                source_row_id
            FROM flights
            WHERE source_row_id IN (
                {placeholders}
            )
            """
        )

        with engine.connect() as conn:

            rows = conn.execute(
                query,
                params
            ).fetchall()

        for row in rows:

            if (
                row.source_row_id
                is not None
            ):

                id_map[
                    int(row.source_row_id)
                ] = int(row.flight_id)

    # --------------------------------------------------------
    # Flight delay
    # --------------------------------------------------------

    delay_rows = []

    for row in flight_delay.itertuples(
        index=False
    ):

        source_id = (
            int(row.source_row_id)
        )

        flight_id = id_map.get(
            source_id
        )

        if flight_id is None:

            warn(
                f"No flight_id found for "
                f"source_row_id={source_id}"
            )

            continue

        delay_rows.append((
            flight_id,
            int(
                row.departure_delay_minutes
            ),
            int(
                row.arrival_delay_minutes
            ),
            bool(row.delayed_15),
            row.delay_status,
            row.delay_category,
        ))

    insert_rows(
        "flight_delay",
        [
            "flight_id",
            "departure_delay_minutes",
            "arrival_delay_minutes",
            "delayed_15",
            "delay_status",
            "delay_category",
        ],
        delay_rows,
    )

    # --------------------------------------------------------
    # Route history
    #
    # ON CONFLICT prevents failure when the same route/date
    # appears in another CSV chunk.
    # --------------------------------------------------------

    route_rows = [
        (
            int(row.origin_airport_id),
            int(row.destination_airport_id),
            str(row.route_code)[:10],
            row.observation_date,
            int(row.previous_flights),
            int(row.previous_delays),
            float(row.delay_rate),
            float(row.average_delay_minutes),
        )
        for row in route_history.itertuples(
            index=False
        )
    ]

    if route_rows:

        raw = engine.raw_connection()

        try:

            cursor = raw.cursor()

            execute_values(
                cursor,
                """
                INSERT INTO route_history (
                    origin_airport_id,
                    destination_airport_id,
                    route_code,
                    observation_date,
                    previous_flights,
                    previous_delays,
                    delay_rate,
                    average_delay_minutes
                )
                VALUES %s
                ON CONFLICT (
                    origin_airport_id,
                    destination_airport_id,
                    observation_date
                )
                DO UPDATE SET
                    route_code =
                        EXCLUDED.route_code,
                    previous_flights =
                        GREATEST(
                            route_history.previous_flights,
                            EXCLUDED.previous_flights
                        ),
                    previous_delays =
                        GREATEST(
                            route_history.previous_delays,
                            EXCLUDED.previous_delays
                        ),
                    delay_rate =
                        EXCLUDED.delay_rate,
                    average_delay_minutes =
                        EXCLUDED.average_delay_minutes
                """,
                route_rows,
                page_size=INSERT_PAGE_SIZE
            )

            raw.commit()
            cursor.close()

        except Exception:

            raw.rollback()
            raise

        finally:

            raw.close()

    # --------------------------------------------------------
    # Airline history
    # --------------------------------------------------------

    airline_rows = [
        (
            int(row.airline_id),
            row.observation_date,
            int(row.previous_flights),
            int(row.previous_delays),
            float(row.delay_rate),
            float(row.average_delay_minutes),
        )
        for row in airline_history.itertuples(
            index=False
        )
    ]

    if airline_rows:

        raw = engine.raw_connection()

        try:

            cursor = raw.cursor()

            execute_values(
                cursor,
                """
                INSERT INTO airline_history (
                    airline_id,
                    observation_date,
                    previous_flights,
                    previous_delays,
                    delay_rate,
                    average_delay_minutes
                )
                VALUES %s
                ON CONFLICT (
                    airline_id,
                    observation_date
                )
                DO UPDATE SET
                    previous_flights =
                        GREATEST(
                            airline_history.previous_flights,
                            EXCLUDED.previous_flights
                        ),
                    previous_delays =
                        GREATEST(
                            airline_history.previous_delays,
                            EXCLUDED.previous_delays
                        ),
                    delay_rate =
                        EXCLUDED.delay_rate,
                    average_delay_minutes =
                        EXCLUDED.average_delay_minutes
                """,
                airline_rows,
                page_size=INSERT_PAGE_SIZE
            )

            raw.commit()
            cursor.close()

        except Exception:

            raw.rollback()
            raise

        finally:

            raw.close()

    return len(flights)


# ============================================================
# LOAD FLIGHTS
# ============================================================

def load_flights():

    info(
        "Starting flights.csv ingestion..."
    )

    a_map = airline_map()
    ap_map = airport_map()
    ac_map = aircraft_map()

    total_loaded = 0
    raw_rows_seen = 0
    chunk_number = 0

    dtype = {
        "AIRLINE": "string",
        "FLIGHT_NUMBER": "string",
        "TAIL_NUMBER": "string",
        "ORIGIN_AIRPORT": "string",
        "DESTINATION_AIRPORT": "string",
    }

    for chunk in pd.read_csv(
        FLIGHTS_FILE,
        dtype=dtype,
        chunksize=CHUNK_SIZE,
        low_memory=False,
    ):

        chunk_number += 1

        # Raw CSV position.
        raw_start = (
            raw_rows_seen + 1
        )

        raw_rows_seen += len(chunk)

        (
            flights,
            flight_delay,
            route_history,
            airline_history,
        ) = prepare_chunk(
            chunk,
            a_map,
            ap_map,
            ac_map,
            raw_start,
        )

        inserted = (
            insert_flight_chunk(
                flights,
                flight_delay,
                route_history,
                airline_history,
            )
        )

        total_loaded += inserted

        print(
            f"[INFO] Chunk {chunk_number:,} | "
            f"Raw rows seen: {raw_rows_seen:,} | "
            f"Flights loaded: {total_loaded:,}"
        )

    ok(
        f"Finished loading "
        f"{total_loaded:,} flights."
    )


# ============================================================
# POLICIES
# ============================================================

def seed_policies():

    info(
        "Checking disruption policies..."
    )

    with engine.connect() as conn:

        count = conn.execute(
            text(
                "SELECT COUNT(*) "
                "FROM disruption_policies"
            )
        ).scalar()

    if count:

        ok(
            f"disruption_policies already has "
            f"{count:,} rows."
        )

        return

    with engine.begin() as conn:

        conn.execute(
            text("""
                INSERT INTO disruption_policies (
                    policy_name,
                    minimum_delay_probability,
                    minimum_expected_delay_minutes,
                    action,
                    auto_rebooking,
                    auto_notification,
                    manual_review_required
                )
                VALUES
                (
                    'Low Risk Monitoring',
                    0.00,
                    0,
                    'MONITOR',
                    FALSE,
                    FALSE,
                    FALSE
                ),
                (
                    'Medium Risk Manual Review',
                    0.50,
                    15,
                    'MANUAL_REVIEW',
                    FALSE,
                    FALSE,
                    TRUE
                ),
                (
                    'High Risk Automatic Intervention',
                    0.75,
                    30,
                    'AUTO_INTERVENTION',
                    TRUE,
                    TRUE,
                    FALSE
                )
            """)
        )

    ok(
        "Disruption policies seeded."
    )


# ============================================================
# VALIDATION
# ============================================================

def table_count(table):

    with engine.connect() as conn:

        return conn.execute(
            text(
                f'SELECT COUNT(*) '
                f'FROM "{table}"'
            )
        ).scalar()


def validate():

    print()
    print("=" * 78)
    print("FLITZZ DATABASE VALIDATION")
    print("=" * 78)

    tables = [
        "airlines",
        "airports",
        "aircraft",
        "flights",
        "flight_delay",
        "route_history",
        "airline_history",
        "disruption_policies",
    ]

    for table in tables:

        print(
            f"{table:25s}: "
            f"{table_count(table):,}"
        )

    print()
    print("Integrity checks:")

    checks = {
        "invalid airline FK": """
            SELECT COUNT(*)
            FROM flights f
            LEFT JOIN airlines a
              ON f.airline_id = a.airline_id
            WHERE a.airline_id IS NULL
        """,

        "invalid origin FK": """
            SELECT COUNT(*)
            FROM flights f
            LEFT JOIN airports a
              ON f.origin_airport_id = a.airport_id
            WHERE a.airport_id IS NULL
        """,

        "invalid destination FK": """
            SELECT COUNT(*)
            FROM flights f
            LEFT JOIN airports a
              ON f.destination_airport_id = a.airport_id
            WHERE a.airport_id IS NULL
        """,

        "invalid aircraft FK": """
            SELECT COUNT(*)
            FROM flights f
            LEFT JOIN aircraft a
              ON f.aircraft_id = a.aircraft_id
            WHERE f.aircraft_id IS NOT NULL
              AND a.aircraft_id IS NULL
        """,

        "NaN/null source IDs": """
            SELECT COUNT(*)
            FROM flights
            WHERE source_row_id IS NULL
        """,

        "negative departure delay": """
            SELECT COUNT(*)
            FROM flight_delay
            WHERE departure_delay_minutes < 0
        """,

        "negative arrival delay": """
            SELECT COUNT(*)
            FROM flight_delay
            WHERE arrival_delay_minutes < 0
        """,

        "delay target mismatch": """
            SELECT COUNT(*)
            FROM flight_delay
            WHERE delayed_15 <>
                  (arrival_delay_minutes > 15)
        """,
    }

    with engine.connect() as conn:

        for name, query in checks.items():

            value = conn.execute(
                text(query)
            ).scalar()

            print(
                f"{name:32s}: "
                f"{value:,}"
            )

    with engine.connect() as conn:

        result = conn.execute(
            text("""
                SELECT
                    MIN(flight_date),
                    MAX(flight_date)
                FROM flights
            """)
        ).fetchone()

    print()
    print(
        "Flight date range:",
        result[0],
        "->",
        result[1]
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 78)
    print("FLITZZ")
    print("AIRLINE DISRUPTION MANAGEMENT")
    print("CSV -> POSTGRESQL")
    print("=" * 78)

    try:

        check_files()

        test_database()

        check_tables()

        clear_source_tables()

        load_airlines()

        load_airports()

        load_aircraft()

        load_flights()

        seed_policies()

        validate()

        print()
        print("=" * 78)
        print("SUCCESS")
        print("=" * 78)
        print(
            "CSV source data has been loaded successfully."
        )

    except KeyboardInterrupt:

        print(
            "\nProcess interrupted by user."
        )

        sys.exit(1)

    except Exception as exc:

        print()
        print("=" * 78)
        print("LOAD FAILED")
        print("=" * 78)
        print(
            type(exc).__name__,
            ":",
            str(exc)
        )

        raise


if __name__ == "__main__":
    main()
