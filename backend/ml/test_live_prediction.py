"""
FLITZZ - TEST LIVE PREDICTION

Enter flight details below.
The script loads:

1. XGBoost classification PKL
2. Single-best LightGBM regression PKL

Then prints the complete prediction.

NO FASTAPI REQUIRED.
NO FRONTEND REQUIRED.
NO WEATHER.
"""

from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from datetime import datetime


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MODEL_DIR = BASE_DIR / "models"

XGB_MODEL_PATH = MODEL_DIR / "xgboost_classifier.pkl"
XGB_SCHEMA_PATH = MODEL_DIR / "feature_schema.pkl"

LGB_MODEL_PATH = MODEL_DIR / "flight_delay_champion.pkl"


# ============================================================
# ENTER FLIGHT DETAILS HERE
# ============================================================

FLIGHT_DATE = "2026-11-24"
DEPARTURE_TIME = "17:30"

AIRLINE = "AA"

ORIGIN_AIRPORT = "ORD"
DESTINATION_AIRPORT = "LGA"

DEPARTURE_DELAY = 25.0
TAXI_OUT = 17.0

DISTANCE = 750.0
SCHEDULED_TIME = 135.0


# ============================================================
# LOAD MODELS
# ============================================================

print()
print("=" * 70)
print("FLITZZ - LIVE FLIGHT PREDICTION TEST")
print("=" * 70)

print("\n[1] Loading models...")

if not XGB_MODEL_PATH.exists():
    raise FileNotFoundError(
        f"XGBoost model not found:\n{XGB_MODEL_PATH}"
    )

if not XGB_SCHEMA_PATH.exists():
    raise FileNotFoundError(
        f"XGBoost schema not found:\n{XGB_SCHEMA_PATH}"
    )

if not LGB_MODEL_PATH.exists():
    raise FileNotFoundError(
        f"LightGBM model not found:\n{LGB_MODEL_PATH}"
    )


xgb_model = joblib.load(
    XGB_MODEL_PATH
)

xgb_schema = joblib.load(
    XGB_SCHEMA_PATH
)

lgb_artifact = joblib.load(
    LGB_MODEL_PATH
)


print("[OK] XGBoost model loaded")
print("[OK] XGBoost schema loaded")
print("[OK] LightGBM champion loaded")


# ============================================================
# LIGHTGBM ARTIFACT
# ============================================================

lgb_model = lgb_artifact["model"]

best_fold = lgb_artifact[
    "best_fold_number"
]

best_mae = lgb_artifact[
    "best_fold_mae"
]

global_mean = lgb_artifact[
    "global_mean"
]

lookup_priors = lgb_artifact[
    "lookup_priors"
]

lgb_features = lgb_artifact[
    "final_features"
]

cat_targets = lgb_artifact[
    "cat_targets"
]


print()
print("LIGHTGBM CHAMPION")
print("-" * 70)

print(
    f"Best Fold       : {best_fold}"
)

print(
    f"Validation MAE  : {best_mae:.4f} minutes"
)

print(
    f"Feature Count   : {len(lgb_features)}"
)


# ============================================================
# CREATE DATE FEATURES
# ============================================================

parsed_date = datetime.strptime(
    FLIGHT_DATE,
    "%Y-%m-%d"
)

month = parsed_date.month
day = parsed_date.day

day_of_week = (
    parsed_date.isoweekday()
)


# ============================================================
# CREATE TIME FEATURES
# ============================================================

parsed_time = datetime.strptime(
    DEPARTURE_TIME,
    "%H:%M"
)

hour = parsed_time.hour
minute = parsed_time.minute

dep_min_of_day = (
    hour * 60 + minute
)

scheduled_departure = (
    hour * 100 + minute
)


# ============================================================
# NORMALIZE FLIGHT DATA
# ============================================================

airline = AIRLINE.strip().upper()

origin = (
    ORIGIN_AIRPORT
    .strip()
    .upper()
)

destination = (
    DESTINATION_AIRPORT
    .strip()
    .upper()
)

route = (
    f"{origin}_{destination}"
)


# ============================================================
# SCHEDULED SPEED
# ============================================================

if SCHEDULED_TIME <= 0:

    raise ValueError(
        "SCHEDULED_TIME must be greater than 0"
    )

scheduled_speed = (
    DISTANCE / SCHEDULED_TIME
)


# ============================================================
# CREATE COMMON FEATURE DICTIONARY
# ============================================================

features = {

    # --------------------------------------------------------
    # TIME
    # --------------------------------------------------------

    "year":
        parsed_date.year,

    "month":
        month,

    "day":
        day,

    "day_of_week":
        day_of_week,

    "scheduled_departure":
        scheduled_departure,

    "departure_hour":
        hour,

    "departure_minute":
        minute,

    "departure_minute_of_day":
        dep_min_of_day,

    # --------------------------------------------------------
    # FLIGHT
    # --------------------------------------------------------

    "airline":
        airline,

    "origin_airport":
        origin,

    "destination_airport":
        destination,

    "route":
        route,

    "distance":
        DISTANCE,

    "distance_miles":
        DISTANCE,

    "scheduled_time":
        SCHEDULED_TIME,

    "scheduled_speed":
        scheduled_speed,

    # --------------------------------------------------------
    # OPERATIONAL
    # --------------------------------------------------------

    "departure_delay":
        DEPARTURE_DELAY,

    "taxi_out":
        TAXI_OUT,
}


# ============================================================
# XGBOOST FEATURE PREPARATION
# ============================================================

print()
print("=" * 70)
print("XGBOOST CLASSIFICATION")
print("=" * 70)


# Support both schema formats

if (
    isinstance(
        xgb_schema,
        dict
    )
    and "xgboost" in xgb_schema
):

    xgb_config = xgb_schema[
        "xgboost"
    ]

    xgb_features = list(
        xgb_config[
            "feature_columns"
        ]
    )

    xgb_categorical = list(
        xgb_config.get(
            "categorical_features",
            []
        )
    )

    xgb_encoder = (
        xgb_config.get(
            "encoder"
        )
    )

    xgb_medians = (
        xgb_config.get(
            "numerical_medians",
            {}
        )
    )

else:

    xgb_features = list(
        xgb_schema.get(
            "feature_columns",
            []
        )
    )

    xgb_categorical = list(
        xgb_schema.get(
            "categorical_features",
            []
        )
    )

    xgb_encoder = (
        xgb_schema.get(
            "encoder"
        )
    )

    xgb_medians = (
        xgb_schema.get(
            "numerical_medians",
            {}
        )
    )


print(
    f"[INFO] XGBoost features: "
    f"{len(xgb_features)}"
)


# ============================================================
# CREATE XGBOOST DATAFRAME
# ============================================================

xgb_row = pd.DataFrame(
    [features]
)


# Add missing columns

for column in xgb_features:

    if column not in xgb_row.columns:

        xgb_row[column] = np.nan


# Exact feature order

xgb_row = xgb_row[
    xgb_features
].copy()


# ============================================================
# CATEGORICAL FEATURES
# ============================================================

for column in xgb_categorical:

    xgb_row[column] = (

        xgb_row[column]
        .fillna("UNKNOWN")
        .astype(str)
    )


# ============================================================
# NUMERICAL FEATURES
# ============================================================

numerical_features = [

    column

    for column in xgb_features

    if column
    not in xgb_categorical
]


for column in numerical_features:

    xgb_row[column] = pd.to_numeric(
        xgb_row[column],
        errors="coerce"
    )

    xgb_row[column] = (
        xgb_row[column]
        .replace(
            [
                np.inf,
                -np.inf
            ],
            np.nan
        )
    )

    fallback = xgb_medians.get(
        column,
        0.0
    )

    if (
        fallback is None
        or pd.isna(fallback)
    ):

        fallback = 0.0

    xgb_row[column] = (
        xgb_row[column]
        .fillna(
            float(fallback)
        )
    )


# ============================================================
# ENCODE CATEGORICAL FEATURES
# ============================================================

if xgb_categorical:

    if xgb_encoder is None:

        raise RuntimeError(
            "XGBoost encoder not found"
        )

    xgb_row[
        xgb_categorical
    ] = xgb_encoder.transform(
        xgb_row[
            xgb_categorical
        ]
    )


# ============================================================
# XGBOOST PREDICTION
# ============================================================

X_xgb = xgb_row.astype(
    np.float32
)

delay_probability = float(
    xgb_model
    .predict_proba(
        X_xgb
    )[0][1]
)

delay_probability = min(
    max(
        delay_probability,
        0.0
    ),
    1.0
)


delayed_15 = (
    delay_probability >= 0.50
)


if delay_probability >= 0.70:

    classification_risk = "VERY_HIGH"

elif delay_probability >= 0.50:

    classification_risk = "HIGH"

elif delay_probability >= 0.30:

    classification_risk = "MEDIUM"

else:

    classification_risk = "LOW"


print()
print(
    f"Delay Probability : "
    f"{delay_probability * 100:.2f}%"
)

print(
    f"Delayed >= 15 min : "
    f"{delayed_15}"
)

print(
    f"Classification    : "
    f"{'DELAYED' if delayed_15 else 'NOT DELAYED'}"
)

print(
    f"Probability Risk  : "
    f"{classification_risk}"
)


# ============================================================
# LIGHTGBM REGRESSION
# ============================================================

print()
print("=" * 70)
print("LIGHTGBM REGRESSION")
print("=" * 70)


lgb_row = pd.DataFrame(
    [features]
)


# ============================================================
# HISTORICAL PRIORS
# ============================================================

for column in cat_targets:

    prior_map = lookup_priors.get(
        column,
        {}
    )

    value = str(
        lgb_row[
            column
        ].iloc[0]
    )

    historical_delay = (
        prior_map.get(
            value,
            global_mean
        )
    )

    lgb_row[
        f"{column}_HIST_DELAY"
    ] = float(
        historical_delay
    )


# ============================================================
# ADD MISSING FEATURES
# ============================================================

for column in lgb_features:

    if column not in lgb_row.columns:

        lgb_row[column] = np.nan


# Exact model feature order

lgb_row = lgb_row[
    lgb_features
].copy()


# ============================================================
# NUMERICAL
# ============================================================

lgb_numerical = [

    column

    for column in lgb_features

    if column
    not in cat_targets
]


for column in lgb_numerical:

    lgb_row[column] = pd.to_numeric(
        lgb_row[column],
        errors="coerce"
    )

    lgb_row[column] = (
        lgb_row[column]
        .replace(
            [
                np.inf,
                -np.inf
            ],
            np.nan
        )
        .fillna(0.0)
    )


# ============================================================
# CATEGORICAL
# ============================================================

for column in cat_targets:

    lgb_row[column] = (
        lgb_row[column]
        .fillna("UNKNOWN")
        .astype("category")
    )


# ============================================================
# LIGHTGBM PREDICTION
# ============================================================

predicted_delay = float(
    lgb_model.predict(
        lgb_row
    )[0]
)

predicted_delay = max(
    0.0,
    predicted_delay
)


# ============================================================
# REGRESSION STATUS
# ============================================================

if predicted_delay >= 45:

    regression_risk = "CRITICAL"

elif predicted_delay >= 30:

    regression_risk = "HIGH"

elif predicted_delay >= 15:

    regression_risk = "MODERATE"

else:

    regression_risk = "LOW"


if predicted_delay >= 30:

    action = "AUTOMATIC_ACTION"

elif predicted_delay >= 15:

    action = "MANUAL_ACTION"

else:

    action = "NORMAL_WAIT"


print()
print(
    f"Predicted Delay   : "
    f"{predicted_delay:.2f} minutes"
)

print(
    f"Delay Status      : "
    f"{'DELAYED' if predicted_delay >= 15 else 'ON-TIME'}"
)

print(
    f"Regression Risk   : "
    f"{regression_risk}"
)

print(
    f"Recommended Action: "
    f"{action}"
)


# ============================================================
# COMBINED RISK
# ============================================================

if (
    predicted_delay >= 45
    or delay_probability >= 0.70
):

    combined_risk = "CRITICAL"

elif (
    predicted_delay >= 30
    or delay_probability >= 0.50
):

    combined_risk = "HIGH"

elif (
    predicted_delay >= 15
    or delay_probability >= 0.30
):

    combined_risk = "MEDIUM"

else:

    combined_risk = "LOW"


# ============================================================
# FINAL RESULT
# ============================================================

print()
print("=" * 70)
print("FINAL FLIGHT PREDICTION")
print("=" * 70)

print()
print("FLIGHT DETAILS")
print("-" * 70)

print(
    f"Date              : {FLIGHT_DATE}"
)

print(
    f"Departure         : {DEPARTURE_TIME}"
)

print(
    f"Airline           : {airline}"
)

print(
    f"Route             : "
    f"{origin} -> {destination}"
)

print(
    f"Departure Delay   : "
    f"{DEPARTURE_DELAY:.2f} min"
)

print(
    f"Taxi Out          : "
    f"{TAXI_OUT:.2f} min"
)

print(
    f"Distance          : "
    f"{DISTANCE:.2f} miles"
)

print(
    f"Scheduled Time    : "
    f"{SCHEDULED_TIME:.2f} min"
)


print()
print("CLASSIFICATION")
print("-" * 70)

print(
    f"Delay Probability : "
    f"{delay_probability * 100:.2f}%"
)

print(
    f"Delayed >= 15 min : "
    f"{'YES' if delayed_15 else 'NO'}"
)

print(
    f"Risk              : "
    f"{classification_risk}"
)


print()
print("REGRESSION")
print("-" * 70)

print(
    f"Predicted Delay   : "
    f"{predicted_delay:.2f} min"
)

print(
    f"Risk              : "
    f"{regression_risk}"
)

print(
    f"Action            : "
    f"{action}"
)


print()
print("COMBINED")
print("-" * 70)

print(
    f"Final Risk        : "
    f"{combined_risk}"
)

print(
    f"Weather Used      : NO"
)

print(
    f"Regression Model  : "
    f"LightGBM Fold {best_fold}"
)

print(
    f"Champion MAE      : "
    f"{best_mae:.4f} min"
)

print()
print("=" * 70)
print("PREDICTION COMPLETE")
print("=" * 70)