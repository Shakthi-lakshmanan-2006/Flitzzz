"""
FLITZZ - FINAL CHUNK TRAINING
=============================

Architecture
------------
PostgreSQL -> features.py -> chronological 50,000-row chunks

Chronological split:
    first 80%  -> TRAIN
    final 20%  -> TEST ONLY

Models:
    XGBoost  -> classification: arrival delay >= 15 minutes
    LightGBM -> regression: arrival delay minutes

Feature contracts:
    XGBoost  : 24 existing classification features
    LightGBM : the same 24 + 10 engineered regression features = 34

Weather:
    COMPLETELY REMOVED / FORBIDDEN

No validation split is used.

IMPORTANT:
Do not compare features.py MODEL_FEATURES to a hard-coded 24-feature list.
features.py may expose the complete 34-feature set. This trainer explicitly
selects the 24-feature XGBoost subset and 34-feature LightGBM subset.
"""

from __future__ import annotations

import gc
import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.preprocessing import OrdinalEncoder
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

from xgboost import XGBClassifier
from lightgbm import LGBMRegressor


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

MODEL_DIR = BASE_DIR / "models"
ARTIFACT_DIR = BASE_DIR / "artifacts"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# IMPORT FEATURE BUILDER
# ============================================================

from features import (
    build_features,
    TARGET_CLASSIFICATION,
    TARGET_REGRESSION,
    CATEGORICAL_FEATURES,
)

import features as feature_module


# ============================================================
# FEATURE CONTRACTS
# ============================================================

# EXACT 24-feature contract used by the current XGBoost classifier.
XGB_FEATURES = [
    # Flight
    "airline",
    "origin_airport",
    "destination_airport",
    "departure_hour",
    "departure_period",
    "day_of_week",
    "month",
    "season",
    "distance_miles",

    # Historical
    "route_average_delay_minutes",
    "route_delay_rate",
    "route_previous_flights",
    "route_previous_delays",
    "airline_average_delay_minutes",
    "airline_delay_rate",
    "airline_previous_flights",
    "airline_previous_delays",

    # Traffic
    "route_flights_1h",
    "route_flights_3h",
    "origin_flights_1h",
    "destination_flights_1h",
    "route_congestion_ratio",
    "origin_congestion_ratio",
    "destination_congestion_ratio",
]


# 10 engineered features added for LightGBM regression.
LGB_EXTRA_FEATURES = [
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

LGB_FEATURES = XGB_FEATURES + LGB_EXTRA_FEATURES


# ============================================================
# FEATURE SAFETY
# ============================================================

WEATHER_KEYWORDS = (
    "weather",
    "temperature",
    "humidity",
    "wind",
    "precipitation",
    "rain",
    "snow",
    "visibility",
    "pressure",
    "cloud",
    "dew_point",
    "heat_index",
    "storm",
)


def weather_features(feature_list: list[str]) -> list[str]:
    return [
        f for f in feature_list
        if any(
            keyword in f.lower()
            for keyword in WEATHER_KEYWORDS
        )
    ]


for model_name, feature_list in (
    ("XGBoost", XGB_FEATURES),
    ("LightGBM", LGB_FEATURES),
):
    bad = weather_features(feature_list)

    if bad:
        raise RuntimeError(
            f"{model_name} contains forbidden weather features: {bad}"
        )


# Make sure the feature builder actually produces everything.
features_py_list = list(
    getattr(feature_module, "MODEL_FEATURES", [])
)

required_all = set(LGB_FEATURES)
missing_from_features_py = [
    f for f in LGB_FEATURES
    if f not in features_py_list
]

if missing_from_features_py:
    raise RuntimeError(
        "features.py does not produce all required model features.\n"
        f"Missing:\n{missing_from_features_py}\n\n"
        f"features.py MODEL_FEATURES contains {len(features_py_list)} features."
    )


# ============================================================
# CONFIGURATION
# ============================================================

CHUNK_SIZE = 50_000

# Trees added on each chronological training segment.
TREES_PER_CHUNK = 10

TRAIN_RATIO = 0.80
TEST_RATIO = 0.20

# Fixed BEFORE touching the final test metrics.
CLASSIFICATION_THRESHOLD = 0.50

# None = all valid PostgreSQL rows.
# For a quick smoke test, temporarily use e.g. 500_000.
MAX_TRAINING_ROWS = None

# XGBoost
XGB_LEARNING_RATE = 0.03
XGB_MAX_DEPTH = 6
XGB_SUBSAMPLE = 0.90
XGB_COLSAMPLE = 0.90

# LightGBM
LGB_LEARNING_RATE = 0.03
LGB_NUM_LEAVES = 31
LGB_MAX_DEPTH = -1
LGB_SUBSAMPLE = 0.90
LGB_COLSAMPLE = 0.90


# ============================================================
# BASIC HELPERS
# ============================================================

def optimize_memory(df: pd.DataFrame) -> pd.DataFrame:
    for column in df.columns:
        if pd.api.types.is_float_dtype(df[column]):
            df[column] = pd.to_numeric(
                df[column],
                downcast="float",
            )
        elif pd.api.types.is_integer_dtype(df[column]):
            df[column] = pd.to_numeric(
                df[column],
                downcast="integer",
            )
    return df


def decision_from_minutes(minutes: float) -> str:
    if minutes < 15:
        return "NORMAL_WAIT"
    if minutes < 30:
        return "MANUAL_ACTION"
    return "AUTOMATIC_ACTION"


def prepare_target_chunk(
    df: pd.DataFrame,
) -> pd.DataFrame:

    result = df.copy()

    required = (
        set(LGB_FEATURES)
        | {
            TARGET_CLASSIFICATION,
            TARGET_REGRESSION,
        }
    )

    missing = [
        c for c in required
        if c not in result.columns
    ]

    if missing:
        raise RuntimeError(
            "Feature builder is missing required columns:\n"
            + "\n".join(
                f"  - {c}"
                for c in missing
            )
        )

    result[TARGET_CLASSIFICATION] = pd.to_numeric(
        result[TARGET_CLASSIFICATION],
        errors="coerce",
    )

    result[TARGET_REGRESSION] = pd.to_numeric(
        result[TARGET_REGRESSION],
        errors="coerce",
    )

    result = result[
        result[TARGET_CLASSIFICATION].isin([0, 1])
        & result[TARGET_REGRESSION].notna()
    ].copy()

    result[TARGET_CLASSIFICATION] = (
        result[TARGET_CLASSIFICATION]
        .astype(int)
    )

    result[TARGET_REGRESSION] = (
        result[TARGET_REGRESSION]
        .clip(lower=0)
        .astype(float)
    )

    return result.reset_index(drop=True)


# ============================================================
# POSTGRESQL FEATURE CHUNKS
# ============================================================

def get_feature_chunks():
    """
    Preferred:
        features.iter_feature_chunks()

    Fallback:
        features.build_features(limit=..., offset=...)

    No weather parameter is passed anywhere.
    """

    iterator = getattr(
        feature_module,
        "iter_feature_chunks",
        None,
    )

    if iterator is not None:

        print(
            "[INFO] Using features.iter_feature_chunks()."
        )

        try:
            yield from iterator(
                chunk_size=CHUNK_SIZE,
                max_rows=MAX_TRAINING_ROWS,
            )
            return

        except TypeError:

            try:
                yield from iterator(
                    chunk_size=CHUNK_SIZE,
                )
                return

            except TypeError:
                print(
                    "[WARNING] Falling back to build_features()."
                )

    print(
        "[INFO] Using build_features(limit, offset)."
    )

    offset = 0
    total = 0

    while True:

        if (
            MAX_TRAINING_ROWS is not None
            and total >= MAX_TRAINING_ROWS
        ):
            break

        limit = CHUNK_SIZE

        if MAX_TRAINING_ROWS is not None:
            limit = min(
                limit,
                MAX_TRAINING_ROWS - total,
            )

        if limit <= 0:
            break

        df = build_features(
            limit=limit,
            offset=offset,
        )

        if df is None or df.empty:
            break

        yield df

        rows = len(df)

        total += rows
        offset += rows

        if rows < limit:
            break

        del df
        gc.collect()


# ============================================================
# PREPROCESSING
# ============================================================

def categorical_for(
    feature_columns: list[str],
) -> list[str]:

    return [
        c
        for c in CATEGORICAL_FEATURES
        if c in feature_columns
    ]


def fit_encoder(
    df: pd.DataFrame,
    categorical_features: list[str],
):
    if not categorical_features:
        return None

    encoder = OrdinalEncoder(
        handle_unknown="use_encoded_value",
        unknown_value=-1,
    )

    values = (
        df[categorical_features]
        .fillna("UNKNOWN")
        .astype(str)
    )

    encoder.fit(values)

    return encoder


def calculate_medians(
    df: pd.DataFrame,
    feature_columns: list[str],
    categorical_features: list[str],
) -> dict:

    medians = {}

    for column in feature_columns:

        if column in categorical_features:
            continue

        values = pd.to_numeric(
            df[column],
            errors="coerce",
        )

        values = values.replace(
            [np.inf, -np.inf],
            np.nan,
        )

        median = values.median()

        if pd.isna(median):
            median = 0.0

        medians[column] = float(median)

    return medians


def transform_features(
    df: pd.DataFrame,
    feature_columns: list[str],
    categorical_features: list[str],
    encoder,
    medians: dict,
) -> pd.DataFrame:

    X = df[
        feature_columns
    ].copy()

    # Categorical
    if categorical_features:

        values = (
            X[categorical_features]
            .fillna("UNKNOWN")
            .astype(str)
        )

        if encoder is None:
            raise RuntimeError(
                "Categorical encoder is not initialized."
            )

        X[categorical_features] = (
            encoder.transform(values)
        )

    # Numerical
    for column in feature_columns:

        if column in categorical_features:
            continue

        X[column] = pd.to_numeric(
            X[column],
            errors="coerce",
        )

        X[column] = (
            X[column]
            .replace(
                [np.inf, -np.inf],
                np.nan,
            )
            .fillna(
                medians.get(
                    column,
                    0.0,
                )
            )
        )

    return optimize_memory(X)


# ============================================================
# MODEL FACTORIES
# ============================================================

def create_xgb_model(
    scale_pos_weight: float,
) -> XGBClassifier:

    return XGBClassifier(
        n_estimators=TREES_PER_CHUNK,
        learning_rate=XGB_LEARNING_RATE,
        max_depth=XGB_MAX_DEPTH,
        subsample=XGB_SUBSAMPLE,
        colsample_bytree=XGB_COLSAMPLE,
        objective="binary:logistic",
        eval_metric="logloss",
        tree_method="hist",
        scale_pos_weight=scale_pos_weight,
        n_jobs=-1,
        random_state=42,
        verbosity=0,
    )


def create_lgb_model() -> LGBMRegressor:

    return LGBMRegressor(
        n_estimators=TREES_PER_CHUNK,
        learning_rate=LGB_LEARNING_RATE,
        num_leaves=LGB_NUM_LEAVES,
        max_depth=LGB_MAX_DEPTH,
        objective="regression",
        subsample=LGB_SUBSAMPLE,
        colsample_bytree=LGB_COLSAMPLE,
        n_jobs=-1,
        random_state=42,
        verbosity=-1,
    )


# ============================================================
# METRICS
# ============================================================

def classification_metrics(
    y_true,
    probabilities,
) -> dict:

    predictions = (
        probabilities
        >= CLASSIFICATION_THRESHOLD
    ).astype(int)

    try:
        auc = roc_auc_score(
            y_true,
            probabilities,
        )
    except ValueError:
        auc = 0.0

    matrix = confusion_matrix(
        y_true,
        predictions,
    )

    return {
        "accuracy": float(
            accuracy_score(
                y_true,
                predictions,
            )
        ),
        "precision": float(
            precision_score(
                y_true,
                predictions,
                zero_division=0,
            )
        ),
        "recall": float(
            recall_score(
                y_true,
                predictions,
                zero_division=0,
            )
        ),
        "f1_score": float(
            f1_score(
                y_true,
                predictions,
                zero_division=0,
            )
        ),
        "roc_auc": float(auc),
        "threshold": float(
            CLASSIFICATION_THRESHOLD
        ),
        "confusion_matrix": matrix.tolist(),
        "classification_report":
            classification_report(
                y_true,
                predictions,
                output_dict=True,
                zero_division=0,
            ),
    }


def regression_metrics(
    y_true,
    predictions,
) -> dict:

    predictions = np.maximum(
        predictions,
        0,
    )

    return {
        "mae_minutes": float(
            mean_absolute_error(
                y_true,
                predictions,
            )
        ),
        "rmse_minutes": float(
            np.sqrt(
                mean_squared_error(
                    y_true,
                    predictions,
                )
            )
        ),
        "r2": float(
            r2_score(
                y_true,
                predictions,
            )
        ),
    }


# ============================================================
# FEATURE IMPORTANCE
# ============================================================

def save_feature_importance(
    xgb_model,
    lgb_model,
):

    xgb_df = pd.DataFrame(
        {
            "feature": XGB_FEATURES,
            "xgboost_importance":
                xgb_model.feature_importances_,
        }
    )

    lgb_df = pd.DataFrame(
        {
            "feature": LGB_FEATURES,
            "lightgbm_importance":
                lgb_model.feature_importances_,
        }
    )

    result = pd.merge(
        xgb_df,
        lgb_df,
        on="feature",
        how="outer",
    ).fillna(0)

    result = result.sort_values(
        "xgboost_importance",
        ascending=False,
    )

    output = (
        ARTIFACT_DIR
        / "feature_importance.csv"
    )

    result.to_csv(
        output,
        index=False,
    )

    print()
    print(
        f"[OK] Feature importance saved: {output}"
    )

    print()
    print("TOP FEATURES")
    print("-" * 70)
    print(
        result.head(20).to_string(
            index=False
        )
    )

    return result


# ============================================================
# SAVE MODELS / SCHEMAS
# ============================================================

def save_models(
    xgb_model,
    lgb_model,
    xgb_encoder,
    lgb_encoder,
    xgb_medians,
    lgb_medians,
    metrics,
    train_rows,
    test_rows,
    train_segments,
    test_segments,
):

    xgb_path = (
        MODEL_DIR
        / "xgboost_classifier.pkl"
    )

    lgb_path = (
        MODEL_DIR
        / "lightgbm_regressor.pkl"
    )

    schema_path = (
        MODEL_DIR
        / "feature_schema.pkl"
    )

    metadata_path = (
        MODEL_DIR
        / "model_metadata.json"
    )

    metrics_path = (
        ARTIFACT_DIR
        / "metrics.json"
    )

    with open(
        xgb_path,
        "wb",
    ) as file:
        pickle.dump(
            xgb_model,
            file,
            protocol=pickle.HIGHEST_PROTOCOL,
        )

    with open(
        lgb_path,
        "wb",
    ) as file:
        pickle.dump(
            lgb_model,
            file,
            protocol=pickle.HIGHEST_PROTOCOL,
        )

    xgb_cat = categorical_for(
        XGB_FEATURES
    )

    lgb_cat = categorical_for(
        LGB_FEATURES
    )

    schema = {
        "schema_version": 3,
        "weather_used": False,

        "classification": {
            "model": "XGBoost",
            "feature_columns": XGB_FEATURES,
            "categorical_features": xgb_cat,
            "numerical_features": [
                c
                for c in XGB_FEATURES
                if c not in xgb_cat
            ],
            "encoder": xgb_encoder,
            "numerical_medians": xgb_medians,
            "target": TARGET_CLASSIFICATION,
            "threshold": CLASSIFICATION_THRESHOLD,
        },

        "regression": {
            "model": "LightGBM",
            "feature_columns": LGB_FEATURES,
            "categorical_features": lgb_cat,
            "numerical_features": [
                c
                for c in LGB_FEATURES
                if c not in lgb_cat
            ],
            "encoder": lgb_encoder,
            "numerical_medians": lgb_medians,
            "target": TARGET_REGRESSION,
        },

        # Compatibility aliases for older code.
        "feature_columns": XGB_FEATURES,
        "categorical_features": xgb_cat,
        "numerical_features": [
            c
            for c in XGB_FEATURES
            if c not in xgb_cat
        ],
        "encoder": xgb_encoder,

        "decision_policy": {
            "normal_wait": "<15 minutes",
            "manual_action": "15-29 minutes",
            "automatic_action": ">=30 minutes",
        },
    }

    with open(
        schema_path,
        "wb",
    ) as file:
        pickle.dump(
            schema,
            file,
            protocol=pickle.HIGHEST_PROTOCOL,
        )

    with open(
        metrics_path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metrics,
            file,
            indent=2,
            default=str,
        )

    metadata = {
        "project": "FLITZZ",
        "training_type":
            "chronological_80_20_chunk_training",
        "weather_used": False,
        "validation_used": False,

        "models": {
            "classification": "XGBoost",
            "regression": "LightGBM",
        },

        "features": {
            "xgboost_count":
                len(XGB_FEATURES),
            "lightgbm_count":
                len(LGB_FEATURES),
            "xgboost":
                XGB_FEATURES,
            "lightgbm":
                LGB_FEATURES,
        },

        "split": {
            "train_ratio":
                TRAIN_RATIO,
            "test_ratio":
                TEST_RATIO,
            "train_rows":
                train_rows,
            "test_rows":
                test_rows,
            "train_segments":
                train_segments,
            "test_segments":
                test_segments,
        },

        "targets": {
            "classification":
                TARGET_CLASSIFICATION,
            "regression":
                TARGET_REGRESSION,
        },

        "classification_threshold":
            CLASSIFICATION_THRESHOLD,

        "decision_policy": {
            "normal_wait":
                "<15 minutes",
            "manual_action":
                "15-29 minutes",
            "automatic_action":
                ">=30 minutes",
        },

        "metrics": metrics,
    }

    with open(
        metadata_path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metadata,
            file,
            indent=2,
            default=str,
        )

    print()
    print(
        "[OK] XGBoost:",
        xgb_path,
    )
    print(
        "[OK] LightGBM:",
        lgb_path,
    )
    print(
        "[OK] Feature schema:",
        schema_path,
    )
    print(
        "[OK] Metrics:",
        metrics_path,
    )
    print(
        "[OK] Metadata:",
        metadata_path,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    start = time.time()

    print()
    print("=" * 70)
    print("FLITZZ - FINAL 80/20 CHUNK TRAINING")
    print("=" * 70)

    print()
    print(
        "[INFO] PostgreSQL       : PRIMARY DATA SOURCE"
    )
    print(
        "[INFO] Weather          : REMOVED"
    )
    print(
        f"[INFO] XGBoost features : {len(XGB_FEATURES)}"
    )
    print(
        f"[INFO] LightGBM features: {len(LGB_FEATURES)}"
    )
    print(
        f"[INFO] Chunk size       : {CHUNK_SIZE:,}"
    )
    print(
        f"[INFO] Train            : {TRAIN_RATIO:.0%}"
    )
    print(
        f"[INFO] Test             : {TEST_RATIO:.0%}"
    )
    print(
        "[INFO] Validation       : NONE"
    )

    # --------------------------------------------------------
    # Feature contract summary
    # --------------------------------------------------------

    print()
    print("XGBOOST FEATURES (24)")
    print("-" * 70)

    for i, feature in enumerate(
        XGB_FEATURES,
        1,
    ):
        print(
            f"{i:02d}. {feature}"
        )

    print()
    print("LIGHTGBM FEATURES (34)")
    print("-" * 70)

    for i, feature in enumerate(
        LGB_FEATURES,
        1,
    ):
        print(
            f"{i:02d}. {feature}"
        )

    # ========================================================
    # PASS 1: COUNT VALID ROWS
    # ========================================================

    print()
    print("=" * 70)
    print("PASS 1 - COUNT CHRONOLOGICAL DATA")
    print("=" * 70)

    total_rows = 0
    source_chunks = 0

    for raw in get_feature_chunks():

        if raw is None or raw.empty:
            continue

        prepared = prepare_target_chunk(
            raw
        )

        if not prepared.empty:
            total_rows += len(prepared)
            source_chunks += 1

        del raw
        del prepared
        gc.collect()

    if (
        MAX_TRAINING_ROWS is not None
    ):
        total_rows = min(
            total_rows,
            MAX_TRAINING_ROWS,
        )

    if total_rows < 2:
        raise RuntimeError(
            "Not enough valid rows for 80/20 training."
        )

    train_end = int(
        total_rows * TRAIN_RATIO
    )

    train_end = max(
        1,
        min(
            train_end,
            total_rows - 1,
        ),
    )

    expected_train = train_end
    expected_test = (
        total_rows
        - train_end
    )

    print(
        f"[OK] Total valid rows : {total_rows:,}"
    )
    print(
        f"[OK] Train rows       : {expected_train:,}"
    )
    print(
        f"[OK] Test rows        : {expected_test:,}"
    )
    print(
        f"[OK] Source chunks    : {source_chunks}"
    )

    # ========================================================
    # PASS 2: TRAIN 80% / TEST 20%
    # ========================================================

    print()
    print("=" * 70)
    print("PASS 2 - 80% TRAIN / 20% FINAL TEST")
    print("=" * 70)

    xgb_cat = categorical_for(
        XGB_FEATURES
    )

    lgb_cat = categorical_for(
        LGB_FEATURES
    )

    xgb_encoder = None
    lgb_encoder = None

    xgb_medians = {}
    lgb_medians = {}

    xgb_model = None
    lgb_model = None

    test_class_true = []
    test_probabilities = []

    test_reg_true = []
    test_reg_predictions = []

    rows_seen = 0

    train_rows = 0
    test_rows = 0

    train_segments = 0
    test_segments = 0

    for source_number, raw in enumerate(
        get_feature_chunks(),
        1,
    ):

        if raw is None or raw.empty:
            continue

        if rows_seen >= total_rows:
            del raw
            break

        allowed = min(
            len(raw),
            total_rows - rows_seen,
        )

        if allowed < len(raw):
            raw = raw.iloc[
                :allowed
            ].copy()

        chunk = prepare_target_chunk(
            raw
        )

        del raw
        gc.collect()

        if chunk.empty:
            continue

        chunk_start = rows_seen
        chunk_end = (
            chunk_start
            + len(chunk)
        )

        local_start = 0

        while local_start < len(chunk):

            global_start = (
                chunk_start
                + local_start
            )

            if global_start < train_end:
                split = "TRAIN"
                split_end = train_end
            else:
                split = "TEST"
                split_end = total_rows

            local_end = min(
                len(chunk),
                local_start
                + (
                    split_end
                    - global_start
                ),
            )

            part = chunk.iloc[
                local_start:local_end
            ].copy()

            # ====================================================
            # TRAIN
            # ====================================================

            if split == "TRAIN":

                # Fit encoders/medians ONLY from training data.
                if xgb_encoder is None:
                    xgb_encoder = fit_encoder(
                        part,
                        xgb_cat,
                    )

                if lgb_encoder is None:
                    lgb_encoder = fit_encoder(
                        part,
                        lgb_cat,
                    )

                if not xgb_medians:
                    xgb_medians = calculate_medians(
                        part,
                        XGB_FEATURES,
                        xgb_cat,
                    )

                if not lgb_medians:
                    lgb_medians = calculate_medians(
                        part,
                        LGB_FEATURES,
                        lgb_cat,
                    )

                X_xgb = transform_features(
                    part,
                    XGB_FEATURES,
                    xgb_cat,
                    xgb_encoder,
                    xgb_medians,
                )

                X_lgb = transform_features(
                    part,
                    LGB_FEATURES,
                    lgb_cat,
                    lgb_encoder,
                    lgb_medians,
                )

                y_class = (
                    part[
                        TARGET_CLASSIFICATION
                    ]
                    .astype(int)
                )

                y_reg = (
                    part[
                        TARGET_REGRESSION
                    ]
                    .astype(float)
                )

                # ------------------------------------------------
                # Initialize / continue XGBoost
                # ------------------------------------------------

                if xgb_model is None:

                    positive = int(
                        y_class.sum()
                    )

                    negative = (
                        len(y_class)
                        - positive
                    )

                    if positive <= 0:
                        raise RuntimeError(
                            "First training segment contains "
                            "no delayed_15=1 rows."
                        )

                    scale_pos_weight = (
                        negative
                        / positive
                    )

                    print()
                    print("=" * 70)
                    print(
                        "MODEL INITIALIZATION"
                    )
                    print("=" * 70)
                    print(
                        f"[INFO] First segment : "
                        f"{len(part):,}"
                    )
                    print(
                        f"[INFO] Positive      : "
                        f"{positive:,}"
                    )
                    print(
                        f"[INFO] Negative      : "
                        f"{negative:,}"
                    )
                    print(
                        f"[INFO] scale_pos_weight: "
                        f"{scale_pos_weight:.4f}"
                    )

                    xgb_model = create_xgb_model(
                        scale_pos_weight
                    )

                    lgb_model = create_lgb_model()

                    xgb_model.fit(
                        X_xgb,
                        y_class,
                    )

                    lgb_model.fit(
                        X_lgb,
                        y_reg,
                    )

                else:

                    previous_xgb = xgb_model
                    previous_lgb = lgb_model

                    xgb_model.fit(
                        X_xgb,
                        y_class,
                        xgb_model=previous_xgb,
                    )

                    lgb_model.fit(
                        X_lgb,
                        y_reg,
                        init_model=previous_lgb,
                    )

                train_rows += len(part)
                train_segments += 1

                print(
                    f"[TRAIN] source={source_number:03d} "
                    f"rows={len(part):,} "
                    f"total={train_rows:,}/"
                    f"{expected_train:,}"
                )

                del (
                    X_xgb,
                    X_lgb,
                    y_class,
                    y_reg,
                )

            # ====================================================
            # FINAL TEST
            # ====================================================

            else:

                if (
                    xgb_model is None
                    or lgb_model is None
                ):
                    raise RuntimeError(
                        "Test data reached before training."
                    )

                X_xgb = transform_features(
                    part,
                    XGB_FEATURES,
                    xgb_cat,
                    xgb_encoder,
                    xgb_medians,
                )

                X_lgb = transform_features(
                    part,
                    LGB_FEATURES,
                    lgb_cat,
                    lgb_encoder,
                    lgb_medians,
                )

                y_class = (
                    part[
                        TARGET_CLASSIFICATION
                    ]
                    .astype(int)
                )

                y_reg = (
                    part[
                        TARGET_REGRESSION
                    ]
                    .astype(float)
                )

                probability = (
                    xgb_model
                    .predict_proba(
                        X_xgb
                    )[:, 1]
                )

                prediction_minutes = (
                    lgb_model
                    .predict(
                        X_lgb
                    )
                )

                prediction_minutes = np.maximum(
                    prediction_minutes,
                    0,
                )

                test_class_true.append(
                    y_class.to_numpy()
                )

                test_probabilities.append(
                    probability
                )

                test_reg_true.append(
                    y_reg.to_numpy()
                )

                test_reg_predictions.append(
                    prediction_minutes
                )

                test_rows += len(part)
                test_segments += 1

                print(
                    f"[TEST ] source={source_number:03d} "
                    f"rows={len(part):,} "
                    f"total={test_rows:,}/"
                    f"{expected_test:,}"
                )

                del (
                    X_xgb,
                    X_lgb,
                    y_class,
                    y_reg,
                    probability,
                    prediction_minutes,
                )

            del part
            gc.collect()

            local_start = local_end

        rows_seen = chunk_end

        del chunk
        gc.collect()

    # ========================================================
    # FINAL SANITY
    # ========================================================

    if xgb_model is None or lgb_model is None:
        raise RuntimeError(
            "No model was trained."
        )

    if rows_seen != total_rows:
        raise RuntimeError(
            f"Row accounting mismatch: "
            f"{rows_seen:,} != {total_rows:,}"
        )

    if train_rows != expected_train:
        raise RuntimeError(
            f"Training rows mismatch: "
            f"{train_rows:,} != {expected_train:,}"
        )

    if test_rows != expected_test:
        raise RuntimeError(
            f"Test rows mismatch: "
            f"{test_rows:,} != {expected_test:,}"
        )

    # ========================================================
    # FINAL TEST METRICS
    # ========================================================

    y_test_class = np.concatenate(
        test_class_true
    )

    probability_test = np.concatenate(
        test_probabilities
    )

    y_test_reg = np.concatenate(
        test_reg_true
    )

    prediction_test_reg = np.concatenate(
        test_reg_predictions
    )

    class_metrics = classification_metrics(
        y_test_class,
        probability_test,
    )

    reg_metrics = regression_metrics(
        y_test_reg,
        prediction_test_reg,
    )

    print()
    print("=" * 70)
    print("FINAL 20% TEST RESULTS")
    print("=" * 70)

    print()
    print("XGBOOST CLASSIFICATION")
    print("-" * 70)
    print(
        f"Accuracy : {class_metrics['accuracy']:.4f}"
    )
    print(
        f"Precision: {class_metrics['precision']:.4f}"
    )
    print(
        f"Recall   : {class_metrics['recall']:.4f}"
    )
    print(
        f"F1 Score : {class_metrics['f1_score']:.4f}"
    )
    print(
        f"ROC-AUC  : {class_metrics['roc_auc']:.4f}"
    )
    print(
        f"Threshold: {CLASSIFICATION_THRESHOLD:.2f}"
    )

    print()
    print("Confusion Matrix:")
    print(
        np.array(
            class_metrics[
                "confusion_matrix"
            ]
        )
    )

    print()
    print("LIGHTGBM REGRESSION")
    print("-" * 70)
    print(
        f"MAE : {reg_metrics['mae_minutes']:.4f} minutes"
    )
    print(
        f"RMSE: {reg_metrics['rmse_minutes']:.4f} minutes"
    )
    print(
        f"R²  : {reg_metrics['r2']:.4f}"
    )

    # ========================================================
    # TEST PREDICTIONS
    # ========================================================

    test_prediction_df = pd.DataFrame(
        {
            "test_row_index":
                np.arange(
                    1,
                    test_rows + 1,
                ),
            "actual_delayed_15":
                y_test_class,
            "actual_delay_minutes":
                y_test_reg,
            "delay_probability":
                probability_test,
            "predicted_delayed_15":
                (
                    probability_test
                    >= CLASSIFICATION_THRESHOLD
                ).astype(int),
            "predicted_delay_minutes":
                prediction_test_reg,
        }
    )

    test_prediction_df[
        "recommended_action"
    ] = (
        test_prediction_df[
            "predicted_delay_minutes"
        ]
        .apply(
            decision_from_minutes
        )
    )

    test_prediction_path = (
        ARTIFACT_DIR
        / "test_predictions.parquet"
    )

    test_prediction_df.to_parquet(
        test_prediction_path,
        index=False,
        engine="pyarrow",
    )

    print()
    print(
        "[OK] Test predictions:",
        test_prediction_path,
    )

    # ========================================================
    # FEATURE IMPORTANCE
    # ========================================================

    save_feature_importance(
        xgb_model,
        lgb_model,
    )

    # ========================================================
    # METRICS / METADATA
    # ========================================================

    metrics = {
        "split": {
            "total_rows": total_rows,
            "train_rows": train_rows,
            "test_rows": test_rows,
            "train_ratio":
                train_rows / total_rows,
            "test_ratio":
                test_rows / total_rows,
        },
        "classification": class_metrics,
        "regression": reg_metrics,
    }

    save_models(
        xgb_model=xgb_model,
        lgb_model=lgb_model,
        xgb_encoder=xgb_encoder,
        lgb_encoder=lgb_encoder,
        xgb_medians=xgb_medians,
        lgb_medians=lgb_medians,
        metrics=metrics,
        train_rows=train_rows,
        test_rows=test_rows,
        train_segments=train_segments,
        test_segments=test_segments,
    )

    elapsed = (
        time.time()
        - start
    )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print("=" * 70)
    print("FLITZZ FINAL CHUNK TRAINING COMPLETE")
    print("=" * 70)

    print()
    print("DATA")
    print("-" * 70)
    print(
        f"Total rows       : {total_rows:,}"
    )
    print(
        f"Training rows    : {train_rows:,}"
    )
    print(
        f"Test rows        : {test_rows:,}"
    )
    print(
        f"Chunk size       : {CHUNK_SIZE:,}"
    )
    print(
        f"Training segments: {train_segments}"
    )
    print(
        f"Test segments    : {test_segments}"
    )

    print()
    print("FEATURES")
    print("-" * 70)
    print(
        f"XGBoost          : {len(XGB_FEATURES)}"
    )
    print(
        f"LightGBM         : {len(LGB_FEATURES)}"
    )
    print(
        "Weather          : REMOVED"
    )
    print(
        "Validation       : NONE"
    )

    print()
    print("FINAL 20% TEST")
    print("-" * 70)
    print(
        f"Accuracy : {class_metrics['accuracy']:.4f}"
    )
    print(
        f"Precision: {class_metrics['precision']:.4f}"
    )
    print(
        f"Recall   : {class_metrics['recall']:.4f}"
    )
    print(
        f"F1 Score : {class_metrics['f1_score']:.4f}"
    )
    print(
        f"ROC-AUC  : {class_metrics['roc_auc']:.4f}"
    )
    print(
        f"MAE      : {reg_metrics['mae_minutes']:.4f} min"
    )
    print(
        f"RMSE     : {reg_metrics['rmse_minutes']:.4f} min"
    )
    print(
        f"R²       : {reg_metrics['r2']:.4f}"
    )

    print()
    print("DECISION POLICY")
    print("-" * 70)
    print(
        "< 15 min   -> NORMAL / WAIT"
    )
    print(
        "15-29 min  -> MANUAL ACTION"
    )
    print(
        ">= 30 min  -> AUTOMATIC ACTION"
    )

    print()
    print(
        f"Total runtime: {elapsed:.2f} seconds"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()