"""
FLITZZ - DATABASE-BACKED FLIGHT DELAY PREDICTION API

Flow
----
Frontend sends only a flight ID or flight number.
Backend:
1. Looks the flight up in PostgreSQL.
2. Fetches the complete operational flight row.
3. Fetches the linked delay row only for display/validation.
4. Builds the exact 17 LightGBM features.
5. Builds the XGBoost dataframe from its saved schema.
6. Runs XGBoost classification.
7. Runs LightGBM regression.
8. Produces operational risk/action.
9. Produces model-factor explanations from the features available to the
   current 17-feature model.
10. Returns everything needed by the Predict page.

IMPORTANT
---------
The actual arrival delay is NEVER passed to either model.
It is returned separately as a historical validation value when the
selected database row has already-completed flight data.

Current trained model contract:
< 15 min  -> NORMAL / WAIT
15-29 min -> MANUAL ACTION
>= 30 min  -> AUTOMATIC ACTION
"""

from __future__ import annotations

import os
import time
from datetime import date, datetime, time as dt_time
from pathlib import Path
from typing import Any, Optional

import joblib
import xgboost as xgb
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text


# ============================================================================
# APP / ENV
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        f"DATABASE_URL not found. Expected .env at {BASE_DIR / '.env'}"
    )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
)

app = FastAPI(
    title="FLITZZ Flight Delay Prediction API",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# MODEL PATHS
# ============================================================================

MODEL_DIR = BASE_DIR / "ml" / "models"

XGB_MODEL_PATH = MODEL_DIR / "xgboost_classifier.pkl"
XGB_SCHEMA_PATH = MODEL_DIR / "feature_schema.pkl"

# Regression is a separate direct LightGBM pickle supplied by your friend.
# It is intentionally kept separate from the XGBoost classifier contract.
LGB_MODEL_PATH = MODEL_DIR / "flight_delay_champion.pkl"


# ============================================================================
# MODEL STATE
# ============================================================================

xgb_model: Any = None
xgb_schema: dict[str, Any] = {}

lgb_model: Any = None
lgb_artifact: dict[str, Any] = {}

lgb_features: list[str] = []
lgb_cat_targets: list[str] = []
lookup_priors: dict[str, dict[str, float]] = {}
global_mean: float = 0.0


EXPECTED_LGB_FEATURES = [
    "DEPARTURE_DELAY",
    "TAXI_OUT",
    "SCHEDULED_TIME",
    "DISTANCE",
    "SCHEDULED_SPEED",
    "DEP_MIN_OF_DAY",
    "MONTH",
    "DAY",
    "DAY_OF_WEEK",
    "AIRLINE",
    "ORIGIN_AIRPORT",
    "DESTINATION_AIRPORT",
    "ROUTE",
    "AIRLINE_HIST_DELAY",
    "ORIGIN_AIRPORT_HIST_DELAY",
    "DESTINATION_AIRPORT_HIST_DELAY",
    "ROUTE_HIST_DELAY",
]

EXPECTED_LGB_CATEGORICAL = [
    "AIRLINE",
    "ORIGIN_AIRPORT",
    "DESTINATION_AIRPORT",
    "ROUTE",
]


# ============================================================================
# MODEL LOADING
# ============================================================================

def load_models() -> None:
    global xgb_model
    global xgb_schema
    global lgb_model
    global lgb_artifact
    global lgb_features
    global lgb_cat_targets

    # ------------------------------------------------------------------------
    # XGBoost — YOUR 24-feature classification model
    # ------------------------------------------------------------------------
    if not XGB_MODEL_PATH.exists():
        raise RuntimeError(f"Missing XGBoost model: {XGB_MODEL_PATH}")

    if not XGB_SCHEMA_PATH.exists():
        raise RuntimeError(f"Missing XGBoost schema: {XGB_SCHEMA_PATH}")

    xgb_model = joblib.load(XGB_MODEL_PATH)
    xgb_schema = joblib.load(XGB_SCHEMA_PATH)

    print("[OK] XGBoost classifier loaded")
    print(f"[OK] XGBoost model: {type(xgb_model)}")

    # ------------------------------------------------------------------------
    # LightGBM — FRIEND'S DIRECT 17-FEATURE REGRESSION PICKLE
    # ------------------------------------------------------------------------
    if not LGB_MODEL_PATH.exists():
        raise RuntimeError(
            f"Missing friend's LightGBM regression pickle: {LGB_MODEL_PATH}"
        )

    lgb_artifact = {}
    artifact = joblib.load(LGB_MODEL_PATH)

    # A direct model is expected. We also tolerate a simple wrapper dict,
    # but NEVER silently accept the 34-feature champion artifact here.
    if isinstance(artifact, dict):
        if "model" in artifact:
            lgb_model = artifact["model"]
        elif "models" in artifact and artifact["models"]:
            lgb_model = artifact["models"][0]
        else:
            raise RuntimeError(
                "The configured LightGBM regression pickle is a dict, "
                "but no direct 'model'/'models' entry was found."
            )

        lgb_features = list(
            artifact.get("final_features", EXPECTED_LGB_FEATURES)
        )
        lgb_cat_targets = list(
            artifact.get("cat_targets", EXPECTED_LGB_CATEGORICAL)
        )
    else:
        lgb_model = artifact
        lgb_features = EXPECTED_LGB_FEATURES.copy()
        lgb_cat_targets = EXPECTED_LGB_CATEGORICAL.copy()

    if lgb_features != EXPECTED_LGB_FEATURES:
        raise RuntimeError(
            "FRIEND LIGHTGBM FEATURE MISMATCH. "
            "This page expects the direct 17-feature regression model.\n"
            f"Expected: {EXPECTED_LGB_FEATURES}\n"
            f"Found:    {lgb_features}"
        )

    if lgb_cat_targets != EXPECTED_LGB_CATEGORICAL:
        raise RuntimeError(
            "FRIEND LIGHTGBM CATEGORICAL FEATURE MISMATCH.\n"
            f"Expected: {EXPECTED_LGB_CATEGORICAL}\n"
            f"Found:    {lgb_cat_targets}"
        )

    print("[OK] Friend LightGBM direct pickle loaded")
    print(f"[OK] LightGBM features: {len(lgb_features)}")
    print(f"[OK] LightGBM categorical: {lgb_cat_targets}")
    print("[OK] Regression feature schema verified: EXACT 17")


load_models()


# ============================================================================
# REQUEST
# ============================================================================

class FlightLookupRequest(BaseModel):
    flight_key: str = Field(
        ...,
        min_length=1,
        description="Database flight_id or flight_number.",
        examples=["123456", "AA123"],
    )


# ============================================================================
# DB HELPERS
# ============================================================================

def db_value(value: Any) -> Any:
    """Convert DB/NumPy/Pandas values to JSON-safe Python values."""
    if value is None:
        return None

    if isinstance(value, (np.integer,)):
        return int(value)

    if isinstance(value, (np.floating,)):
        if np.isnan(value):
            return None
        return float(value)

    if isinstance(value, (np.bool_,)):
        return bool(value)

    if isinstance(value, (datetime, date, dt_time)):
        return value.isoformat()

    if pd.isna(value):
        return None

    return value


def get_flight_from_db(flight_key: str) -> dict[str, Any]:
    """
    Resolve either:
      - numeric flight_id
      - flight_number

    If a flight number appears multiple times, the most recent database
    record is selected. The response tells the frontend how it was resolved.
    """

    key = flight_key.strip()

    if not key:
        raise HTTPException(
            status_code=400,
            detail="Enter a flight ID or flight number.",
        )

    numeric_id: Optional[int] = None
    if key.isdigit():
        try:
            numeric_id = int(key)
        except ValueError:
            numeric_id = None

    # The schema is the user's normalized PostgreSQL schema:
    # flights -> airlines / aircraft / airports -> flight_delay.
    if numeric_id is not None:
        query = text(
            """
            SELECT
                f.flight_id,
                f.source_row_id,
                f.flight_number,
                f.flight_date,
                f.year,
                f.month,
                f.day,
                f.day_of_week,
                f.airline_id,
                f.origin_airport_id,
                f.destination_airport_id,

                al.iata_code AS airline_code,
                al.airline_name,

                ac.tail_number,

                oa.iata_code AS origin_airport,
                oa.airport_name AS origin_name,
                oa.city AS origin_city,

                da.iata_code AS destination_airport,
                da.airport_name AS destination_name,
                da.city AS destination_city,

                f.scheduled_departure,
                f.scheduled_arrival,
                f.departure_time,
                f.arrival_time,

                f.scheduled_time_minutes,
                f.elapsed_time_minutes,
                f.air_time_minutes,
                f.taxi_out_minutes,
                f.taxi_in_minutes,

                f.wheels_off,
                f.wheels_on,

                f.distance_miles,
                f.diverted,
                f.cancelled,

                f.departure_hour,
                f.departure_minute,
                f.arrival_hour,
                f.arrival_minute,

                f.is_weekend,
                f.season,
                f.departure_period,
                f.route,
                f.flight_datetime,

                fd.departure_delay_minutes,
                fd.arrival_delay_minutes,
                fd.delayed_15,
                fd.delay_status,
                fd.delay_category

            FROM flights f
            JOIN airlines al
                ON al.airline_id = f.airline_id
            LEFT JOIN aircraft ac
                ON ac.aircraft_id = f.aircraft_id
            JOIN airports oa
                ON oa.airport_id = f.origin_airport_id
            JOIN airports da
                ON da.airport_id = f.destination_airport_id
            LEFT JOIN flight_delay fd
                ON fd.flight_id = f.flight_id

            WHERE f.flight_id = :flight_id
            LIMIT 1
            """
        )
        params = {"flight_id": numeric_id}
        resolution = "flight_id"

    else:
        query = text(
            """
            SELECT
                f.flight_id,
                f.source_row_id,
                f.flight_number,
                f.flight_date,
                f.year,
                f.month,
                f.day,
                f.day_of_week,
                f.airline_id,
                f.origin_airport_id,
                f.destination_airport_id,

                al.iata_code AS airline_code,
                al.airline_name,

                ac.tail_number,

                oa.iata_code AS origin_airport,
                oa.airport_name AS origin_name,
                oa.city AS origin_city,

                da.iata_code AS destination_airport,
                da.airport_name AS destination_name,
                da.city AS destination_city,

                f.scheduled_departure,
                f.scheduled_arrival,
                f.departure_time,
                f.arrival_time,

                f.scheduled_time_minutes,
                f.elapsed_time_minutes,
                f.air_time_minutes,
                f.taxi_out_minutes,
                f.taxi_in_minutes,

                f.wheels_off,
                f.wheels_on,

                f.distance_miles,
                f.diverted,
                f.cancelled,

                f.departure_hour,
                f.departure_minute,
                f.arrival_hour,
                f.arrival_minute,

                f.is_weekend,
                f.season,
                f.departure_period,
                f.route,
                f.flight_datetime,

                fd.departure_delay_minutes,
                fd.arrival_delay_minutes,
                fd.delayed_15,
                fd.delay_status,
                fd.delay_category

            FROM flights f
            JOIN airlines al
                ON al.airline_id = f.airline_id
            LEFT JOIN aircraft ac
                ON ac.aircraft_id = f.aircraft_id
            JOIN airports oa
                ON oa.airport_id = f.origin_airport_id
            JOIN airports da
                ON da.airport_id = f.destination_airport_id
            LEFT JOIN flight_delay fd
                ON fd.flight_id = f.flight_id

            WHERE UPPER(f.flight_number) = UPPER(:flight_number)

            ORDER BY
                f.flight_datetime DESC NULLS LAST,
                f.flight_id DESC

            LIMIT 1
            """
        )
        params = {"flight_number": key}
        resolution = "flight_number"

    with engine.connect() as conn:
        row = conn.execute(query, params).mappings().first()

    if not row:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No flight found for '{key}'. "
                "Enter a valid database flight ID or flight number."
            ),
        )

    data = {k: db_value(v) for k, v in row.items()}
    data["_lookup_resolution"] = resolution
    data["_lookup_key"] = key

    return data


# ============================================================================
# FEATURE BUILDING
# ============================================================================

def parse_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    if isinstance(value, datetime):
        return value.date()

    return datetime.strptime(str(value), "%Y-%m-%d").date()


def parse_time(value: Any, fallback: str = "00:00") -> dt_time:
    if value is None:
        return datetime.strptime(fallback, "%H:%M").time()

    if isinstance(value, dt_time):
        return value

    if isinstance(value, datetime):
        return value.time()

    value_str = str(value)

    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(value_str, fmt).time()
        except ValueError:
            pass

    raise ValueError(f"Invalid time value: {value}")


def numeric(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


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


def _season(month: int) -> str:
    return {
        12: "Winter", 1: "Winter", 2: "Winter",
        3: "Spring", 4: "Spring", 5: "Spring",
        6: "Summer", 7: "Summer", 8: "Summer",
        9: "Autumn", 10: "Autumn", 11: "Autumn",
    }.get(month, "UNKNOWN")


def _departure_period(hour: int) -> str:
    if 5 <= hour <= 11:
        return "Morning"
    if 12 <= hour <= 16:
        return "Afternoon"
    if 17 <= hour <= 20:
        return "Evening"
    return "Night"


def _history_row(
    table: str,
    key_columns: str,
    key_params: dict[str, Any],
    flight_date: date,
) -> dict[str, Any]:
    query = text(
        f"""
        SELECT
            previous_flights,
            previous_delays,
            delay_rate,
            average_delay_minutes
        FROM {table}
        WHERE {key_columns}
          AND observation_date = :flight_date
        LIMIT 1
        """
    )

    with engine.connect() as conn:
        row = conn.execute(
            query,
            {**key_params, "flight_date": flight_date},
        ).mappings().first()

    return dict(row) if row else {}


def _airport_history(
    airport_id: int,
    flight_date: date,
    role: str,
    exclude_flight_id: int | None = None,
) -> float | None:
    """
    Historical mean arrival delay for the airport before the selected flight.

    This is used only for the friend's 17-feature regression model.
    The selected flight itself is excluded so its actual arrival delay can
    never leak into the prediction.
    """
    column = (
        "origin_airport_id"
        if role == "origin"
        else "destination_airport_id"
    )

    query = text(
        f"""
        SELECT AVG(fd.arrival_delay_minutes) AS average_delay
        FROM flights f
        INNER JOIN flight_delay fd
            ON fd.flight_id = f.flight_id
        WHERE f.{column} = :airport_id
          AND f.flight_date < :flight_date
          AND f.cancelled = FALSE
          AND f.diverted = FALSE
          AND fd.arrival_delay_minutes IS NOT NULL
          AND (:exclude_flight_id IS NULL OR f.flight_id <> :exclude_flight_id)
        """
    )

    with engine.connect() as conn:
        row = conn.execute(
            query,
            {
                "airport_id": airport_id,
                "flight_date": flight_date,
                "exclude_flight_id": exclude_flight_id,
            },
        ).mappings().first()

    if not row or row.get("average_delay") is None:
        return None

    return numeric(row["average_delay"], 0.0)


def _traffic_features(
    flight: dict[str, Any],
) -> dict[str, float]:
    """
    Match the training congestion design:
      - 1h origin/destination/route counts from the previous hour
      - route 3h count from the previous three hours
      - ratios: origin/destination / 20, route / 10, clipped to [0, 2]
    """
    flight_dt = pd.to_datetime(
        flight.get("flight_datetime"),
        errors="coerce",
        utc=True,
    )

    if pd.isna(flight_dt):
        return {
            "route_flights_1h": 0.0,
            "route_flights_3h": 0.0,
            "origin_flights_1h": 0.0,
            "destination_flights_1h": 0.0,
            "route_congestion_ratio": 0.0,
            "origin_congestion_ratio": 0.0,
            "destination_congestion_ratio": 0.0,
        }

    hour_end = flight_dt.floor("h")
    one_hour_start = hour_end - pd.Timedelta(hours=1)
    three_hour_start = hour_end - pd.Timedelta(hours=3)

    query = text(
        """
        SELECT
            COUNT(*) FILTER (
                WHERE origin_airport_id = :origin_id
            ) AS origin_flights_1h,
            COUNT(*) FILTER (
                WHERE destination_airport_id = :destination_id
            ) AS destination_flights_1h,
            COUNT(*) FILTER (
                WHERE origin_airport_id = :origin_id
                  AND destination_airport_id = :destination_id
            ) AS route_flights_1h,
            COUNT(*) FILTER (
                WHERE origin_airport_id = :origin_id
                  AND destination_airport_id = :destination_id
            ) AS route_flights_3h
        FROM flights
        WHERE cancelled = FALSE
          AND diverted = FALSE
          AND flight_datetime IS NOT NULL
          AND flight_datetime >= :three_hour_start
          AND flight_datetime < :hour_end
        """
    )

    with engine.connect() as conn:
        row = conn.execute(
            query,
            {
                "origin_id": int(flight["origin_airport_id"]),
                "destination_id": int(flight["destination_airport_id"]),
                "three_hour_start": three_hour_start.to_pydatetime(),
                "hour_end": hour_end.to_pydatetime(),
            },
        ).mappings().first()

    values = {
        key: numeric((row or {}).get(key), 0.0)
        for key in (
            "origin_flights_1h",
            "destination_flights_1h",
            "route_flights_1h",
            "route_flights_3h",
        )
    }

    # The 1h counts must use only the immediately preceding hour.
    one_hour_query = text(
        """
        SELECT
            COUNT(*) FILTER (
                WHERE origin_airport_id = :origin_id
            ) AS origin_flights_1h,
            COUNT(*) FILTER (
                WHERE destination_airport_id = :destination_id
            ) AS destination_flights_1h,
            COUNT(*) FILTER (
                WHERE origin_airport_id = :origin_id
                  AND destination_airport_id = :destination_id
            ) AS route_flights_1h
        FROM flights
        WHERE cancelled = FALSE
          AND diverted = FALSE
          AND flight_datetime IS NOT NULL
          AND flight_datetime >= :one_hour_start
          AND flight_datetime < :hour_end
        """
    )

    with engine.connect() as conn:
        one_hour = conn.execute(
            one_hour_query,
            {
                "origin_id": int(flight["origin_airport_id"]),
                "destination_id": int(flight["destination_airport_id"]),
                "one_hour_start": one_hour_start.to_pydatetime(),
                "hour_end": hour_end.to_pydatetime(),
            },
        ).mappings().first()

    if one_hour:
        values["origin_flights_1h"] = numeric(
            one_hour.get("origin_flights_1h"), 0.0
        )
        values["destination_flights_1h"] = numeric(
            one_hour.get("destination_flights_1h"), 0.0
        )
        values["route_flights_1h"] = numeric(
            one_hour.get("route_flights_1h"), 0.0
        )

    values["origin_congestion_ratio"] = float(
        np.clip(values["origin_flights_1h"] / 20.0, 0.0, 2.0)
    )
    values["destination_congestion_ratio"] = float(
        np.clip(values["destination_flights_1h"] / 20.0, 0.0, 2.0)
    )
    values["route_congestion_ratio"] = float(
        np.clip(values["route_flights_1h"] / 10.0, 0.0, 2.0)
    )

    return values


def build_model_features(
    flight: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """
    Build TWO independent model contracts.

    XGBoost:
        Your 24-feature classifier, including traffic/congestion.

    LightGBM:
        Friend's separate direct 17-feature regression pickle.

    Actual arrival delay is never passed to either model.
    """
    flight_date = parse_date(flight["flight_date"])
    scheduled_departure = parse_time(
        flight.get("scheduled_departure"),
        "00:00",
    )

    departure_hour = scheduled_departure.hour
    departure_minute = scheduled_departure.minute

    airline = str(
        flight.get("airline_code") or ""
    ).strip().upper()
    origin = str(
        flight.get("origin_airport") or ""
    ).strip().upper()
    destination = str(
        flight.get("destination_airport") or ""
    ).strip().upper()
    route = (
        str(flight.get("route") or "").strip().upper()
        or f"{origin}_{destination}"
    )

    scheduled_time = numeric(
        flight.get("scheduled_time_minutes"),
        0.0,
    )
    distance = numeric(
        flight.get("distance_miles"),
        0.0,
    )
    departure_delay = numeric(
        flight.get("departure_delay_minutes"),
        0.0,
    )
    taxi_out = numeric(
        flight.get("taxi_out_minutes"),
        0.0,
    )

    scheduled_speed = (
        distance / scheduled_time
        if scheduled_time > 0
        else 0.0
    )
    dep_min_of_day = departure_hour * 60 + departure_minute
    day_of_week = numeric(
        flight.get("day_of_week"),
        flight_date.isoweekday(),
    )

    # Historical values for YOUR XGBoost classifier.
    airline_history = _history_row(
        "airline_history",
        "airline_id = :airline_id",
        {"airline_id": int(flight["airline_id"])},
        flight_date,
    )

    route_history = _history_row(
        "route_history",
        (
            "origin_airport_id = :origin_id "
            "AND destination_airport_id = :destination_id"
        ),
        {
            "origin_id": int(flight["origin_airport_id"]),
            "destination_id": int(flight["destination_airport_id"]),
        },
        flight_date,
    )

    traffic = _traffic_features(flight)

    xgb_features = {
        "airline": airline,
        "origin_airport": origin,
        "destination_airport": destination,
        "departure_hour": departure_hour,
        "departure_period": _departure_period(departure_hour),
        "day_of_week": day_of_week,
        "month": flight_date.month,
        "season": _season(flight_date.month),
        "distance_miles": distance,

        "route_average_delay_minutes": db_value(
            route_history.get("average_delay_minutes")
        ),
        "route_delay_rate": db_value(
            route_history.get("delay_rate")
        ),
        "route_previous_flights": db_value(
            route_history.get("previous_flights")
        ),
        "route_previous_delays": db_value(
            route_history.get("previous_delays")
        ),

        "airline_average_delay_minutes": db_value(
            airline_history.get("average_delay_minutes")
        ),
        "airline_delay_rate": db_value(
            airline_history.get("delay_rate")
        ),
        "airline_previous_flights": db_value(
            airline_history.get("previous_flights")
        ),
        "airline_previous_delays": db_value(
            airline_history.get("previous_delays")
        ),

        **traffic,
    }

    origin_airport_hist = _airport_history(
        int(flight["origin_airport_id"]),
        flight_date,
        "origin",
        int(flight["flight_id"]),
    )
    destination_airport_hist = _airport_history(
        int(flight["destination_airport_id"]),
        flight_date,
        "destination",
        int(flight["flight_id"]),
    )

    # Friend's direct 17-feature LightGBM contract.
    lgb_features = {
        "DEPARTURE_DELAY": departure_delay,
        "TAXI_OUT": taxi_out,
        "SCHEDULED_TIME": scheduled_time,
        "DISTANCE": distance,
        "SCHEDULED_SPEED": scheduled_speed,
        "DEP_MIN_OF_DAY": dep_min_of_day,
        "MONTH": flight_date.month,
        "DAY": flight_date.day,
        "DAY_OF_WEEK": day_of_week,
        "AIRLINE": airline,
        "ORIGIN_AIRPORT": origin,
        "DESTINATION_AIRPORT": destination,
        "ROUTE": route,
        "AIRLINE_HIST_DELAY": numeric(
            airline_history.get("average_delay_minutes")
        ),
        "ORIGIN_AIRPORT_HIST_DELAY": (
            origin_airport_hist
        ),
        "DESTINATION_AIRPORT_HIST_DELAY": (
            destination_airport_hist
        ),
        "ROUTE_HIST_DELAY": numeric(
            route_history.get("average_delay_minutes")
        ),
    }

    derived = {
        "scheduled_speed": scheduled_speed,
        "departure_minute_of_day": dep_min_of_day,
        "traffic": traffic,
        "xgb_feature_count": len(XGB_FEATURES),
        "lgb_feature_count": len(EXPECTED_LGB_FEATURES),
    }

    return xgb_features, lgb_features, derived


# ============================================================================
# XGBOOST
# ============================================================================

def get_xgb_config() -> dict[str, Any]:
    if not isinstance(xgb_schema, dict):
        raise RuntimeError("feature_schema.pkl is not a dictionary.")

    # Current training schema.
    if "classification" in xgb_schema:
        return xgb_schema["classification"]

    # Older compatibility schema.
    if "xgboost" in xgb_schema:
        return xgb_schema["xgboost"]

    return xgb_schema


def _xgb_contributions(
    X: pd.DataFrame,
    feature_columns: list[str],
) -> list[dict[str, Any]]:
    """
    Per-flight XGBoost contribution using the trained booster.

    Positive contribution => pushes the current prediction toward
    delayed_15=1. Negative contribution => pushes it toward 0.

    This is an explanation of model output, not a causal claim.
    """
    try:
        booster = xgb_model.get_booster()
        matrix = xgb.DMatrix(X)
        contribution_matrix = booster.predict(
            matrix,
            pred_contribs=True,
        )

        contributions = contribution_matrix[0][:-1]

        result = []
        for feature, contribution in zip(
            feature_columns,
            contributions,
        ):
            result.append({
                "feature": feature,
                "contribution": float(contribution),
                "direction": (
                    "INCREASES_RISK"
                    if contribution > 0
                    else "REDUCES_RISK"
                    if contribution < 0
                    else "NEUTRAL"
                ),
            })

        return sorted(
            result,
            key=lambda item: abs(item["contribution"]),
            reverse=True,
        )

    except Exception as exc:
        print(
            "[WARNING] Per-feature XGBoost contributions unavailable:",
            exc,
        )
        return []


def predict_xgboost(
    model_features: dict[str, Any],
) -> dict[str, Any]:
    config = get_xgb_config()

    feature_columns = list(
        config.get("feature_columns", [])
    )

    categorical_features = list(
        config.get("categorical_features", [])
    )

    encoder = config.get("encoder")
    medians = config.get(
        "numerical_medians",
        {},
    ) or {}

    if feature_columns != XGB_FEATURES:
        raise RuntimeError(
            "XGBOOST FEATURE CONTRACT MISMATCH. "
            "The loaded pkl/schema must be the 24-feature FLITZZ classifier.\\n"
            f"Expected: {XGB_FEATURES}\\n"
            f"Found:    {feature_columns}"
        )

    df = pd.DataFrame([model_features])
    df = df[feature_columns].copy()

    for column in categorical_features:
        df[column] = (
            df[column]
            .fillna("UNKNOWN")
            .astype(str)
        )

    numerical_features = [
        c
        for c in feature_columns
        if c not in categorical_features
    ]

    for column in numerical_features:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

        fallback = numeric(
            medians.get(column, 0.0),
            0.0,
        )

        df[column] = (
            df[column]
            .replace(
                [np.inf, -np.inf],
                np.nan,
            )
            .fillna(fallback)
        )

    if categorical_features:
        if encoder is None:
            raise RuntimeError(
                "XGBoost encoder missing from feature_schema.pkl"
            )

        df[categorical_features] = encoder.transform(
            df[categorical_features]
        )

    X = df.astype(np.float32)

    probability = float(
        xgb_model.predict_proba(X)[0][1]
    )

    probability = min(
        max(probability, 0.0),
        1.0,
    )

    threshold = numeric(
        config.get("threshold", 0.50),
        0.50,
    )
    delayed_15 = probability >= threshold

    if probability >= 0.70:
        probability_risk = "VERY_HIGH"
    elif probability >= 0.50:
        probability_risk = "HIGH"
    elif probability >= 0.30:
        probability_risk = "MEDIUM"
    else:
        probability_risk = "LOW"

    contributions = _xgb_contributions(
        X,
        feature_columns,
    )

    feature_values = {}
    for feature in feature_columns:
        if feature in categorical_features:
            feature_values[feature] = db_value(
                model_features.get(feature)
            )
        else:
            feature_values[feature] = db_value(
                df.iloc[0][feature]
            )

    for item in contributions:
        item["value"] = feature_values.get(
            item["feature"]
        )

    positive_contributors = [
        item
        for item in contributions
        if item["contribution"] > 0
    ]

    negative_contributors = [
        item
        for item in contributions
        if item["contribution"] < 0
    ]

    return {
        "delay_probability": probability,
        "delay_probability_percent": probability * 100.0,
        "delayed_15": delayed_15,
        "classification_threshold": threshold,
        "status": (
            "DELAYED"
            if delayed_15
            else "NOT_DELAYED"
        ),
        "probability_risk": probability_risk,

        # Exact model contract and live input values.
        "feature_count": len(feature_columns),
        "features": feature_columns,
        "categorical_features": categorical_features,
        "feature_values": feature_values,

        # Per-flight explanation.
        "feature_contributions": contributions,
        "top_risk_factors": positive_contributors[:6],
        "risk_reducing_factors": negative_contributors[:4],
    }


# ============================================================================
# LIGHTGBM
# ============================================================================

def predict_lightgbm(model_features: dict[str, Any]) -> dict[str, Any]:
    row = dict(model_features)

    df = pd.DataFrame([row])

    # The artifact has the exact 17-column contract.
    df = df[lgb_features].copy()

    for column in lgb_cat_targets:
        df[column] = (
            df[column]
            .fillna("UNKNOWN")
            .astype(str)
            .astype("category")
        )

    for column in df.columns:
        if column in lgb_cat_targets:
            continue

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

        df[column] = (
            df[column]
            .replace(
                [np.inf, -np.inf],
                np.nan,
            )
            .fillna(0.0)
        )

    if list(df.columns) != EXPECTED_LGB_FEATURES:
        raise RuntimeError(
            "LightGBM feature order changed unexpectedly."
        )

    print()
    print("[DEBUG] LIGHTGBM INPUT")
    print("-" * 70)
    print(df.to_string(index=False))
    print("-" * 70)

    raw_prediction = float(
        lgb_model.predict(df)[0]
    )

    # Preserve the model's raw precision.
    predicted_delay = max(
        0.0,
        raw_prediction,
    )

    print(
        f"[DEBUG] LightGBM raw prediction: "
        f"{raw_prediction:.6f}"
    )
    print(
        f"[DEBUG] LightGBM final prediction: "
        f"{predicted_delay:.6f}"
    )

    if predicted_delay >= 15:
        status = "DELAYED"
    else:
        status = "ON_TIME"

    if predicted_delay >= 45:
        risk_level = "CRITICAL"
    elif predicted_delay >= 30:
        risk_level = "HIGH"
    elif predicted_delay >= 15:
        risk_level = "MODERATE"
    else:
        risk_level = "LOW"

    if predicted_delay >= 30:
        recommended_action = "AUTOMATIC_ACTION"
    elif predicted_delay >= 15:
        recommended_action = "MANUAL_ACTION"
    else:
        recommended_action = "NORMAL_WAIT"

    return {
        "predicted_arrival_delay_minutes": predicted_delay,
        "status": status,
        "risk_level": risk_level,
        "recommended_action": recommended_action,
        "raw_prediction": raw_prediction,
    }


# ============================================================================
# OPERATIONAL EXPLANATION
# ============================================================================

def build_reasons(
    model_features: dict[str, Any],
    regression: dict[str, Any],
    classification: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Operational explanation, not a causal claim.

    Operational explanation for the separate models.

    XGBoost is the 24-feature classification model and DOES include
    historical/traffic congestion proxy features. The values are shown
    separately from the friend's 17-feature LightGBM regression inputs.

    These are model signals, not causal claims.
    """

    reasons: list[dict[str, Any]] = []

    departure_delay = numeric(
        model_features["DEPARTURE_DELAY"]
    )
    taxi_out = numeric(
        model_features["TAXI_OUT"]
    )

    route_hist = numeric(
        model_features["ROUTE_HIST_DELAY"]
    )
    origin_hist = numeric(
        model_features["ORIGIN_AIRPORT_HIST_DELAY"]
    )
    destination_hist = numeric(
        model_features["DESTINATION_AIRPORT_HIST_DELAY"]
    )
    airline_hist = numeric(
        model_features["AIRLINE_HIST_DELAY"]
    )

    predicted_delay = numeric(
        regression["predicted_arrival_delay_minutes"]
    )

    probability = numeric(
        classification["delay_probability_percent"]
    )

    # Current departure delay is the strongest direct operational signal.
    if departure_delay >= 30:
        reasons.append({
            "type": "departure_delay",
            "title": "Severe departure delay",
            "description": (
                f"The flight is already {departure_delay:.2f} minutes "
                "behind schedule at departure."
            ),
            "severity": "HIGH",
            "value": departure_delay,
        })
    elif departure_delay >= 15:
        reasons.append({
            "type": "departure_delay",
            "title": "Current departure delay",
            "description": (
                f"The flight has a {departure_delay:.2f}-minute "
                "departure delay."
            ),
            "severity": "MODERATE",
            "value": departure_delay,
        })
    elif departure_delay > 0:
        reasons.append({
            "type": "departure_delay",
            "title": "Small departure delay",
            "description": (
                f"The flight is currently {departure_delay:.2f} "
                "minutes behind schedule."
            ),
            "severity": "LOW",
            "value": departure_delay,
        })

    if taxi_out >= 30:
        reasons.append({
            "type": "taxi_out",
            "title": "Extended taxi-out",
            "description": (
                f"Taxi-out is {taxi_out:.2f} minutes, which is an "
                "elevated operational movement time."
            ),
            "severity": "HIGH",
            "value": taxi_out,
        })
    elif taxi_out >= 20:
        reasons.append({
            "type": "taxi_out",
            "title": "Elevated taxi-out",
            "description": (
                f"Taxi-out is {taxi_out:.2f} minutes and can contribute "
                "to arrival delay."
            ),
            "severity": "MODERATE",
            "value": taxi_out,
        })

    # Historical priors are mean delay values used by LightGBM.
    hist_candidates = [
        (
            route_hist,
            "Route historical delay",
            (
                f"Historical delay for route "
                f"{model_features['ROUTE']} is {route_hist:.2f} minutes."
            ),
        ),
        (
            origin_hist,
            "Origin historical delay",
            (
                f"Historical delay associated with origin "
                f"{model_features['ORIGIN_AIRPORT']} is "
                f"{origin_hist:.2f} minutes."
            ),
        ),
        (
            destination_hist,
            "Destination historical delay",
            (
                f"Historical delay associated with destination "
                f"{model_features['DESTINATION_AIRPORT']} is "
                f"{destination_hist:.2f} minutes."
            ),
        ),
        (
            airline_hist,
            "Airline historical delay",
            (
                f"Historical delay associated with airline "
                f"{model_features['AIRLINE']} is "
                f"{airline_hist:.2f} minutes."
            ),
        ),
    ]

    hist_candidates.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    for value, title, description in hist_candidates[:2]:
        if value > 0:
            severity = (
                "HIGH"
                if value >= 30
                else "MODERATE"
                if value >= 15
                else "LOW"
            )
            reasons.append({
                "type": "historical",
                "title": title,
                "description": description,
                "severity": severity,
                "value": value,
            })

    # Probability can be a useful operational signal even when regression
    # remains below 15 minutes.
    if probability >= 70:
        reasons.append({
            "type": "classification",
            "title": "High delay probability",
            "description": (
                f"XGBoost estimates a {probability:.2f}% probability "
                "of an arrival delay of at least 15 minutes."
            ),
            "severity": "HIGH",
            "value": probability,
        })
    elif probability >= 50:
        reasons.append({
            "type": "classification",
            "title": "Elevated delay probability",
            "description": (
                f"XGBoost estimates a {probability:.2f}% probability "
                "of an arrival delay of at least 15 minutes."
            ),
            "severity": "MODERATE",
            "value": probability,
        })

    # If nothing meaningful was found, say exactly that.
    if not reasons:
        reasons.append({
            "type": "baseline",
            "title": "No strong operational signal",
            "description": (
                f"The model predicts approximately "
                f"{predicted_delay:.6f} minutes of arrival delay "
                "with no strong operational factor crossing the "
                "configured explanation thresholds."
            ),
            "severity": "LOW",
            "value": predicted_delay,
        })

    # Deduplicate titles while preserving order.
    seen = set()
    unique = []
    for item in reasons:
        if item["title"] in seen:
            continue
        seen.add(item["title"])
        unique.append(item)

    return unique[:4]


# ============================================================================
# DECISION
# ============================================================================

def decision_message(action: str) -> str:
    if action == "AUTOMATIC_ACTION":
        return (
            "Predicted delay is 30 minutes or more. "
            "Trigger the operational action workflow."
        )

    if action == "MANUAL_ACTION":
        return (
            "Predicted delay is between 15 and 29 minutes. "
            "Send the flight for operations-team review."
        )

    return (
        "Predicted delay is below 15 minutes. "
        "Continue normal monitoring."
    )


# ============================================================================
# PREDICT
# ============================================================================

@app.post("/predict")
def predict(payload: FlightLookupRequest):
    started = time.perf_counter()

    try:
        print()
        print("=" * 70)
        print("NEW DATABASE-BACKED FLIGHT PREDICTION")
        print("=" * 70)

        # --------------------------------------------------------------------
        # 1. DB LOOKUP
        # --------------------------------------------------------------------
        print("[1] Looking up flight in PostgreSQL...")

        flight = get_flight_from_db(
            payload.flight_key
        )

        print(
            f"[OK] Flight resolved: "
            f"{flight['flight_id']} / "
            f"{flight['flight_number']}"
        )

        # --------------------------------------------------------------------
        # 2. FEATURES
        # --------------------------------------------------------------------
        print("[2] Building exact model features...")

        xgb_features, lgb_features, derived = build_model_features(
            flight
        )

        print(
            f"[OK] Built {len(xgb_features)} XGBoost classification features"
        )
        print(
            f"[OK] Built {len(lgb_features)} friend LightGBM regression features"
        )

        # --------------------------------------------------------------------
        # 3. XGBOOST — YOUR 24-FEATURE CLASSIFIER
        # --------------------------------------------------------------------
        print("[3] Running XGBoost classification...")

        classification = predict_xgboost(
            xgb_features
        )

        print(
            "[OK] XGBoost:",
            classification,
        )

        # --------------------------------------------------------------------
        # 4. LIGHTGBM
        # --------------------------------------------------------------------
        print("[4] Running LightGBM regression...")

        regression = predict_lightgbm(
            lgb_features
        )

        print(
            "[OK] LightGBM:",
            {
                k: v
                for k, v in regression.items()
                if k != "raw_prediction"
            },
        )

        # --------------------------------------------------------------------
        # 5. COMBINED DECISION
        # --------------------------------------------------------------------
        action = regression["recommended_action"]

        risk_level = regression["risk_level"]

        # Probability can elevate an otherwise low-minute prediction.
        # We do NOT downgrade the regression-based action.
        combined_risk = risk_level

        if (
            classification["probability_risk"]
            in {"HIGH", "VERY_HIGH"}
            and risk_level == "LOW"
        ):
            combined_risk = "MODERATE"

        reasons = build_reasons(
            lgb_features,
            regression,
            classification,
        )

        elapsed_ms = (
            time.perf_counter()
            - started
        ) * 1000.0

        # --------------------------------------------------------------------
        # 6. FLIGHT DISPLAY DATA
        # --------------------------------------------------------------------
        display_flight = {
            "flight_id": flight["flight_id"],
            "source_row_id": flight["source_row_id"],
            "flight_number": flight["flight_number"],
            "tail_number": flight["tail_number"],
            "flight_date": flight["flight_date"],
            "airline": flight["airline_code"],
            "airline_name": flight["airline_name"],
            "origin_airport": flight["origin_airport"],
            "origin_name": flight["origin_name"],
            "origin_city": flight["origin_city"],
            "destination_airport": flight["destination_airport"],
            "destination_name": flight["destination_name"],
            "destination_city": flight["destination_city"],
            "scheduled_departure": flight["scheduled_departure"],
            "scheduled_arrival": flight["scheduled_arrival"],
            "departure_time": flight["departure_time"],
            "arrival_time": flight["arrival_time"],
            "scheduled_time_minutes": flight["scheduled_time_minutes"],
            "elapsed_time_minutes": flight["elapsed_time_minutes"],
            "air_time_minutes": flight["air_time_minutes"],
            "taxi_out_minutes": flight["taxi_out_minutes"],
            "taxi_in_minutes": flight["taxi_in_minutes"],
            "departure_delay_minutes": flight["departure_delay_minutes"],
            "wheels_off": flight["wheels_off"],
            "wheels_on": flight["wheels_on"],
            "distance_miles": flight["distance_miles"],
            "diverted": flight["diverted"],
            "cancelled": flight["cancelled"],
            "route": lgb_features["ROUTE"],
        }

        # --------------------------------------------------------------------
        # 7. ACTUAL OUTCOME
        #
        # This is NEVER sent to the model. It exists only to let the UI
        # validate a historical DB flight after prediction.
        # --------------------------------------------------------------------
        actual_arrival_delay = flight.get(
            "arrival_delay_minutes"
        )

        actual_outcome = None

        if actual_arrival_delay is not None:
            actual_value = numeric(
                actual_arrival_delay
            )

            if actual_value <= 0:
                actual_status = "ON_TIME"
            elif actual_value < 15:
                actual_status = "MINOR_DELAY"
            else:
                actual_status = "DELAYED"

            actual_outcome = {
                "arrival_delay_minutes": actual_value,
                "delayed_15": bool(
                    flight.get(
                        "delayed_15",
                        actual_value >= 15,
                    )
                ),
                "status": actual_status,
                "database_delay_status": flight.get(
                    "delay_status"
                ),
                "database_delay_category": flight.get(
                    "delay_category"
                ),
            }

        # --------------------------------------------------------------------
        # 8. RESPONSE
        # --------------------------------------------------------------------
        response = {
            "success": True,

            "lookup": {
                "input": payload.flight_key,
                "resolved_by": flight["_lookup_resolution"],
                "resolved_value": flight["_lookup_key"],
            },

            "flight": display_flight,

            # Backward-compatible regression feature object.
            "model_features": lgb_features,

            "derived_features": derived,

            # Explicitly separate model contracts in the API.
            "classification_features": xgb_features,
            "regression_features": lgb_features,

            "classification": classification,

            "regression": regression,

            "prediction": {
                "predicted_arrival_delay_minutes":
                    regression["predicted_arrival_delay_minutes"],
                "delay_probability":
                    classification["delay_probability"],
                "delay_probability_percent":
                    classification["delay_probability_percent"],
                "risk_level": combined_risk,
                "status": (
                    "DELAYED"
                    if (
                        regression["predicted_arrival_delay_minutes"]
                        >= 15
                        or classification["delayed_15"]
                    )
                    else "ON_TIME"
                ),
                "recommended_action": action,
                "prediction_time_ms": elapsed_ms,
            },

            "decision": action,

            "action": {
                "level": action,
                "message": decision_message(action),
                "requires_trigger": (
                    action
                    in {
                        "MANUAL_ACTION",
                        "AUTOMATIC_ACTION",
                    }
                ),
            },

            "combined_risk": combined_risk,

            "reasons": reasons,

            "actual_outcome": actual_outcome,

            "model_contract": {
                "classifier": "XGBoost",
                "classifier_target": (
                    "arrival delay >= 15 minutes"
                ),
                "classifier_feature_count": classification["feature_count"],
                "classifier_features": classification["features"],

                "regressor": "LightGBM",
                "regressor_target": (
                    "arrival delay minutes"
                ),
                "regressor_feature_count": len(
                    EXPECTED_LGB_FEATURES
                ),
                "regressor_features": EXPECTED_LGB_FEATURES,

                "feature_count": classification["feature_count"],
                "features": classification["features"],

                "weather_used": False,
                "traffic_congestion_feature_used": any(
                    "congestion" in feature
                    or "flights_1h" in feature
                    or "flights_3h" in feature
                    for feature in classification["features"]
                ),
            },

            "meta": {
                "processing_time_ms": elapsed_ms,
                "historical_validation_only": (
                    actual_outcome is not None
                ),
            },
        }

        print()
        print("[SUCCESS] FINAL PREDICTION")
        print(
            f"Delay: "
            f"{regression['predicted_arrival_delay_minutes']:.6f} min"
        )
        print(
            f"Probability: "
            f"{classification['delay_probability_percent']:.4f}%"
        )
        print(
            f"Risk: {combined_risk}"
        )
        print(
            f"Action: {action}"
        )
        print(
            f"Processing time: {elapsed_ms:.2f} ms"
        )
        print("=" * 70)

        return response

    except HTTPException:
        raise

    except Exception as exc:
        print()
        print("[ERROR] Prediction failed")
        print(repr(exc))

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


# ============================================================================
# HEALTH
# ============================================================================

@app.get("/health")
def health():
    db_ok = False

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": (
            "ok"
            if (
                db_ok
                and xgb_model is not None
                and lgb_model is not None
            )
            else "degraded"
        ),
        "database": db_ok,
        "xgboost_loaded": xgb_model is not None,
        "lightgbm_loaded": lgb_model is not None,
        "lightgbm_features": len(lgb_features),
    }


@app.get("/")
def root():
    return {
        "service": "FLITZZ Flight Delay Prediction API",
        "version": "2.0.0",
        "database_lookup": True,
        "models": {
            "classification": "XGBoost",
            "regression": "LightGBM Champion",
        },
        "endpoint": "/predict",
    }

# ============================================================================

# ============================================================================
# API ROUTERS
# ============================================================================
#
# The ML prediction pipeline above is intentionally unchanged.
# These routers add the operational APIs around it:
#
#   GET  /api/flights/{flight_id}
#   GET  /api/rebooking/{flight_id}
#   GET  /api/rebooking/{flight_id}/passengers
#   GET  /api/rebooking/{flight_id}/alternatives
#   POST /api/rebooking/{flight_id}/rebook
#   POST /api/rebooking/recommendation/{recommendation_id}/accept
#   POST /api/notifications/{flight_id}/send
#
# They use the existing files under backend/api and backend/services.
# ============================================================================

from api import (
    flights_router,
    rebooking_router,
    notification_router,
    crew_router,
)


app.include_router(flights_router)
app.include_router(rebooking_router)
app.include_router(notification_router)
app.include_router(crew_router)