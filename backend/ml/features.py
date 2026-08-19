"""
FLITZZ - ML FEATURE BUILDER

PostgreSQL
    |
    +-- Primary flight data
    +-- Historical airline / route behavior
    +-- Historical airport behavior
    +-- Flight traffic congestion proxy
    +-- Current departure status
    |
    v
 Master feature dataset
    |
    +-- XGBoost: exact existing 24-feature contract
    |
    +-- LightGBM: 24 + 10 additional regression features
Targets
-------
Classification:
    delayed_15 = arrival_delay_minutes >= 15

Regression:
    arrival_delay_minutes
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd

from dotenv import load_dotenv
from sqlalchemy import create_engine, text



# ============================================================================
# PATH / ENVIRONMENT
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

load_dotenv(BACKEND_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL not found.\n"
        f"Expected .env at: {BACKEND_DIR / '.env'}"
    )

ENGINE = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


# ============================================================================
# MODEL FEATURES
# ============================================================================

MODEL_FEATURES = [

    # ============================================================
    # XGBOOST CLASSIFICATION CONTRACT — EXISTING 24 FEATURES
    # ============================================================

    "airline",
    "origin_airport",
    "destination_airport",
    "departure_hour",
    "departure_period",
    "day_of_week",
    "month",
    "season",
    "distance_miles",

    "route_average_delay_minutes",
    "route_delay_rate",
    "route_previous_flights",
    "route_previous_delays",

    "airline_average_delay_minutes",
    "airline_delay_rate",
    "airline_previous_flights",
    "airline_previous_delays",

    "route_flights_1h",
    "route_flights_3h",
    "origin_flights_1h",
    "destination_flights_1h",
    "route_congestion_ratio",
    "origin_congestion_ratio",
    "destination_congestion_ratio",

    # ============================================================
    # LIGHTGBM ADDITIONAL FEATURES — 10
    # ============================================================

    "scheduled_time",
    "scheduled_speed",
    "departure_minute_of_day",
    "day",

    "airline_hist_delay",
    "origin_airport_hist_delay",
    "destination_airport_hist_delay",
    "route_hist_delay",

    "departure_delay",
    "taxi_out",
]

# Two explicit model contracts.
# XGBoost uses the exact 24 columns expected by the existing classifier.
XGB_FEATURES = [
    "airline",
    "origin_airport",
    "destination_airport",
    "departure_hour",
    "departure_period",
    "day_of_week",
    "month",
    "season",
    "distance_miles",
    "route_average_delay_minutes",
    "route_delay_rate",
    "route_previous_flights",
    "route_previous_delays",
    "airline_average_delay_minutes",
    "airline_delay_rate",
    "airline_previous_flights",
    "airline_previous_delays",
    "route_flights_1h",
    "route_flights_3h",
    "origin_flights_1h",
    "destination_flights_1h",
    "route_congestion_ratio",
    "origin_congestion_ratio",
    "destination_congestion_ratio",
]

# LightGBM gets the 24 original features plus the 10 genuinely new
# features from the friend's model.
LGBM_FEATURES = list(XGB_FEATURES) + [
    "scheduled_time",
    "scheduled_speed",
    "departure_minute_of_day",
    "day",
    "airline_hist_delay",
    "origin_airport_hist_delay",
    "destination_airport_hist_delay",
    "route_hist_delay",
    "departure_delay",
    "taxi_out",
]

EXPECTED_FEATURE_COUNT = 34

if len(XGB_FEATURES) != 24:
    raise RuntimeError(
        f"XGB_FEATURES must contain exactly 24 features, got {len(XGB_FEATURES)}."
    )

if len(LGBM_FEATURES) != 34:
    raise RuntimeError(
        f"LGBM_FEATURES must contain exactly 34 features, got {len(LGBM_FEATURES)}."
    )

if len(set(LGBM_FEATURES)) != len(LGBM_FEATURES):
    raise RuntimeError("LGBM_FEATURES contains duplicate columns.")

# ============================================================================
# TARGETS
# ============================================================================

TARGET_CLASSIFICATION = "delayed_15"

TARGET_REGRESSION = "arrival_delay_minutes"


# ============================================================================
# CATEGORICAL FEATURES
# ============================================================================

CATEGORICAL_FEATURES = [
    "airline",
    "origin_airport",
    "destination_airport",
    "season",
    "departure_period",
]

XGB_CATEGORICAL_FEATURES = [
    "airline",
    "origin_airport",
    "destination_airport",
    "departure_period",
    "season",
]

LGBM_CATEGORICAL_FEATURES = XGB_CATEGORICAL_FEATURES.copy()

# ============================================================================
# DATABASE CONNECTION TEST
# ============================================================================

def test_database_connection() -> None:
    """Test PostgreSQL connection."""

    print("[INFO] Testing PostgreSQL...")

    with ENGINE.connect() as conn:
        result = conn.execute(
            text("SELECT 1")
        )
        result.scalar()

    print(
        "[OK] PostgreSQL connection successful."
    )


# ============================================================================
# LOAD FLIGHTS
# ============================================================================


def load_flights(
    limit: int | None = None,
    offset: int = 0,
    after_flight_datetime=None,
    after_flight_id: int | None = None,
) -> pd.DataFrame:
    """
    Load flights from PostgreSQL in chronological order.

    Two pagination modes are supported:

    1. Development/testing:
           limit=10_000
           offset=0

    2. Large sequential training:
           limit=50_000
           after_flight_datetime=<last timestamp>
           after_flight_id=<last flight id>

    Keyset pagination is preferred for very large datasets because
    OFFSET becomes increasingly expensive in PostgreSQL.

    The airport join only retrieves coordinates for airports belonging
    to the flights in this chunk. It does NOT load the airport table
    into Python.
    """

    print("[INFO] Loading flights from PostgreSQL...")

    limit_sql = ""
    if limit is not None:
        limit_sql = f"LIMIT {int(limit)}"

    params = {}

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    pagination_sql = ""

    if after_flight_datetime is not None:

        pagination_sql = """
            AND (
                f.flight_datetime > :after_flight_datetime
                OR (
                    f.flight_datetime = :after_flight_datetime
                    AND f.flight_id > :after_flight_id
                )
            )
        """

        params["after_flight_datetime"] = after_flight_datetime
        params["after_flight_id"] = int(
            after_flight_id or 0
        )

    elif offset > 0:

        pagination_sql = f"""
            OFFSET {int(offset)}
        """

    query = f"""
        SELECT

            f.flight_id,
            f.airline_id,
            f.aircraft_id,
            f.flight_number,

            f.flight_date,

            f.year,
            f.month,
            f.day,
            f.day_of_week,

            f.origin_airport_id,
            f.destination_airport_id,

            ao.iata_code AS origin_airport,
            ad.iata_code AS destination_airport,

            ao.latitude AS origin_latitude,
            ao.longitude AS origin_longitude,

            ad.latitude AS destination_latitude,
            ad.longitude AS destination_longitude,

            al.iata_code AS airline,

            ac.tail_number AS aircraft,

            f.scheduled_departure,
            f.scheduled_arrival,

            f.scheduled_time_minutes,
            f.distance_miles,

            f.departure_hour,
            f.departure_minute,

            f.is_weekend,
            f.season,
            f.departure_period,

            f.route,
            f.flight_datetime,

            f.cancelled,
            f.diverted

        FROM flights f

        INNER JOIN airlines al
            ON f.airline_id = al.airline_id

        LEFT JOIN aircraft ac
            ON f.aircraft_id = ac.aircraft_id

        INNER JOIN airports ao
            ON f.origin_airport_id = ao.airport_id

        INNER JOIN airports ad
            ON f.destination_airport_id = ad.airport_id

        WHERE f.cancelled = FALSE
          AND f.diverted = FALSE
          AND f.flight_datetime IS NOT NULL

        {pagination_sql}

        ORDER BY
            f.flight_datetime ASC,
            f.flight_id ASC

        {limit_sql}
    """

    df = pd.read_sql(
        text(query),
        ENGINE,
        params=params,
    )

    if df.empty:
        return df

    print(
        f"[OK] Flights loaded: {len(df):,}"
    )

    # ------------------------------------------------------------------
    # Datetime normalization
    # ------------------------------------------------------------------

    df["flight_date"] = pd.to_datetime(
        df["flight_date"],
        errors="coerce",
    ).dt.date

    df["flight_datetime"] = pd.to_datetime(
        df["flight_datetime"],
        errors="coerce",
        utc=True,
    )

    df["scheduled_departure"] = pd.to_datetime(
        df["scheduled_departure"].astype(str),
        errors="coerce",
    ).dt.time

    df["scheduled_arrival"] = pd.to_datetime(
        df["scheduled_arrival"].astype(str),
        errors="coerce",
    ).dt.time

    return df



# ============================================================================
# LOAD DELAY TARGETS
# ============================================================================


def load_delay_targets(
    flight_ids: pd.Series,
) -> pd.DataFrame:

    """
    Load targets only for the flight IDs in the current chunk.

    This is important for large sequential training because we never
    load the complete flight_delay table into memory.
    """

    print(
        "[INFO] Loading historical delay targets..."
    )

    ids = [
        int(x)
        for x in flight_ids.dropna().unique()
    ]

    if not ids:

        return pd.DataFrame(
            columns=[
                "flight_id",
                TARGET_REGRESSION,
                TARGET_CLASSIFICATION,
            ]
        )

    query = """
        SELECT
            flight_id,
            arrival_delay_minutes,
            departure_delay_minutes

        FROM flight_delay

        WHERE flight_id = ANY(:flight_ids)
    """

    with ENGINE.connect() as conn:

        result = conn.execute(
            text(query),
            {
                "flight_ids": ids
            },
        )

        rows = result.fetchall()
        columns = result.keys()

    delay = pd.DataFrame(
        rows,
        columns=columns,
    )

    if delay.empty:

        print(
            "[WARNING] No flight_delay records found "
            "for this chunk."
        )

        return pd.DataFrame(
            columns=[
                "flight_id",
                TARGET_REGRESSION,
                TARGET_CLASSIFICATION,
            ]
        )

    delay["arrival_delay_minutes"] = (
        pd.to_numeric(
            delay["arrival_delay_minutes"],
            errors="coerce",
        )
        .fillna(0)
        .clip(lower=0)
    )

    delay["departure_delay_minutes"] = (
        pd.to_numeric(
            delay["departure_delay_minutes"],
            errors="coerce",
        )
        .fillna(0)
    )

    delay[TARGET_CLASSIFICATION] = (
        delay["arrival_delay_minutes"] >= 15
    ).astype(int)

    print(
        f"[OK] Delay targets loaded: "
        f"{len(delay):,}"
    )

    return delay[
        [
            "flight_id",
            TARGET_REGRESSION,
            TARGET_CLASSIFICATION,
        ]
    ]



# ============================================================================
# HISTORICAL AIRLINE FEATURES
# ============================================================================

def load_airline_history(
    flights: pd.DataFrame,
) -> pd.DataFrame:

    print(
        "[INFO] Loading airline history..."
    )

    airline_ids = (
        flights["airline_id"]
        .dropna()
        .unique()
        .tolist()
    )

    if not airline_ids:
        return pd.DataFrame(
            index=flights.index
        )

    min_date = flights["flight_date"].min()
    max_date = flights["flight_date"].max()

    query = """
        SELECT

            airline_id,
            observation_date,

            previous_flights,
            previous_delays,
            delay_rate,
            average_delay_minutes

        FROM airline_history

        WHERE airline_id = ANY(:airline_ids)

          AND observation_date
              BETWEEN :min_date AND :max_date
    """

    with ENGINE.connect() as conn:

        result = conn.execute(
            text(query),
            {
                "airline_ids": [
                    int(x)
                    for x in airline_ids
                ],
                "min_date": min_date,
                "max_date": max_date,
            },
        )

        rows = result.fetchall()
        columns = result.keys()

    history = pd.DataFrame(
        rows,
        columns=columns,
    )

    if history.empty:

        print(
            "[WARNING] No airline history found."
        )

        return pd.DataFrame(
            index=flights.index
        )

    history["observation_date"] = (
        pd.to_datetime(
            history["observation_date"],
            errors="coerce",
        )
        .dt.date
    )

    base = flights[
        [
            "airline_id",
            "flight_date",
        ]
    ].copy()

    base["_feature_index"] = base.index

    merged = base.merge(
        history,
        left_on=[
            "airline_id",
            "flight_date",
        ],
        right_on=[
            "airline_id",
            "observation_date",
        ],
        how="left",
    )

    merged = merged.set_index(
        "_feature_index"
    )

    result = merged[
        [
            "previous_flights",
            "previous_delays",
            "delay_rate",
            "average_delay_minutes",
        ]
    ].rename(
        columns={
            "previous_flights":
                "airline_previous_flights",

            "previous_delays":
                "airline_previous_delays",

            "delay_rate":
                "airline_delay_rate",

            "average_delay_minutes":
                "airline_average_delay_minutes",
        }
    )

    result.index = flights.index

    return result


# ============================================================================
# HISTORICAL ROUTE FEATURES
# ============================================================================

def load_route_history(
    flights: pd.DataFrame,
) -> pd.DataFrame:

    print(
        "[INFO] Loading route history..."
    )

    origin_ids = [
        int(x)
        for x in flights["origin_airport_id"]
        .dropna()
        .unique()
    ]

    destination_ids = [
        int(x)
        for x in flights["destination_airport_id"]
        .dropna()
        .unique()
    ]

    if not origin_ids or not destination_ids:
        return pd.DataFrame(index=flights.index)

    query = """
        SELECT

            origin_airport_id,
            destination_airport_id,
            observation_date,

            previous_flights,
            previous_delays,
            delay_rate,
            average_delay_minutes

        FROM route_history

        WHERE observation_date
              BETWEEN :min_date AND :max_date

          AND origin_airport_id = ANY(:origin_ids)
          AND destination_airport_id = ANY(:destination_ids)
    """

    with ENGINE.connect() as conn:

        result = conn.execute(
            text(query),
            {
                "min_date":
                    flights["flight_date"].min(),

                "max_date":
                    flights["flight_date"].max(),

                "origin_ids": origin_ids,
                "destination_ids": destination_ids,
            },
        )

        rows = result.fetchall()
        columns = result.keys()

    history = pd.DataFrame(
        rows,
        columns=columns,
    )

    if history.empty:

        print(
            "[WARNING] No route history found."
        )

        return pd.DataFrame(
            index=flights.index
        )

    history["observation_date"] = (
        pd.to_datetime(
            history["observation_date"],
            errors="coerce",
        )
        .dt.date
    )

    base = flights[
        [
            "origin_airport_id",
            "destination_airport_id",
            "flight_date",
        ]
    ].copy()

    base["_feature_index"] = base.index

    merged = base.merge(
        history,
        left_on=[
            "origin_airport_id",
            "destination_airport_id",
            "flight_date",
        ],
        right_on=[
            "origin_airport_id",
            "destination_airport_id",
            "observation_date",
        ],
        how="left",
    )

    merged = merged.set_index(
        "_feature_index"
    )

    result = merged[
        [
            "previous_flights",
            "previous_delays",
            "delay_rate",
            "average_delay_minutes",
        ]
    ].rename(
        columns={
            "previous_flights":
                "route_previous_flights",

            "previous_delays":
                "route_previous_delays",

            "delay_rate":
                "route_delay_rate",

            "average_delay_minutes":
                "route_average_delay_minutes",
        }
    )

    result.index = flights.index

    return result



# ============================================================================
# AIRPORT HISTORICAL DELAY
# ============================================================================

def load_airport_history(
    flights: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build airport historical-delay features without using the current day's
    outcome.

    We use the previous calendar day's airport delay statistics. This avoids
    using same-day future flights as historical information, which would leak
    information from the future into the current row.
    """

    print("[INFO] Loading airport historical delay...")

    if flights.empty:
        return pd.DataFrame(index=flights.index)

    origin_ids = [
        int(x)
        for x in flights["origin_airport_id"].dropna().unique()
    ]
    destination_ids = [
        int(x)
        for x in flights["destination_airport_id"].dropna().unique()
    ]

    if not origin_ids and not destination_ids:
        return pd.DataFrame(index=flights.index)

    min_date = pd.to_datetime(flights["flight_date"]).min()
    max_date = pd.to_datetime(flights["flight_date"]).max()

    # Pull one extra day because each flight uses the previous day's history.
    history_start = (min_date - pd.Timedelta(days=1)).date()
    history_end = (max_date - pd.Timedelta(days=1)).date()

    query = """
        SELECT
            f.flight_date,
            f.origin_airport_id,
            f.destination_airport_id,
            fd.arrival_delay_minutes
        FROM flights f
        INNER JOIN flight_delay fd
            ON f.flight_id = fd.flight_id
        WHERE f.cancelled = FALSE
          AND f.diverted = FALSE
          AND f.flight_date BETWEEN :history_start AND :history_end
          AND (
              f.origin_airport_id = ANY(:origin_ids)
              OR f.destination_airport_id = ANY(:destination_ids)
          )
    """

    try:
        with ENGINE.connect() as conn:
            result = conn.execute(
                text(query),
                {
                    "history_start": history_start,
                    "history_end": history_end,
                    "origin_ids": origin_ids or [-1],
                    "destination_ids": destination_ids or [-1],
                },
            )
            rows = result.fetchall()
            columns = result.keys()
    except Exception as exc:
        print(f"[WARNING] Could not load airport history: {exc}")
        return pd.DataFrame(index=flights.index)

    history = pd.DataFrame(rows, columns=columns)

    if history.empty:
        result = pd.DataFrame(index=flights.index)
        result["origin_airport_hist_delay"] = np.nan
        result["destination_airport_hist_delay"] = np.nan
        return result

    history["flight_date"] = pd.to_datetime(
        history["flight_date"], errors="coerce"
    ).dt.date

    history["arrival_delay_minutes"] = pd.to_numeric(
        history["arrival_delay_minutes"], errors="coerce"
    ).fillna(0).clip(lower=0)

    origin_daily = (
        history.groupby(
            ["origin_airport_id", "flight_date"],
            dropna=False,
        )["arrival_delay_minutes"]
        .mean()
        .rename("origin_airport_hist_delay")
        .reset_index()
    )

    destination_daily = (
        history.groupby(
            ["destination_airport_id", "flight_date"],
            dropna=False,
        )["arrival_delay_minutes"]
        .mean()
        .rename("destination_airport_hist_delay")
        .reset_index()
    )

    base = flights[
        [
            "origin_airport_id",
            "destination_airport_id",
            "flight_date",
        ]
    ].copy()

    base["_feature_index"] = base.index
    base["_history_date"] = (
        pd.to_datetime(base["flight_date"]) -
        pd.Timedelta(days=1)
    ).dt.date

    origin_merge = base.merge(
        origin_daily,
        left_on=["origin_airport_id", "_history_date"],
        right_on=["origin_airport_id", "flight_date"],
        how="left",
    )

    destination_merge = base.merge(
        destination_daily,
        left_on=["destination_airport_id", "_history_date"],
        right_on=["destination_airport_id", "flight_date"],
        how="left",
    )

    result = pd.DataFrame(index=flights.index)

    origin_values = origin_merge.set_index(
        "_feature_index"
    )["origin_airport_hist_delay"]

    destination_values = destination_merge.set_index(
        "_feature_index"
    )["destination_airport_hist_delay"]

    result["origin_airport_hist_delay"] = (
        origin_values.reindex(flights.index).to_numpy()
    )
    result["destination_airport_hist_delay"] = (
        destination_values.reindex(flights.index).to_numpy()
    )

    return result


# ============================================================================
# CONGESTION
# ============================================================================


def add_congestion_features(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add previous-hour traffic features.

    IMPORTANT FOR CHUNK TRAINING
    ----------------------------
    The previous implementation calculated traffic only from the rows
    already present in the DataFrame. That creates incorrect values at
    chunk boundaries.

    This implementation queries PostgreSQL for the relevant historical
    flights covering the previous-hour window required by this chunk.

    Therefore:

        flight at 11:05
            -> traffic from 10:00-10:59

    is available even when 10:00-10:59 belongs to the previous chunk.
    """

    print(
        "[INFO] Building traffic congestion features..."
    )

    df = df.copy()

    if df.empty:
        return df

    df["_timestamp"] = pd.to_datetime(
        df["flight_datetime"],
        errors="coerce",
        utc=True,
    )

    df["_hour"] = (
        df["_timestamp"]
        .dt.floor("h")
    )

    min_hour = (
        df["_hour"].min()
    )

    max_hour = (
        df["_hour"].max()
    )

    if pd.isna(min_hour) or pd.isna(max_hour):

        for column in [
            "origin_flights_1h",
            "destination_flights_1h",
            "route_flights_1h",
        ]:
            df[column] = 0

    else:

        previous_start = (
            min_hour - pd.Timedelta(hours=1)
        )

        previous_end = max_hour

        # --------------------------------------------------------------
        # Get only the traffic interval needed by this chunk.
        #
        # We deliberately do NOT load the whole flights table.
        # --------------------------------------------------------------

        query = """
            SELECT
                flight_datetime,
                origin_airport_id,
                destination_airport_id

            FROM flights

            WHERE cancelled = FALSE
              AND diverted = FALSE
              AND flight_datetime IS NOT NULL

              AND flight_datetime >= :start_time
              AND flight_datetime < :end_time
        """

        with ENGINE.connect() as conn:

            result = conn.execute(
                text(query),
                {
                    "start_time": previous_start.to_pydatetime(),
                    "end_time": previous_end.to_pydatetime(),
                },
            )

            rows = result.fetchall()
            columns = result.keys()

        traffic = pd.DataFrame(
            rows,
            columns=columns,
        )

        if traffic.empty:

            hourly_origin = pd.DataFrame(
                columns=[
                    "origin_airport_id",
                    "_hour",
                    "origin_flights_1h",
                ]
            )

            hourly_destination = pd.DataFrame(
                columns=[
                    "destination_airport_id",
                    "_hour",
                    "destination_flights_1h",
                ]
            )

            hourly_route = pd.DataFrame(
                columns=[
                    "origin_airport_id",
                    "destination_airport_id",
                    "_hour",
                    "route_flights_1h",
                ]
            )

        else:

            traffic["flight_datetime"] = pd.to_datetime(
                traffic["flight_datetime"],
                errors="coerce",
                utc=True,
            )

            traffic["_hour"] = (
                traffic["flight_datetime"]
                .dt.floor("h")
            )

            # ----------------------------------------------------------
            # Origin traffic
            # ----------------------------------------------------------

            hourly_origin = (
                traffic.groupby(
                    [
                        "origin_airport_id",
                        "_hour",
                    ]
                )
                .size()
                .rename(
                    "origin_flights_1h"
                )
                .reset_index()
            )

            # ----------------------------------------------------------
            # Destination traffic
            # ----------------------------------------------------------

            hourly_destination = (
                traffic.groupby(
                    [
                        "destination_airport_id",
                        "_hour",
                    ]
                )
                .size()
                .rename(
                    "destination_flights_1h"
                )
                .reset_index()
            )

            # ----------------------------------------------------------
            # Route traffic
            # ----------------------------------------------------------

            hourly_route = (
                traffic.groupby(
                    [
                        "origin_airport_id",
                        "destination_airport_id",
                        "_hour",
                    ]
                )
                .size()
                .rename(
                    "route_flights_1h"
                )
                .reset_index()
            )

        # --------------------------------------------------------------
        # Current flight looks at the PREVIOUS hour.
        # --------------------------------------------------------------

        df["_previous_hour"] = (
            df["_hour"]
            - pd.Timedelta(hours=1)
        )

        # --------------------------------------------------------------
        # Origin
        # --------------------------------------------------------------

        origin_lookup = hourly_origin.rename(
            columns={
                "_hour": "_previous_hour"
            }
        )

        df = df.merge(
            origin_lookup,
            on=[
                "origin_airport_id",
                "_previous_hour",
            ],
            how="left",
        )

        # --------------------------------------------------------------
        # Destination
        # --------------------------------------------------------------

        destination_lookup = (
            hourly_destination.rename(
                columns={
                    "_hour": "_previous_hour"
                }
            )
        )

        df = df.merge(
            destination_lookup,
            on=[
                "destination_airport_id",
                "_previous_hour",
            ],
            how="left",
        )

        # --------------------------------------------------------------
        # Route
        # --------------------------------------------------------------

        route_lookup = hourly_route.rename(
            columns={
                "_hour": "_previous_hour"
            }
        )

        df = df.merge(
            route_lookup,
            on=[
                "origin_airport_id",
                "destination_airport_id",
                "_previous_hour",
            ],
            how="left",
        )

    # ------------------------------------------------------------------
    # Missing traffic
    # ------------------------------------------------------------------

    congestion_count_columns = [
        "origin_flights_1h",
        "destination_flights_1h",
        "route_flights_1h",
    ]

    for column in congestion_count_columns:

        if column not in df.columns:
            df[column] = 0

        df[column] = (
            pd.to_numeric(
                df[column],
                errors="coerce",
            )
            .fillna(0)
        )

    # ------------------------------------------------------------------
    # Congestion ratios
    # ------------------------------------------------------------------

    df["origin_congestion_ratio"] = (
        df["origin_flights_1h"] / 20.0
    ).clip(0, 2)

    df["destination_congestion_ratio"] = (
        df["destination_flights_1h"] / 20.0
    ).clip(0, 2)

    df["route_congestion_ratio"] = (
        df["route_flights_1h"] / 10.0
    ).clip(0, 2)

    # ------------------------------------------------------------------
    # Congestion levels
    # ------------------------------------------------------------------

    def congestion_level(
        value: float,
    ) -> str:

        if value < 0.50:
            return "LOW"

        if value < 1.00:
            return "MEDIUM"

        return "HIGH"

    df["origin_congestion_level"] = (
        df["origin_congestion_ratio"]
        .apply(congestion_level)
    )

    df["destination_congestion_level"] = (
        df["destination_congestion_ratio"]
        .apply(congestion_level)
    )

    df["route_congestion_level"] = (
        df["route_congestion_ratio"]
        .apply(congestion_level)
    )

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    df = df.drop(
        columns=[
            "_timestamp",
            "_hour",
            "_previous_hour",
        ],
        errors="ignore",
    )

    print(
        "[OK] Chunk-safe congestion features created."
    )

    return df



# ============================================================================
# PREPARE CATEGORICAL FEATURES
# ============================================================================

def clean_categorical_features(
    df: pd.DataFrame,
) -> pd.DataFrame:

    df = df.copy()

    for column in CATEGORICAL_FEATURES:

        if column not in df.columns:
            df[column] = "UNKNOWN"

        df[column] = (
            df[column]
            .fillna("UNKNOWN")
            .astype(str)
        )

    return df


# ============================================================================
# PREPARE NUMERIC FEATURES
# ============================================================================

def clean_numeric_features(
    df: pd.DataFrame,
) -> pd.DataFrame:

    df = df.copy()

    numeric_features = [
        column
        for column in MODEL_FEATURES
        if column not in CATEGORICAL_FEATURES
    ]

    for column in numeric_features:

        if column not in df.columns:
            df[column] = np.nan

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

        df[column] = (
            df[column]
            .replace(
                [
                    np.inf,
                    -np.inf,
                ],
                np.nan,
            )
        )

    # ------------------------------------------------------------------------
    # Fill missing values.
    #
    # ------------------------------------------------------------------------

    for column in numeric_features:

        median = df[column].median()

        if pd.isna(median):
            median = 0.0

        df[column] = (
            df[column]
            .fillna(median)
        )

    return df


# ============================================================================
# FINAL FEATURE BUILD
# ============================================================================


def build_features(
    limit: int | None = None,
    offset: int = 0,
    after_flight_datetime=None,
    after_flight_id: int | None = None,
) -> pd.DataFrame:

    """
    Build one ML feature chunk.

    For large datasets use:

        limit=50_000
        after_flight_datetime=<last row timestamp>
        after_flight_id=<last row id>

    This keeps memory bounded and supports sequential training.
    """

    print()
    print("=" * 70)
    print("FLITZZ FEATURE BUILDER")
    print("=" * 70)

    # ------------------------------------------------------------------------
    # 1. Primary flight data
    # ------------------------------------------------------------------------

    flights = load_flights(
        limit=limit,
        offset=offset,
        after_flight_datetime=after_flight_datetime,
        after_flight_id=after_flight_id,
    )

    if flights.empty:
        return pd.DataFrame(
            columns=[
                "flight_id",
                "flight_datetime",
                *MODEL_FEATURES,
                TARGET_CLASSIFICATION,
                TARGET_REGRESSION,
            ]
        )

    # ------------------------------------------------------------------------
    # 2. Historical delay target
    # ------------------------------------------------------------------------

    targets = load_delay_targets(
        flights["flight_id"]
    )

    df = flights.merge(
        targets,
        on="flight_id",
        how="inner",
    )

    if df.empty:

        print(
            "[WARNING] No flights remained after "
            "joining flight_delay."
        )

        return pd.DataFrame(
            columns=[
                "flight_id",
                "flight_datetime",
                *MODEL_FEATURES,
                TARGET_CLASSIFICATION,
                TARGET_REGRESSION,
            ]
        )

    print(
        f"[OK] Flights after target join: "
        f"{len(df):,}"
    )

    # ------------------------------------------------------------------------
    # 3. Airline historical behavior
    # ------------------------------------------------------------------------

    airline_history = load_airline_history(
        df
    )

    if not airline_history.empty:

        df = df.join(
            airline_history,
            how="left",
        )

    # ------------------------------------------------------------------------
    # 4. Route historical behavior
    # ------------------------------------------------------------------------

    route_history = load_route_history(
        df
    )

    if not route_history.empty:

        df = df.join(
            route_history,
            how="left",
        )

    # ------------------------------------------------------------------------
    # 5. Friend-model historical airport features
    # ------------------------------------------------------------------------

    airport_history = load_airport_history(df)

    if not airport_history.empty:
        df = df.join(airport_history, how="left")
    else:
        df["origin_airport_hist_delay"] = np.nan
        df["destination_airport_hist_delay"] = np.nan

    # The friend's "airline_hist_delay" and "route_hist_delay" correspond
    # directly to the existing DB-backed average-delay history.
    df["airline_hist_delay"] = pd.to_numeric(
        df.get("airline_average_delay_minutes", np.nan),
        errors="coerce",
    )

    df["route_hist_delay"] = pd.to_numeric(
        df.get("route_average_delay_minutes", np.nan),
        errors="coerce",
    )

    # ------------------------------------------------------------------------
    # 6. Friend-model engineered schedule features
    # ------------------------------------------------------------------------

    df["scheduled_time"] = pd.to_numeric(
        df.get("scheduled_time_minutes", np.nan),
        errors="coerce",
    )

    departure_hour = pd.to_numeric(
        df.get("departure_hour", np.nan),
        errors="coerce",
    ).fillna(0)

    departure_minute = pd.to_numeric(
        df.get("departure_minute", np.nan),
        errors="coerce",
    ).fillna(0)

    df["departure_minute_of_day"] = (
        departure_hour * 60 + departure_minute
    )

    scheduled_hours = df["scheduled_time"] / 60.0
    distance = pd.to_numeric(
        df.get("distance_miles", np.nan),
        errors="coerce",
    )

    df["scheduled_speed"] = np.where(
        scheduled_hours > 0,
        distance / scheduled_hours,
        0.0,
    )

    # ------------------------------------------------------------------------
    # 7. Traffic congestion
    # ------------------------------------------------------------------------

    df = add_congestion_features(df)

    # ------------------------------------------------------------------------
    # 7. Categorical cleanup
    # ------------------------------------------------------------------------

    df = clean_categorical_features(
        df
    )

    # ------------------------------------------------------------------------
    # 8. Numeric cleanup
    # ------------------------------------------------------------------------

    df = clean_numeric_features(
        df
    )

    # ------------------------------------------------------------------------
    # 9. Final columns
    # ------------------------------------------------------------------------

    final_columns = [
        "flight_id",
        "flight_datetime",
    ]

    final_columns += MODEL_FEATURES

    final_columns += [
        TARGET_CLASSIFICATION,
        TARGET_REGRESSION,
    ]

    missing_final_columns = [
        column
        for column in final_columns
        if column not in df.columns
    ]

    if missing_final_columns:

        raise RuntimeError(
            "Final ML dataset is missing columns:\n"
            + "\n".join(
                f"  - {column}"
                for column in missing_final_columns
            )
        )

    df = df[
        final_columns
    ]

    # ------------------------------------------------------------------------
    # Sort chronologically
    # ------------------------------------------------------------------------

    df = df.sort_values(
        [
            "flight_datetime",
            "flight_id",
        ]
    )

    df = df.reset_index(
        drop=True
    )

    print()
    print(
        f"[OK] Final feature rows: "
        f"{len(df):,}"
    )

    print(
        f"[OK] Final ML features: "
        f"{len(MODEL_FEATURES)}"
    )

    return df





# ============================================================================
# SEQUENTIAL FEATURE CHUNK ITERATOR
# ============================================================================

def iter_feature_chunks(
    chunk_size: int = 50_000,
):
    """
    Yield feature DataFrames sequentially.

    This uses keyset pagination, not OFFSET.

    Example:

        for chunk in iter_feature_chunks(
            chunk_size=50_000,
        ):
            train_on_chunk(chunk)

    The function keeps only one feature chunk in memory at a time.

    Yields
    ------
    pd.DataFrame
        One chronologically ordered ML feature chunk.
    """

    if chunk_size <= 0:
        raise ValueError(
            "chunk_size must be greater than zero."
        )

    last_datetime = None
    last_flight_id = None

    chunk_number = 0

    while True:

        chunk_number += 1

        print()
        print("=" * 70)
        print(
            f"FEATURE CHUNK {chunk_number}"
        )
        print("=" * 70)

        chunk = build_features(
            limit=chunk_size,
            after_flight_datetime=last_datetime,
            after_flight_id=last_flight_id,
        )

        if chunk.empty:
            print(
                "[INFO] No more flights."
            )
            break

        yield chunk

        # --------------------------------------------------------------
        # Keyset cursor
        # --------------------------------------------------------------

        last_row = chunk.iloc[-1]

        last_datetime = (
            last_row["flight_datetime"]
        )

        last_flight_id = int(
            last_row["flight_id"]
        )

        print(
            f"[INFO] Chunk {chunk_number} complete."
        )

        print(
            f"[INFO] Cursor: "
            f"{last_datetime} / "
            f"{last_flight_id}"
        )

        del chunk

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":

    test_database_connection()