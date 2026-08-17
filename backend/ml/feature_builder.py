"""
FLITZZ - Feature Builder
========================

Builds the final ML feature dataset for flight-delay prediction.

DATA SOURCES
------------
1. PostgreSQL
   - flights
   - flight_delay
   - airline_history
   - route_history
   - airports

2. Open-Meteo Archive
   - historical weather only
   - exact historical flight date
   - flight departure/arrival hour
   - airport latitude/longitude from PostgreSQL

FEATURE GROUPS
--------------
1. Flight / schedule
2. Historical delay
3. Operational congestion proxy
4. Historical weather

TARGET
------
delayed_15

IMPORTANT
---------
No post-flight information is used as an input feature.
"""

from __future__ import annotations

import os
from typing import Optional

import numpy as np
import pandas as pd
import requests_cache
import openmeteo_requests

from retry_requests import retry
from sqlalchemy import create_engine, text


# ============================================================
# CONFIGURATION
# ============================================================

CONGESTION_WINDOW_MINUTES = 60


# ============================================================
# DATABASE / ENVIRONMENT
# ============================================================

# feature_builder.py is located at:
#   backend/ml/feature_builder.py
#
# The project .env is located at:
#   backend/.env

BACKEND_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

ENV_FILE = os.path.join(
    BACKEND_DIR,
    ".env"
)

print(
    f"[INFO] Loading environment from: {ENV_FILE}"
)

if not os.path.exists(ENV_FILE):
    raise FileNotFoundError(
        "Backend .env file was not found.\n"
        f"Expected: {ENV_FILE}"
    )

try:
    from dotenv import load_dotenv
except ImportError as exc:
    raise ImportError(
        "python-dotenv is required. "
        "Install it with: pip install python-dotenv"
    ) from exc

load_dotenv(
    ENV_FILE,
    override=True
)

DATABASE_URL = os.getenv(
    "DATABASE_URL"
)

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL was not loaded from backend/.env.\n"
        f"Expected: {ENV_FILE}\n"
        "Example: DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/flitz"
    )

print("[OK] DATABASE_URL loaded.")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


def test_database_connection() -> bool:
    """Test the PostgreSQL connection used by the feature builder."""

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT 1")
            )
            result.scalar()

        print("[OK] PostgreSQL connection successful.")
        return True

    except Exception as exc:
        print("[ERROR] PostgreSQL connection failed:")
        print(exc)
        return False


# ============================================================
# OPEN-METEO
# ============================================================

cache_session = requests_cache.CachedSession(
    ".cache",
    expire_after=-1
)

retry_session = retry(
    cache_session,
    retries=5,
    backoff_factor=0.2
)

openmeteo = openmeteo_requests.Client(
    session=retry_session
)


# ============================================================
# 1. LOAD FLIGHT DATA
# ============================================================

def load_flights() -> pd.DataFrame:

    query = text(
        """
        SELECT

            f.flight_id,
            f.airline_id,
            f.aircraft_id,
            f.flight_number,

            f.origin_airport_id,
            f.destination_airport_id,

            f.flight_date,

            f.scheduled_departure,
            f.scheduled_arrival,

            f.scheduled_time_minutes,
            f.distance_miles,

            f.departure_hour,
            f.day_of_week,
            f.month,

            -- TARGET
            fd.delayed_15,

            -- AIRLINE HISTORY
            ah.delay_rate
                AS airline_delay_rate,

            ah.average_delay_minutes
                AS airline_average_delay,

            -- ROUTE HISTORY
            rh.delay_rate
                AS route_delay_rate,

            rh.average_delay_minutes
                AS route_average_delay,

            -- ORIGIN COORDINATES
            origin.latitude
                AS origin_latitude,

            origin.longitude
                AS origin_longitude,

            -- DESTINATION COORDINATES
            destination.latitude
                AS destination_latitude,

            destination.longitude
                AS destination_longitude

        FROM flights f

        LEFT JOIN flight_delay fd
            ON fd.flight_id = f.flight_id

        --------------------------------------------------------
        -- AIRLINE HISTORY
        --------------------------------------------------------

        LEFT JOIN LATERAL (

            SELECT
                h.delay_rate,
                h.average_delay_minutes

            FROM airline_history h

            WHERE h.airline_id = f.airline_id

              AND h.observation_date <= f.flight_date

            ORDER BY h.observation_date DESC

            LIMIT 1

        ) ah ON TRUE

        --------------------------------------------------------
        -- ROUTE HISTORY
        --------------------------------------------------------

        LEFT JOIN LATERAL (

            SELECT
                h.delay_rate,
                h.average_delay_minutes

            FROM route_history h

            WHERE h.origin_airport_id =
                  f.origin_airport_id

              AND h.destination_airport_id =
                  f.destination_airport_id

              AND h.observation_date <= f.flight_date

            ORDER BY h.observation_date DESC

            LIMIT 1

        ) rh ON TRUE

        --------------------------------------------------------
        -- ORIGIN AIRPORT
        --------------------------------------------------------

        LEFT JOIN airports origin
            ON origin.airport_id =
               f.origin_airport_id

        --------------------------------------------------------
        -- DESTINATION AIRPORT
        --------------------------------------------------------

        LEFT JOIN airports destination
            ON destination.airport_id =
               f.destination_airport_id

        --------------------------------------------------------
        -- CANCELLED FLIGHTS ARE NOT USED
        --------------------------------------------------------

        WHERE COALESCE(
            f.cancelled,
            FALSE
        ) = FALSE

        ORDER BY
            f.flight_date,
            f.scheduled_departure,
            f.flight_id
        """
    )

    print("[INFO] Loading flights from PostgreSQL...")

    with engine.connect() as connection:

        df = pd.read_sql(
            query,
            connection
        )

    print(
        f"[OK] Loaded {len(df):,} flights"
    )

    return df


# ============================================================
# 2. CLEAN DATA
# ============================================================

def clean_data(
    df: pd.DataFrame
) -> pd.DataFrame:

    df = df.copy()

    df["flight_date"] = pd.to_datetime(
        df["flight_date"],
        errors="coerce"
    )

    numeric_columns = [
        "airline_id",
        "aircraft_id",
        "flight_number",

        "origin_airport_id",
        "destination_airport_id",

        "departure_hour",
        "day_of_week",
        "month",

        "scheduled_time_minutes",
        "distance_miles",

        "airline_delay_rate",
        "airline_average_delay",

        "route_delay_rate",
        "route_average_delay",

        "origin_latitude",
        "origin_longitude",

        "destination_latitude",
        "destination_longitude",

        "delayed_15"
    ]

    for column in numeric_columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    return df


# ============================================================
# 3. FLIGHT NUMBER HISTORY
# ============================================================

def add_flight_history(
    df: pd.DataFrame
) -> pd.DataFrame:

    df = df.copy()

    df = df.sort_values(
        [
            "airline_id",
            "flight_number",
            "flight_date",
            "scheduled_departure",
            "flight_id"
        ]
    )

    group = df.groupby(
        [
            "airline_id",
            "flight_number"
        ],
        sort=False
    )

    # --------------------------------------------------------
    # Previous flights
    # --------------------------------------------------------

    previous_count = (
        group.cumcount()
    )

    # --------------------------------------------------------
    # Previous delay rate
    # --------------------------------------------------------

    previous_delays = (
        group["delayed_15"]
        .transform(
            lambda x:
            x.shift(1)
            .expanding()
            .mean()
        )
    )

    df[
        "flight_number_delay_rate"
    ] = previous_delays.fillna(0)

    # --------------------------------------------------------
    # Previous average delay
    # --------------------------------------------------------

    # Use historical arrival/departure delay only.
    # This is calculated from rows BEFORE the current flight.

    if "arrival_delay_minutes" in df.columns:

        delay_values = pd.to_numeric(
            df["arrival_delay_minutes"],
            errors="coerce"
        ).clip(lower=0)

    else:

        delay_values = pd.Series(
            0.0,
            index=df.index
        )

    df[
        "_delay_value"
    ] = delay_values

    df[
        "flight_number_average_delay"
    ] = (
        df.groupby(
            [
                "airline_id",
                "flight_number"
            ]
        )["_delay_value"]
        .transform(
            lambda x:
            x.shift(1)
            .expanding()
            .mean()
        )
        .fillna(0)
    )

    df.drop(
        columns=["_delay_value"],
        inplace=True
    )

    return df


# ============================================================
# 4. CONGESTION PROXY
# ============================================================

def add_congestion_features(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Calculates congestion from our own flight data.

    No traffic API is used.

    For each flight:

        origin_flights_1h
        destination_flights_1h
        route_flights_1h

    are calculated from flights scheduled around the
    current flight time.

    Ratios compare current activity with the historical
    average for the same airport/route/time bucket.
    """

    print("[INFO] Calculating congestion...")

    df = df.copy()

    # --------------------------------------------------------
    # Absolute departure time
    # --------------------------------------------------------

    departure_minutes = (
        df["departure_hour"].fillna(0) * 60
        +
        df.get(
            "departure_minute",
            pd.Series(0, index=df.index)
        ).fillna(0)
    )

    df["_absolute_minutes"] = (
        df["flight_date"]
        .dt.normalize()
        .astype("int64")
        // 10**9
        // 60
    ) + departure_minutes

    # ========================================================
    # ORIGIN CONGESTION
    # ========================================================

    df[
        "origin_flights_1h"
    ] = calculate_rolling_count(
        df,
        group_columns=[
            "origin_airport_id"
        ],
        time_column="_absolute_minutes"
    )

    # ========================================================
    # DESTINATION CONGESTION
    # ========================================================

    # For the destination, use scheduled arrival time.

    arrival_minutes = (
        pd.to_datetime(
            df["scheduled_arrival"],
            errors="coerce"
        )
        .dt.hour
        .fillna(0) * 60
        +
        pd.to_datetime(
            df["scheduled_arrival"],
            errors="coerce"
        )
        .dt.minute
        .fillna(0)
    )

    df["_arrival_absolute"] = (
        df["flight_date"]
        .dt.normalize()
        .astype("int64")
        // 10**9
        // 60
    ) + arrival_minutes

    df[
        "destination_flights_1h"
    ] = calculate_rolling_count(
        df,
        group_columns=[
            "destination_airport_id"
        ],
        time_column="_arrival_absolute"
    )

    # ========================================================
    # ROUTE CONGESTION
    # ========================================================

    df[
        "route_flights_1h"
    ] = calculate_rolling_count(
        df,
        group_columns=[
            "origin_airport_id",
            "destination_airport_id"
        ],
        time_column="_absolute_minutes"
    )

    # ========================================================
    # HISTORICAL BASELINE
    # ========================================================

    origin_baseline = (
        df.groupby(
            [
                "origin_airport_id",
                "day_of_week",
                "departure_hour"
            ]
        )["origin_flights_1h"]
        .transform("mean")
    )

    destination_baseline = (
        df.groupby(
            [
                "destination_airport_id",
                "day_of_week",
                "departure_hour"
            ]
        )["destination_flights_1h"]
        .transform("mean")
    )

    route_baseline = (
        df.groupby(
            [
                "origin_airport_id",
                "destination_airport_id",
                "day_of_week",
                "departure_hour"
            ]
        )["route_flights_1h"]
        .transform("mean")
    )

    # ========================================================
    # RATIOS
    # ========================================================

    df[
        "origin_congestion_ratio"
    ] = safe_ratio(
        df["origin_flights_1h"],
        origin_baseline
    )

    df[
        "destination_congestion_ratio"
    ] = safe_ratio(
        df["destination_flights_1h"],
        destination_baseline
    )

    df[
        "route_congestion_ratio"
    ] = safe_ratio(
        df["route_flights_1h"],
        route_baseline
    )

    # ========================================================
    # LEVELS
    # ========================================================

    df[
        "origin_congestion_level"
    ] = congestion_level(
        df["origin_congestion_ratio"]
    )

    df[
        "destination_congestion_level"
    ] = congestion_level(
        df["destination_congestion_ratio"]
    )

    df[
        "route_congestion_level"
    ] = congestion_level(
        df["route_congestion_ratio"]
    )

    df.drop(
        columns=[
            "_absolute_minutes",
            "_arrival_absolute"
        ],
        inplace=True,
        errors="ignore"
    )

    return df


# ============================================================
# CONGESTION HELPERS
# ============================================================

def calculate_rolling_count(
    df: pd.DataFrame,
    group_columns: list[str],
    time_column: str
) -> pd.Series:
    """
    Counts flights in the previous 60 minutes.

    Current flight is excluded.
    """

    result = pd.Series(
        0,
        index=df.index,
        dtype="int64"
    )

    working = df[
        group_columns + [time_column]
    ].copy()

    working["_index"] = working.index

    working = working.dropna(
        subset=group_columns + [time_column]
    )

    working = working.sort_values(
        group_columns + [time_column]
    )

    for _, group in working.groupby(
        group_columns,
        sort=False
    ):

        times = group[
            time_column
        ].to_numpy()

        indices = group[
            "_index"
        ].to_numpy()

        left = np.searchsorted(
            times,
            times - CONGESTION_WINDOW_MINUTES,
            side="left"
        )

        right = np.searchsorted(
            times,
            times,
            side="left"
        )

        counts = right - left

        result.loc[
            indices
        ] = counts

    return result


def safe_ratio(
    numerator: pd.Series,
    denominator: pd.Series
) -> pd.Series:

    ratio = (
        numerator
        /
        denominator.replace(0, np.nan)
    )

    return (
        ratio
        .replace(
            [np.inf, -np.inf],
            np.nan
        )
        .fillna(1.0)
        .clip(0, 10)
    )


def congestion_level(
    ratio: pd.Series
) -> pd.Series:

    return pd.cut(
        ratio,
        bins=[
            -np.inf,
            0.75,
            1.25,
            1.75,
            np.inf
        ],
        labels=[
            0,  # LOW
            1,  # NORMAL
            2,  # HIGH
            3   # VERY HIGH
        ]
    ).astype(int)


# ============================================================
# 5. OPEN-METEO HISTORICAL WEATHER
# ============================================================

def get_historical_weather(
    latitude: float,
    longitude: float,
    flight_date,
    flight_hour: int
) -> dict:
    """
    Fetches HISTORICAL weather only.

    Uses:
        airport latitude
        airport longitude
        exact historical date
        flight hour

    Open-Meteo Archive API is used.

    Returns only the essential weather variables.
    """

    if pd.isna(latitude) or pd.isna(longitude):

        return {}

    date = pd.Timestamp(
        flight_date
    ).strftime("%Y-%m-%d")

    params = {
        "latitude": float(latitude),
        "longitude": float(longitude),

        "start_date": date,
        "end_date": date,

        "hourly": [
            "temperature_2m",
            "precipitation",
            "wind_speed_10m",
            "visibility",
            "weather_code"
        ],

        "timezone": "auto"
    }

    try:

        response = openmeteo.weather_api(
            "https://archive-api.open-meteo.com/v1/archive",
            params=params
        )[0]

        hourly = response.Hourly()

        times = pd.date_range(
            start=pd.to_datetime(
                hourly.Time(),
                unit="s",
                utc=True
            ),
            end=pd.to_datetime(
                hourly.TimeEnd(),
                unit="s",
                utc=True
            ),
            freq=pd.Timedelta(
                seconds=hourly.Interval()
            ),
            inclusive="left"
        )

        data = pd.DataFrame({

            "time": times,

            "temperature":
                hourly.Variables(0)
                .ValuesAsNumpy(),

            "precipitation":
                hourly.Variables(1)
                .ValuesAsNumpy(),

            "wind_speed":
                hourly.Variables(2)
                .ValuesAsNumpy(),

            "visibility":
                hourly.Variables(3)
                .ValuesAsNumpy(),

            "weather_code":
                hourly.Variables(4)
                .ValuesAsNumpy()
        })

        # ----------------------------------------------------
        # Match the requested historical hour
        # ----------------------------------------------------

        row = data[
            data["time"].dt.hour == int(
                flight_hour
            )
        ]

        if row.empty:

            return {}

        row = row.iloc[0]

        return {

            "temperature":
                float(row["temperature"]),

            "precipitation":
                float(row["precipitation"]),

            "wind_speed":
                float(row["wind_speed"]),

            "visibility":
                float(row["visibility"]),

            "weather_code":
                float(row["weather_code"])
        }

    except Exception as exc:

        print(
            f"[WARNING] Weather API failed: {exc}"
        )

        return {}


# ============================================================
# 6. WEATHER FEATURES
# ============================================================

def add_weather_features(
    df: pd.DataFrame
) -> pd.DataFrame:

    print(
        "[INFO] Adding historical weather..."
    )

    df = df.copy()

    weather_columns = [
        "temperature",
        "precipitation",
        "wind_speed",
        "visibility",
        "weather_code"
    ]

    for prefix in [
        "origin",
        "destination"
    ]:

        for column in weather_columns:

            df[
                f"{prefix}_{column}"
            ] = np.nan

    df[
        "weather_severity"
    ] = np.nan

    # --------------------------------------------------------
    # Cache API results
    # --------------------------------------------------------

    cache = {}

    # --------------------------------------------------------
    # Weather lookup
    # --------------------------------------------------------

    for index, row in df.iterrows():

        date = row["flight_date"]

        # ====================================================
        # ORIGIN WEATHER
        # ====================================================

        origin_hour = int(
            row["departure_hour"]
        )

        origin_key = (
            round(
                row["origin_latitude"],
                4
            ),
            round(
                row["origin_longitude"],
                4
            ),
            str(date.date()),
            origin_hour
        )

        if origin_key not in cache:

            cache[
                origin_key
            ] = get_historical_weather(
                row["origin_latitude"],
                row["origin_longitude"],
                date,
                origin_hour
            )

        origin_weather = cache[
            origin_key
        ]

        # ====================================================
        # DESTINATION WEATHER
        # ====================================================

        destination_time = pd.to_datetime(
            row["scheduled_arrival"],
            errors="coerce"
        )

        destination_hour = (
            int(destination_time.hour)
            if not pd.isna(destination_time)
            else origin_hour
        )

        destination_key = (
            round(
                row["destination_latitude"],
                4
            ),
            round(
                row["destination_longitude"],
                4
            ),
            str(date.date()),
            destination_hour
        )

        if destination_key not in cache:

            cache[
                destination_key
            ] = get_historical_weather(
                row["destination_latitude"],
                row["destination_longitude"],
                date,
                destination_hour
            )

        destination_weather = cache[
            destination_key
        ]

        # ====================================================
        # STORE ORIGIN
        # ====================================================

        for column in weather_columns:

            df.at[
                index,
                f"origin_{column}"
            ] = origin_weather.get(
                column
            )

        # ====================================================
        # STORE DESTINATION
        # ====================================================

        for column in weather_columns:

            df.at[
                index,
                f"destination_{column}"
            ] = destination_weather.get(
                column
            )

        # ====================================================
        # WEATHER SEVERITY
        # ====================================================

        df.at[
            index,
            "weather_severity"
        ] = calculate_weather_severity(
            origin_weather,
            destination_weather
        )

    return df


# ============================================================
# WEATHER SEVERITY
# ============================================================

def calculate_weather_severity(
    origin: dict,
    destination: dict
) -> float:
    """
    Creates one simple 0-1 weather severity score.
    """

    scores = []

    for weather in [
        origin,
        destination
    ]:

        if not weather:
            continue

        score = 0.0

        precipitation = weather.get(
            "precipitation",
            0
        )

        wind = weather.get(
            "wind_speed",
            0
        )

        visibility = weather.get(
            "visibility",
            10000
        )

        code = weather.get(
            "weather_code",
            0
        )

        # Rain / precipitation
        if precipitation >= 5:
            score += 0.30

        elif precipitation >= 1:
            score += 0.15

        # Wind
        if wind >= 50:
            score += 0.30

        elif wind >= 30:
            score += 0.15

        # Visibility
        if visibility < 1000:
            score += 0.30

        elif visibility < 3000:
            score += 0.15

        # Severe weather
        if code >= 95:
            score += 0.30

        elif code >= 80:
            score += 0.20

        elif code >= 60:
            score += 0.10

        scores.append(
            min(score, 1.0)
        )

    if not scores:
        return 0.0

    return max(scores)


# ============================================================
# 7. FINAL ML FEATURES
# ============================================================

FEATURE_COLUMNS = [

    # --------------------------------------------------------
    # FLIGHT / SCHEDULE - 9
    # --------------------------------------------------------

    "airline_id",
    "aircraft_id",

    "origin_airport_id",
    "destination_airport_id",

    "departure_hour",
    "day_of_week",
    "month",

    "scheduled_time_minutes",
    "distance_miles",

    # --------------------------------------------------------
    # HISTORICAL DELAY - 6
    # --------------------------------------------------------

    "airline_delay_rate",
    "airline_average_delay",

    "route_delay_rate",
    "route_average_delay",

    "flight_number_delay_rate",
    "flight_number_average_delay",

    # --------------------------------------------------------
    # CONGESTION - 9
    # --------------------------------------------------------

    "origin_flights_1h",
    "destination_flights_1h",
    "route_flights_1h",

    "origin_congestion_ratio",
    "destination_congestion_ratio",
    "route_congestion_ratio",

    "origin_congestion_level",
    "destination_congestion_level",
    "route_congestion_level",

    # --------------------------------------------------------
    # WEATHER - 11
    # --------------------------------------------------------

    "origin_temperature",
    "origin_precipitation",
    "origin_wind_speed",
    "origin_visibility",
    "origin_weather_code",

    "destination_temperature",
    "destination_precipitation",
    "destination_wind_speed",
    "destination_visibility",
    "destination_weather_code",

    "weather_severity"
]


# ============================================================
# 8. BUILD FINAL DATASET
# ============================================================

def build_features(
    use_weather: bool = True
) -> pd.DataFrame:

    print()
    print("=" * 60)
    print("FLITZZ FEATURE BUILDER")
    print("=" * 60)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    df = load_flights()

    # --------------------------------------------------------
    # Clean
    # --------------------------------------------------------

    df = clean_data(df)

    # --------------------------------------------------------
    # Historical flight-number features
    # --------------------------------------------------------

    df = add_flight_history(df)

    # --------------------------------------------------------
    # Congestion
    # --------------------------------------------------------

    df = add_congestion_features(df)

    # --------------------------------------------------------
    # Historical weather
    # --------------------------------------------------------

    if use_weather:

        df = add_weather_features(df)

    # --------------------------------------------------------
    # Missing values
    # --------------------------------------------------------

    numeric_features = [
        column
        for column in FEATURE_COLUMNS
        if column in df.columns
    ]

    df[
        numeric_features
    ] = df[
        numeric_features
    ].apply(
        pd.to_numeric,
        errors="coerce"
    )

    # --------------------------------------------------------
    # Final dataset
    # --------------------------------------------------------

    final_columns = [
    "flight_id",
    "flight_date"
    ] + FEATURE_COLUMNS + [
    "delayed_15"
    ]

    missing = [
        column
        for column in final_columns
        if column not in df.columns
    ]

    if missing:

        raise ValueError(
            "Missing required columns:\n"
            + "\n".join(missing)
        )

    result = df[
        final_columns
    ].copy()

    # --------------------------------------------------------
    # Remove rows without target
    # --------------------------------------------------------

    result = result[
        result["delayed_15"]
        .notna()
    ]

    result["delayed_15"] = (
        result["delayed_15"]
        .astype(int)
    )

    print()
    print("=" * 60)
    print("FEATURE DATASET READY")
    print("=" * 60)

    print(
        f"Rows: {len(result):,}"
    )

    print(
        f"Features: {len(FEATURE_COLUMNS)}"
    )

    print(
        "\nTarget distribution:"
    )

    print(
        result[
            "delayed_15"
        ].value_counts(
            normalize=True
        )
    )

    return result


# ============================================================
# RUN DIRECTLY
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("FLITZZ FEATURE BUILDER")
    print("=" * 60)

    if not test_database_connection():
        raise SystemExit(
            "Stopping because PostgreSQL connection failed."
        )

    features = build_features(
        use_weather=True
    )

    print(
        "\nFinal features:"
    )

    for i, feature in enumerate(
        FEATURE_COLUMNS,
        start=1
    ):
        print(
            f"{i:02d}. {feature}"
        )

    # Optional sample
    features.head(
        10000
    ).to_csv(
        "feature_dataset_sample.csv",
        index=False
    )

    print(
        "\n[OK] Sample saved:"
        " feature_dataset_sample.csv"
    )