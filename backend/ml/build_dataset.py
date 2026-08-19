"""
FLITZZ - BUILD ML FEATURE DATASET

Purpose
-------
Build a SMALL validation / development feature dataset
from PostgreSQL.

This file is NOT the full-data training loop.

For large training:

    chunk_train.py
        |
        +--> reads PostgreSQL sequentially
        +--> builds one feature chunk at a time
        +--> trains the models
        +--> releases memory


CURRENT FEATURE DESIGN
----------------------

MASTER FEATURE SET
    The feature builder produces the union required by both models.

XGBoost classification uses the existing 24-feature schema:
    9 flight/schedule
    8 historical
    7 traffic/congestion

LightGBM regression uses 34 features:
    all 24 XGBoost features
    + 10 additional schedule/historical/operational features

Weather is not used by either model.

Targets
-------
Classification:
    delayed_15 = arrival_delay_minutes >= 15

Regression:
    arrival_delay_minutes
"""


# ============================================================================
# IMPORTS
# ============================================================================

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd


# ============================================================================
# PATH
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


# ============================================================================
# FEATURE BUILDER IMPORT
# ============================================================================

from features import (
    build_features,
    MODEL_FEATURES,
    XGB_FEATURES,
    LGBM_FEATURES,
    TARGET_CLASSIFICATION,
    TARGET_REGRESSION,
    CATEGORICAL_FEATURES,
)


# ============================================================================
# CONFIGURATION
# ============================================================================

DATASET_DIR = BASE_DIR / "datasets"

DATASET_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


OUTPUT_FILE = (
    DATASET_DIR /
    "feature_dataset.parquet"
)


# ============================================================================
# DEVELOPMENT SETTINGS
# ============================================================================

# Keep this SMALL while testing.

# Recommended:
#
#     10_000
#
# After validation:
#
# DO NOT increase this to millions.
#
# Use chunk_train.py for full-data training.

BUILD_LIMIT = 10_000


# ============================================================================
# MODEL FEATURE CONTRACTS
# ============================================================================

EXPECTED_XGB_FEATURE_COUNT = 24
EXPECTED_LGBM_FEATURE_COUNT = 34
EXPECTED_MASTER_FEATURE_COUNT = len(MODEL_FEATURES)


# ============================================================================
# FEATURE GROUPS
# ============================================================================

XGB_FLIGHT_FEATURES = [
    "airline",
    "origin_airport",
    "destination_airport",
    "departure_hour",
    "departure_period",
    "day_of_week",
    "month",
    "season",
    "distance_miles",
]

XGB_HISTORICAL_FEATURES = [
    "route_average_delay_minutes",
    "route_delay_rate",
    "route_previous_flights",
    "route_previous_delays",
    "airline_average_delay_minutes",
    "airline_delay_rate",
    "airline_previous_flights",
    "airline_previous_delays",
]

XGB_TRAFFIC_FEATURES = [
    "route_flights_1h",
    "route_flights_3h",
    "origin_flights_1h",
    "destination_flights_1h",
    "route_congestion_ratio",
    "origin_congestion_ratio",
    "destination_congestion_ratio",
]

LGBM_ADDITIONAL_FEATURES = [
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


# ============================================================================
# VALIDATION
# ============================================================================

def validate_dataset(
    df: pd.DataFrame,
) -> None:
    """Validate the master dataset and both model feature contracts."""

    print()
    print("=" * 70)
    print("DATASET VALIDATION")
    print("=" * 70)

    required_columns = [
        "flight_id",
        "flight_datetime",
        *MODEL_FEATURES,
        TARGET_CLASSIFICATION,
        TARGET_REGRESSION,
    ]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise RuntimeError(
            "Missing required columns:\n"
            + "\n".join(f"  - {column}" for column in missing_columns)
        )

    print(f"[OK] Master ML features: {len(MODEL_FEATURES)}")
    print(f"[OK] XGBoost features: {len(XGB_FEATURES)}")
    print(f"[OK] LightGBM features: {len(LGBM_FEATURES)}")

    if len(XGB_FEATURES) != EXPECTED_XGB_FEATURE_COUNT:
        raise RuntimeError(
            f"Expected exactly {EXPECTED_XGB_FEATURE_COUNT} XGBoost features, "
            f"but got {len(XGB_FEATURES)}."
        )

    if len(LGBM_FEATURES) != EXPECTED_LGBM_FEATURE_COUNT:
        raise RuntimeError(
            f"Expected exactly {EXPECTED_LGBM_FEATURE_COUNT} LightGBM features, "
            f"but got {len(LGBM_FEATURES)}."
        )

    if len(set(XGB_FEATURES)) != len(XGB_FEATURES):
        raise RuntimeError("Duplicate features detected in XGB_FEATURES.")

    if len(set(LGBM_FEATURES)) != len(LGBM_FEATURES):
        raise RuntimeError("Duplicate features detected in LGBM_FEATURES.")

    if not set(XGB_FEATURES).issubset(set(MODEL_FEATURES)):
        raise RuntimeError("XGB_FEATURES contains columns missing from master features.")

    if not set(LGBM_FEATURES).issubset(set(MODEL_FEATURES)):
        raise RuntimeError("LGBM_FEATURES contains columns missing from master features.")

    expected_xgb = (
        XGB_FLIGHT_FEATURES
        + XGB_HISTORICAL_FEATURES
        + XGB_TRAFFIC_FEATURES
    )

    if XGB_FEATURES != expected_xgb:
        raise RuntimeError(
            "XGB feature groups do not exactly match XGB_FEATURES."
        )

    expected_lgbm = XGB_FEATURES + LGBM_ADDITIONAL_FEATURES

    if LGBM_FEATURES != expected_lgbm:
        raise RuntimeError(
            "LGBM_FEATURES must equal the 24 XGB features plus "
            "the 10 additional regression features."
        )

    print("[OK] XGBoost feature contract: 24 features.")
    print("[OK] LightGBM feature contract: 34 features.")
    print("[OK] Master feature contract contains all model features.")

    forbidden = [
        "temperature", "humidity", "wind_speed", "wind_direction",
        "precipitation", "visibility", "weather_condition", "weather_delay",
        "rain", "snow", "pressure", "cloud",
    ]

    selected_forbidden = [
        c for c in MODEL_FEATURES
        if any(term in c.lower() for term in forbidden)
    ]

    if selected_forbidden:
        raise RuntimeError(
            "Weather feature detected: " + ", ".join(selected_forbidden)
        )

    print("[OK] Weather features: REMOVED.")

    if df.empty:
        raise RuntimeError("Feature dataset contains zero rows.")

    print(f"[OK] Rows: {len(df):,}")

    duplicate_ids = df["flight_id"].duplicated().sum()
    if duplicate_ids:
        raise RuntimeError(
            f"Found {duplicate_ids:,} duplicate flight_id values."
        )

    print("[OK] No duplicate flight IDs.")

    datetime_values = pd.to_datetime(
        df["flight_datetime"],
        errors="coerce",
        utc=True,
    )

    invalid_datetime = datetime_values.isna().sum()
    if invalid_datetime:
        raise RuntimeError(
            f"Found {invalid_datetime:,} invalid flight_datetime values."
        )

    print("[OK] flight_datetime valid.")

    classification_values = sorted(
        pd.to_numeric(
            df[TARGET_CLASSIFICATION],
            errors="coerce",
        ).dropna().unique().tolist()
    )

    if not set(classification_values).issubset({0, 1}):
        raise RuntimeError(
            "Classification target must contain only 0 and 1."
        )

    classification_missing = df[TARGET_CLASSIFICATION].isna().sum()
    if classification_missing:
        raise RuntimeError(
            f"Classification target contains {classification_missing:,} missing rows."
        )

    positive_rate = (
        pd.to_numeric(df[TARGET_CLASSIFICATION], errors="coerce").mean() * 100
    )

    print(f"[OK] Classification target values: {classification_values}")
    print(f"[INFO] Delayed >=15 minutes: {positive_rate:.2f}%")

    regression_values = pd.to_numeric(
        df[TARGET_REGRESSION],
        errors="coerce",
    )

    regression_missing = regression_values.isna().sum()
    if regression_missing:
        raise RuntimeError(
            f"Regression target contains {regression_missing:,} missing rows."
        )

    print("[OK] Regression target valid.")
    print(f"[INFO] Average actual delay: {regression_values.mean():.2f} minutes")
    print(f"[INFO] Maximum actual delay: {regression_values.max():.2f} minutes")

    numeric_features = (
        df[MODEL_FEATURES]
        .select_dtypes(include="number")
    )

    infinite_count = np.isinf(numeric_features.to_numpy()).sum()

    if infinite_count:
        raise RuntimeError(
            f"Found {infinite_count:,} infinite feature values."
        )

    print("[OK] No infinite numeric feature values.")

    missing_features = df[MODEL_FEATURES].isna().sum()
    missing_features = missing_features[missing_features > 0]

    if missing_features.empty:
        print("[OK] No missing feature values.")
    else:
        print("[WARNING] Missing feature values:")
        for column, count in missing_features.items():
            percentage = count / len(df) * 100
            print(f"  {column:<40} {count:>8,} ({percentage:>6.2f}%)")

    print()
    print("[INFO] XGBoost categorical features:")
    for column in CATEGORICAL_FEATURES:
        if column in XGB_FEATURES:
            print(
                f"  {column:<35} "
                f"{df[column].nunique(dropna=False):,} unique"
            )

    print()
    print("[INFO] Dataset date range:")
    print(f"  {datetime_values.min()} -> {datetime_values.max()}")

    print()
    print("[OK] Dataset validation passed.")


# ============================================================================
# SAVE DATASET
# ============================================================================

def save_dataset(
    df: pd.DataFrame,
) -> None:

    """
    Save the validated development dataset.
    """

    print()
    print("=" * 70)
    print("SAVING DATASET")
    print("=" * 70)


    df.to_parquet(

        OUTPUT_FILE,

        index=False,

        engine="pyarrow",

    )


    size_mb = (

        OUTPUT_FILE.stat().st_size

        /

        (1024 * 1024)

    )


    print(
        "[OK] Dataset saved:"
    )


    print(
        f"     {OUTPUT_FILE}"
    )


    print(

        f"     Size: "
        f"{size_mb:.2f} MB"

    )


# ============================================================================
# FEATURE SUMMARY
# ============================================================================

def print_feature_summary(
    df: pd.DataFrame,
) -> None:

    print()
    print("=" * 70)
    print("FEATURE SUMMARY")
    print("=" * 70)

    print(f"\\nTotal rows          : {len(df):,}")
    print(f"Master features     : {len(MODEL_FEATURES)}")
    print(f"XGBoost features    : {len(XGB_FEATURES)}")
    print(f"LightGBM features   : {len(LGBM_FEATURES)}")
    print(f"Categorical master  : {len(CATEGORICAL_FEATURES)}")

    print()
    print("MODEL FEATURE CONTRACTS")
    print("-" * 70)

    print("XGBoost CLASSIFICATION")
    print("  24 features")
    for feature in XGB_FEATURES:
        print(f"    - {feature}")

    print()
    print("LightGBM REGRESSION")
    print("  34 features = 24 XGBoost + 10 additional")
    for feature in LGBM_FEATURES:
        print(f"    - {feature}")

    print()
    print("TARGETS")
    print("-" * 70)
    print(f"Classification: {TARGET_CLASSIFICATION}")
    print(f"Regression   : {TARGET_REGRESSION}")

    print()
    print("EXCLUDED FROM BOTH MODELS")
    print("-" * 70)
    print("Weather      : REMOVED")
    print("Weather API  : NOT USED")
    print("")


# ============================================================================
# PREVIEW
# ============================================================================

def print_preview(
    df: pd.DataFrame,
) -> None:

    print()
    print("=" * 70)
    print("FEATURE PREVIEW")
    print("=" * 70)


    preview_columns = [

        "flight_id",

        "flight_datetime",

        *MODEL_FEATURES,

        TARGET_CLASSIFICATION,

        TARGET_REGRESSION,

    ]


    print(

        df[
            preview_columns
        ]

        .head(5)

        .to_string(
            index=False
        )

    )


# ============================================================================
# MAIN
# ============================================================================

def main():

    print()
    print("=" * 70)
    print("FLITZZ - BUILD ML DATASET")
    print("=" * 70)


    print()

    print(
        "[INFO] PostgreSQL = PRIMARY DATA SOURCE"
    )


    print(

        f"[INFO] Build limit = "
        f"{BUILD_LIMIT:,}"

    )


    print()

    print(
        "[INFO] Feature design = FRIEND MODEL FEATURES"
    )


    print(
        "[INFO] ML features = "
        f"{len(MODEL_FEATURES)}"
    )


    print(
        "[INFO] Weather = DISABLED"
    )


    print(
        "[INFO] Traffic congestion = DISABLED"
    )


    print()

    print(
        "[INFO] This script builds a small "
        "validation dataset."
    )


    print(

        "[INFO] Full-data training should use "
        "iter_feature_chunks() from features.py."

    )


    # ========================================================================
    # BUILD
    # ========================================================================

    print()
    print("=" * 70)
    print("BUILDING FEATURES")
    print("=" * 70)


    df = build_features(

        limit=BUILD_LIMIT,

    )


    if df.empty:

        raise RuntimeError(

            "Feature builder returned zero rows."

        )


    print()

    print(

        f"[OK] Feature builder returned "
        f"{len(df):,} rows."

    )


    # ========================================================================
    # VALIDATE
    # ========================================================================

    validate_dataset(
        df
    )


    # ========================================================================
    # SUMMARY
    # ========================================================================

    print_feature_summary(
        df
    )


    # ========================================================================
    # SAVE
    # ========================================================================

    save_dataset(
        df
    )


    # ========================================================================
    # PREVIEW
    # ========================================================================

    print_preview(
        df
    )


    # ========================================================================
    # COMPLETE
    # ========================================================================

    print()

    print("=" * 70)
    print("DATASET BUILD COMPLETE")
    print("=" * 70)


    print()

    print(
        "[OK] Development dataset created successfully."
    )


    print()

    print(
        "NEXT STEP"
    )


    print(
        "-" * 70
    )


    print(
        "Do NOT increase BUILD_LIMIT to millions."
    )


    print(
        "Use chunk_train.py for full PostgreSQL training."
    )


    print(
        "Recommended chunk size: 50,000 rows."
    )


    print()

    print(
        "IMPORTANT:"
    )


    print(
        "The full-data trainer should build "
        "features directly from PostgreSQL "
        "in sequential chunks."
    )


    print(
        "It should NOT create a multi-million-row "
        "Parquet dataset first."
    )


    print()

    print("=" * 70)
    print("FLITZZ READY")
    print("=" * 70)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":

    main()