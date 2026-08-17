"""
FLITZZ
======

Flight Delay Prediction ML Training Pipeline

Models:
    1. CatBoost
    2. LightGBM
    3. CatBoost + LightGBM weighted ensemble

Data source:
    PostgreSQL -> feature_builder.py -> pandas DataFrame

NO CSV IS REQUIRED.

Pipeline:
    PostgreSQL
        ↓
    feature_builder.py
        ↓
    Feature DataFrame
        ↓
    Chronological split
        ↓
    CatBoost + LightGBM
        ↓
    Ensemble
        ↓
    Evaluation
        ↓
    .pkl models

Metrics:
    Accuracy
    Precision
    Recall
    F1
    ROC-AUC
    Confusion Matrix
"""

from __future__ import annotations

import os
import json
import joblib
import warnings

import numpy as np
import pandas as pd

from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)

# ------------------------------------------------------------
# IMPORTANT
# ------------------------------------------------------------
# feature_builder.py must be in the same directory.
#
# backend/
#   ml/
#       train.py
#       feature_builder.py
#
# ------------------------------------------------------------

from feature_builder import build_features


warnings.filterwarnings("ignore")


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_DIR = "models"

TARGET = "delayed_15"

ID_COLUMN = "flight_id"

DATE_COLUMN = "flight_date"

RANDOM_STATE = 42


# ============================================================
# ENSEMBLE CONFIGURATION
# ============================================================

CATBOOST_WEIGHT = 0.50

LIGHTGBM_WEIGHT = 0.50

PREDICTION_THRESHOLD = 0.50


# ============================================================
# TIME-BASED SPLIT
# ============================================================

TRAIN_RATIO = 0.70

VALIDATION_RATIO = 0.15

TEST_RATIO = 0.15


# ============================================================
# FEATURE COLUMNS
# ============================================================

FEATURE_COLUMNS = [

    # ========================================================
    # 1. FLIGHT / SCHEDULE
    # ========================================================

    "airline_id",

    "aircraft_id",

    "origin_airport_id",

    "destination_airport_id",

    "departure_hour",

    "day_of_week",

    "month",

    "scheduled_time_minutes",

    "distance_miles",


    # ========================================================
    # 2. HISTORICAL DELAY
    # ========================================================

    "airline_delay_rate",

    "airline_average_delay",

    "route_delay_rate",

    "route_average_delay",

    "flight_number_delay_rate",

    "flight_number_average_delay",


    # ========================================================
    # 3. CONGESTION
    # ========================================================

    "origin_flights_1h",

    "destination_flights_1h",

    "route_flights_1h",

    "origin_congestion_ratio",

    "destination_congestion_ratio",

    "route_congestion_ratio",

    "origin_congestion_level",

    "destination_congestion_level",

    "route_congestion_level",


    # ========================================================
    # 4. HISTORICAL WEATHER
    # ========================================================

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

    "weather_severity",
]


# ============================================================
# CREATE MODEL DIRECTORY
# ============================================================

os.makedirs(
    MODEL_DIR,
    exist_ok=True
)


# ============================================================
# LOAD DATA FROM POSTGRESQL
# ============================================================

def load_dataset() -> pd.DataFrame:

    print()
    print("=" * 70)
    print("BUILDING FEATURE DATASET FROM POSTGRESQL")
    print("=" * 70)

    print()
    print("[INFO] PostgreSQL is the primary data source.")

    print(
        "[INFO] Calling feature_builder.build_features()..."
    )

    # --------------------------------------------------------
    # feature_builder:
    #
    # PostgreSQL
    #     ↓
    # flights
    #     ↓
    # historical delay
    #     ↓
    # congestion
    #     ↓
    # airports
    #     ↓
    # Open-Meteo historical weather
    # --------------------------------------------------------

    df = build_features(
        use_weather=True
    )

    if df is None:

        raise RuntimeError(
            "feature_builder.build_features() returned None."
        )

    if df.empty:

        raise RuntimeError(
            "Feature builder returned an empty dataset."
        )

    print()

    print(
        f"[OK] Feature rows generated: "
        f"{len(df):,}"
    )

    print(
        f"[OK] Dataset columns: "
        f"{len(df.columns)}"
    )

    # --------------------------------------------------------
    # Check required columns
    # --------------------------------------------------------

    required_columns = (

        [
            ID_COLUMN,
            DATE_COLUMN
        ]

        +

        FEATURE_COLUMNS

        +

        [
            TARGET
        ]
    )

    missing_columns = [

        column

        for column in required_columns

        if column not in df.columns
    ]

    if missing_columns:

        raise ValueError(
            "\nMissing required columns "
            "from feature builder:\n\n"
            +
            "\n".join(
                missing_columns
            )
        )

    print(
        "[OK] All required columns are present."
    )

    return df


# ============================================================
# PREPARE DATA
# ============================================================

def prepare_data(
    df: pd.DataFrame
) -> pd.DataFrame:

    print()
    print("=" * 70)
    print("PREPARING DATA")
    print("=" * 70)

    df = df.copy()

    # --------------------------------------------------------
    # Flight date
    # --------------------------------------------------------

    df[DATE_COLUMN] = pd.to_datetime(
        df[DATE_COLUMN],
        errors="coerce"
    )

    invalid_dates = df[
        DATE_COLUMN
    ].isna().sum()

    if invalid_dates > 0:

        print(
            f"[WARNING] Removing "
            f"{invalid_dates:,} rows with invalid dates."
        )

        df = df[
            df[DATE_COLUMN].notna()
        ]

    # --------------------------------------------------------
    # Target
    # --------------------------------------------------------

    df[TARGET] = pd.to_numeric(
        df[TARGET],
        errors="coerce"
    )

    df = df[
        df[TARGET].notna()
    ]

    df[TARGET] = df[
        TARGET
    ].astype(int)

    # --------------------------------------------------------
    # Make sure target is binary
    # --------------------------------------------------------

    invalid_target = ~df[
        TARGET
    ].isin([0, 1])

    if invalid_target.any():

        print(
            "[WARNING] Removing rows "
            "with invalid target values."
        )

        df = df[
            ~invalid_target
        ]

    # --------------------------------------------------------
    # Numeric feature conversion
    # --------------------------------------------------------

    for column in FEATURE_COLUMNS:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # --------------------------------------------------------
    # Replace infinity
    # --------------------------------------------------------

    df[
        FEATURE_COLUMNS
    ] = df[
        FEATURE_COLUMNS
    ].replace(
        [
            np.inf,
            -np.inf
        ],
        np.nan
    )

    # --------------------------------------------------------
    # Sort chronologically
    #
    # This is extremely important.
    #
    # Older flights -> training
    # Later flights -> validation/test
    # --------------------------------------------------------

    df = df.sort_values(
        [
            DATE_COLUMN,
            ID_COLUMN
        ]
    )

    df = df.reset_index(
        drop=True
    )

    print(
        f"[OK] Prepared rows: "
        f"{len(df):,}"
    )

    print()

    print(
        "[INFO] Date range:"
    )

    print(
        f"       {df[DATE_COLUMN].min()}"
    )

    print(
        f"       {df[DATE_COLUMN].max()}"
    )

    print()

    print(
        "[INFO] Target distribution:"
    )

    target_distribution = (
        df[TARGET]
        .value_counts(
            normalize=True
        )
        .sort_index()
    )

    for value, percentage in (
        target_distribution.items()
    ):

        label = (
            "ON-TIME"
            if value == 0
            else "DELAYED"
        )

        print(
            f"       {label} ({value}) : "
            f"{percentage * 100:.2f}%"
        )

    return df


# ============================================================
# TIME-BASED SPLIT
# ============================================================

def time_split(
    df: pd.DataFrame
):

    print()
    print("=" * 70)
    print("CHRONOLOGICAL TIME-BASED SPLIT")
    print("=" * 70)

    if abs(
        TRAIN_RATIO
        +
        VALIDATION_RATIO
        +
        TEST_RATIO
        - 1.0
    ) > 0.001:

        raise ValueError(
            "Train + Validation + Test "
            "ratios must equal 1.0"
        )

    n = len(df)

    train_end = int(
        n * TRAIN_RATIO
    )

    validation_end = int(
        n *
        (
            TRAIN_RATIO
            +
            VALIDATION_RATIO
        )
    )

    train_df = df.iloc[
        :train_end
    ].copy()

    validation_df = df.iloc[
        train_end:validation_end
    ].copy()

    test_df = df.iloc[
        validation_end:
    ].copy()

    # --------------------------------------------------------
    # Print split information
    # --------------------------------------------------------

    print()

    print(
        f"Train      : "
        f"{len(train_df):,} rows"
    )

    print(
        f"Validation : "
        f"{len(validation_df):,} rows"
    )

    print(
        f"Test       : "
        f"{len(test_df):,} rows"
    )

    print()

    print(
        "Train dates:"
    )

    print(
        f"    {train_df[DATE_COLUMN].min()}"
        f" → "
        f"{train_df[DATE_COLUMN].max()}"
    )

    print()

    print(
        "Validation dates:"
    )

    print(
        f"    {validation_df[DATE_COLUMN].min()}"
        f" → "
        f"{validation_df[DATE_COLUMN].max()}"
    )

    print()

    print(
        "Test dates:"
    )

    print(
        f"    {test_df[DATE_COLUMN].min()}"
        f" → "
        f"{test_df[DATE_COLUMN].max()}"
    )

    # --------------------------------------------------------
    # Safety check
    # --------------------------------------------------------

    if (
        train_df[DATE_COLUMN].max()
        >=
        validation_df[DATE_COLUMN].min()
    ):

        raise RuntimeError(
            "Temporal split error: "
            "training overlaps validation."
        )

    if (
        validation_df[DATE_COLUMN].max()
        >=
        test_df[DATE_COLUMN].min()
    ):

        raise RuntimeError(
            "Temporal split error: "
            "validation overlaps test."
        )

    print()

    print(
        "[OK] No chronological overlap."
    )

    return (
        train_df,
        validation_df,
        test_df
    )


# ============================================================
# X / Y
# ============================================================

def xy_split(
    df: pd.DataFrame
):

    X = df[
        FEATURE_COLUMNS
    ].copy()

    y = df[
        TARGET
    ].copy()

    return X, y


# ============================================================
# CATBOOST
# ============================================================

def train_catboost(
    X_train,
    y_train,
    X_validation,
    y_validation
):

    print()
    print("=" * 70)
    print("TRAINING CATBOOST")
    print("=" * 70)

    model = CatBoostClassifier(

        iterations=600,

        depth=8,

        learning_rate=0.05,

        loss_function="Logloss",

        eval_metric="AUC",

        random_seed=RANDOM_STATE,

        verbose=100,

        allow_writing_files=False,

        l2_leaf_reg=5,

        random_strength=1,

        auto_class_weights="Balanced"
    )

    model.fit(

        X_train,

        y_train,

        eval_set=(
            X_validation,
            y_validation
        ),

        early_stopping_rounds=80
    )

    print()

    print(
        "[OK] CatBoost training complete."
    )

    print(
        f"[INFO] Best iteration: "
        f"{model.get_best_iteration()}"
    )

    return model


# ============================================================
# LIGHTGBM
# ============================================================

def train_lightgbm(
    X_train,
    y_train,
    X_validation,
    y_validation
):

    print()
    print("=" * 70)
    print("TRAINING LIGHTGBM")
    print("=" * 70)

    model = LGBMClassifier(

        n_estimators=600,

        learning_rate=0.05,

        num_leaves=31,

        max_depth=-1,

        min_child_samples=30,

        subsample=0.8,

        colsample_bytree=0.8,

        reg_alpha=0.1,

        reg_lambda=0.1,

        random_state=RANDOM_STATE,

        objective="binary",

        n_jobs=-1,

        verbosity=-1,

        class_weight="balanced"
    )

    model.fit(

        X_train,

        y_train,

        eval_set=[
            (
                X_validation,
                y_validation
            )
        ]
    )

    print()

    print(
        "[OK] LightGBM training complete."
    )

    return model


# ============================================================
# MODEL METRICS
# ============================================================

def evaluate_predictions(
    name: str,
    y_true,
    predictions,
    probabilities
):

    accuracy = accuracy_score(
        y_true,
        predictions
    )

    precision = precision_score(
        y_true,
        predictions,
        zero_division=0
    )

    recall = recall_score(
        y_true,
        predictions,
        zero_division=0
    )

    f1 = f1_score(
        y_true,
        predictions,
        zero_division=0
    )

    # --------------------------------------------------------
    # ROC-AUC can fail if test data contains only one class.
    # --------------------------------------------------------

    try:

        roc_auc = roc_auc_score(
            y_true,
            probabilities
        )

    except ValueError:

        roc_auc = 0.0

    matrix = confusion_matrix(
        y_true,
        predictions
    )

    print()
    print("-" * 70)
    print(name)
    print("-" * 70)

    print(
        f"Accuracy  : {accuracy:.4f}"
    )

    print(
        f"Precision : {precision:.4f}"
    )

    print(
        f"Recall    : {recall:.4f}"
    )

    print(
        f"F1 Score  : {f1:.4f}"
    )

    print(
        f"ROC-AUC   : {roc_auc:.4f}"
    )

    print()

    print(
        "Confusion Matrix:"
    )

    print(matrix)

    print()

    print(
        classification_report(
            y_true,
            predictions,
            target_names=[
                "ON-TIME",
                "DELAYED"
            ],
            zero_division=0
        )
    )

    return {

        "accuracy":
            float(accuracy),

        "precision":
            float(precision),

        "recall":
            float(recall),

        "f1":
            float(f1),

        "roc_auc":
            float(roc_auc),

        "confusion_matrix":
            matrix.tolist()
    }


# ============================================================
# SINGLE MODEL EVALUATION
# ============================================================

def evaluate_model(
    name,
    model,
    X,
    y
):

    probabilities = (
        model
        .predict_proba(X)
        [:, 1]
    )

    predictions = (
        probabilities
        >= PREDICTION_THRESHOLD
    ).astype(int)

    return evaluate_predictions(
        name,
        y,
        predictions,
        probabilities
    )


# ============================================================
# ENSEMBLE PREDICTION
# ============================================================

def ensemble_predict(
    catboost_model,
    lightgbm_model,
    X
):

    catboost_probability = (

        catboost_model
        .predict_proba(X)
        [:, 1]
    )

    lightgbm_probability = (

        lightgbm_model
        .predict_proba(X)
        [:, 1]
    )

    # --------------------------------------------------------
    # Weighted probability ensemble
    # --------------------------------------------------------

    ensemble_probability = (

        CATBOOST_WEIGHT
        *
        catboost_probability

        +

        LIGHTGBM_WEIGHT
        *
        lightgbm_probability
    )

    ensemble_prediction = (

        ensemble_probability
        >= PREDICTION_THRESHOLD
    ).astype(int)

    return (
        ensemble_prediction,
        ensemble_probability,
        catboost_probability,
        lightgbm_probability
    )


# ============================================================
# SAVE MODELS
# ============================================================

def save_models(
    catboost_model,
    lightgbm_model
):

    print()
    print("=" * 70)
    print("SAVING MODELS")
    print("=" * 70)

    # --------------------------------------------------------
    # CatBoost
    # --------------------------------------------------------

    catboost_path = os.path.join(
        MODEL_DIR,
        "catboost_model.pkl"
    )

    joblib.dump(
        catboost_model,
        catboost_path
    )

    print(
        f"[OK] {catboost_path}"
    )

    # --------------------------------------------------------
    # LightGBM
    # --------------------------------------------------------

    lightgbm_path = os.path.join(
        MODEL_DIR,
        "lightgbm_model.pkl"
    )

    joblib.dump(
        lightgbm_model,
        lightgbm_path
    )

    print(
        f"[OK] {lightgbm_path}"
    )

    # --------------------------------------------------------
    # Ensemble configuration
    # --------------------------------------------------------

    ensemble_config = {

        "catboost_weight":
            CATBOOST_WEIGHT,

        "lightgbm_weight":
            LIGHTGBM_WEIGHT,

        "threshold":
            PREDICTION_THRESHOLD,

        "features":
            FEATURE_COLUMNS,

        "target":
            TARGET,

        "model_type":
            "weighted_probability_ensemble"
    }

    ensemble_path = os.path.join(
        MODEL_DIR,
        "ensemble_model.pkl"
    )

    joblib.dump(
        ensemble_config,
        ensemble_path
    )

    print(
        f"[OK] {ensemble_path}"
    )


# ============================================================
# SAVE FEATURE IMPORTANCE
# ============================================================

def save_feature_importance(
    catboost_model,
    lightgbm_model
):

    # --------------------------------------------------------
    # CatBoost importance
    # --------------------------------------------------------

    catboost_importance = (
        catboost_model
        .get_feature_importance()
    )

    # --------------------------------------------------------
    # LightGBM importance
    # --------------------------------------------------------

    lightgbm_importance = (
        lightgbm_model
        .feature_importances_
    )

    importance_df = pd.DataFrame({

        "feature":
            FEATURE_COLUMNS,

        "catboost_importance":
            catboost_importance,

        "lightgbm_importance":
            lightgbm_importance
    })

    # --------------------------------------------------------
    # Normalize each model's importance
    # --------------------------------------------------------

    cat_total = (
        importance_df[
            "catboost_importance"
        ].sum()
    )

    lgb_total = (
        importance_df[
            "lightgbm_importance"
        ].sum()
    )

    if cat_total > 0:

        importance_df[
            "catboost_normalized"
        ] = (
            importance_df[
                "catboost_importance"
            ]
            /
            cat_total
        )

    else:

        importance_df[
            "catboost_normalized"
        ] = 0.0

    if lgb_total > 0:

        importance_df[
            "lightgbm_normalized"
        ] = (
            importance_df[
                "lightgbm_importance"
            ]
            /
            lgb_total
        )

    else:

        importance_df[
            "lightgbm_normalized"
        ] = 0.0

    # --------------------------------------------------------
    # Ensemble importance
    # --------------------------------------------------------

    importance_df[
        "ensemble_importance"
    ] = (

        CATBOOST_WEIGHT
        *
        importance_df[
            "catboost_normalized"
        ]

        +

        LIGHTGBM_WEIGHT
        *
        importance_df[
            "lightgbm_normalized"
        ]
    )

    importance_df = (
        importance_df
        .sort_values(
            "ensemble_importance",
            ascending=False
        )
        .reset_index(drop=True)
    )

    output_path = os.path.join(
        MODEL_DIR,
        "feature_importance.csv"
    )

    importance_df.to_csv(
        output_path,
        index=False
    )

    print()
    print(
        f"[OK] Feature importance saved:"
    )

    print(
        f"     {output_path}"
    )

    print()

    print(
        "Top 10 features:"
    )

    print(
        importance_df[
            [
                "feature",
                "ensemble_importance"
            ]
        ].head(10).to_string(
            index=False
        )
    )

    return importance_df


# ============================================================
# SAVE METRICS
# ============================================================

def save_metrics(
    catboost_metrics,
    lightgbm_metrics,
    ensemble_metrics,
    train_df,
    validation_df,
    test_df
):

    metrics = {

        "models": {

            "catboost":
                catboost_metrics,

            "lightgbm":
                lightgbm_metrics,

            "ensemble":
                ensemble_metrics
        },

        "ensemble_configuration": {

            "catboost_weight":
                CATBOOST_WEIGHT,

            "lightgbm_weight":
                LIGHTGBM_WEIGHT,

            "threshold":
                PREDICTION_THRESHOLD
        },

        "dataset": {

            "total_rows":
                (
                    len(train_df)
                    +
                    len(validation_df)
                    +
                    len(test_df)
                ),

            "train_rows":
                len(train_df),

            "validation_rows":
                len(validation_df),

            "test_rows":
                len(test_df),

            "train_start":
                str(
                    train_df[
                        DATE_COLUMN
                    ].min()
                ),

            "train_end":
                str(
                    train_df[
                        DATE_COLUMN
                    ].max()
                ),

            "validation_start":
                str(
                    validation_df[
                        DATE_COLUMN
                    ].min()
                ),

            "validation_end":
                str(
                    validation_df[
                        DATE_COLUMN
                    ].max()
                ),

            "test_start":
                str(
                    test_df[
                        DATE_COLUMN
                    ].min()
                ),

            "test_end":
                str(
                    test_df[
                        DATE_COLUMN
                    ].max()
                )
        },

        "features": FEATURE_COLUMNS,

        "target": TARGET
    }

    path = os.path.join(
        MODEL_DIR,
        "metrics.json"
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            metrics,
            file,
            indent=4
        )

    print()
    print(
        f"[OK] Metrics saved:"
    )

    print(
        f"     {path}"
    )


# ============================================================
# SAVE TEST PREDICTIONS
# ============================================================

def save_test_predictions(
    test_df,
    y_test,
    catboost_probability,
    lightgbm_probability,
    ensemble_probability,
    ensemble_prediction
):

    output = test_df[
        [
            ID_COLUMN,
            DATE_COLUMN
        ]
    ].copy()

    output[
        "actual_delay"
    ] = y_test.values

    output[
        "catboost_probability"
    ] = catboost_probability

    output[
        "lightgbm_probability"
    ] = lightgbm_probability

    output[
        "ensemble_probability"
    ] = ensemble_probability

    output[
        "predicted_delay"
    ] = ensemble_prediction

    output[
        "risk_level"
    ] = pd.cut(

        ensemble_probability,

        bins=[
            -np.inf,
            0.30,
            0.60,
            0.80,
            np.inf
        ],

        labels=[
            "LOW",
            "MEDIUM",
            "HIGH",
            "VERY_HIGH"
        ]
    )

    path = os.path.join(
        MODEL_DIR,
        "test_predictions.csv"
    )

    output.to_csv(
        path,
        index=False
    )

    print()
    print(
        f"[OK] Test predictions saved:"
    )

    print(
        f"     {path}"
    )


# ============================================================
# MAIN TRAINING PIPELINE
# ============================================================

def main():

    print()
    print("=" * 70)
    print("FLITZZ DELAY PREDICTION")
    print("CATBOOST + LIGHTGBM ENSEMBLE")
    print("=" * 70)

    # ========================================================
    # STEP 1
    # PostgreSQL -> Feature Builder
    # ========================================================

    df = load_dataset()

    # ========================================================
    # STEP 2
    # Prepare
    # ========================================================

    df = prepare_data(
        df
    )

    # ========================================================
    # STEP 3
    # Chronological split
    # ========================================================

    (
        train_df,
        validation_df,
        test_df
    ) = time_split(
        df
    )

    # ========================================================
    # STEP 4
    # X / Y
    # ========================================================

    X_train, y_train = xy_split(
        train_df
    )

    X_validation, y_validation = xy_split(
        validation_df
    )

    X_test, y_test = xy_split(
        test_df
    )

    print()
    print(
        f"[OK] Training features: "
        f"{X_train.shape}"
    )

    print(
        f"[OK] Validation features: "
        f"{X_validation.shape}"
    )

    print(
        f"[OK] Test features: "
        f"{X_test.shape}"
    )

    # ========================================================
    # STEP 5
    # CatBoost
    # ========================================================

    catboost_model = train_catboost(

        X_train,
        y_train,

        X_validation,
        y_validation
    )

    # ========================================================
    # STEP 6
    # LightGBM
    # ========================================================

    lightgbm_model = train_lightgbm(

        X_train,
        y_train,

        X_validation,
        y_validation
    )

    # ========================================================
    # STEP 7
    # Individual model evaluation
    # ========================================================

    print()
    print("=" * 70)
    print("FINAL TEST SET EVALUATION")
    print("=" * 70)

    catboost_metrics = evaluate_model(

        "CATBOOST",

        catboost_model,

        X_test,
        y_test
    )

    lightgbm_metrics = evaluate_model(

        "LIGHTGBM",

        lightgbm_model,

        X_test,
        y_test
    )

    # ========================================================
    # STEP 8
    # Ensemble
    # ========================================================

    (
        ensemble_prediction,
        ensemble_probability,
        catboost_probability,
        lightgbm_probability

    ) = ensemble_predict(

        catboost_model,

        lightgbm_model,

        X_test
    )

    ensemble_metrics = evaluate_predictions(

        "CATBOOST + LIGHTGBM ENSEMBLE",

        y_test,

        ensemble_prediction,

        ensemble_probability
    )

    # ========================================================
    # STEP 9
    # Save models
    # ========================================================

    save_models(

        catboost_model,

        lightgbm_model
    )

    # ========================================================
    # STEP 10
    # Feature importance
    # ========================================================

    save_feature_importance(

        catboost_model,

        lightgbm_model
    )

    # ========================================================
    # STEP 11
    # Metrics
    # ========================================================

    save_metrics(

        catboost_metrics,

        lightgbm_metrics,

        ensemble_metrics,

        train_df,

        validation_df,

        test_df
    )

    # ========================================================
    # STEP 12
    # Test predictions
    # ========================================================

    save_test_predictions(

        test_df,

        y_test,

        catboost_probability,

        lightgbm_probability,

        ensemble_probability,

        ensemble_prediction
    )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print("=" * 70)
    print("TRAINING COMPLETE")
    print("=" * 70)

    print()

    print(
        f"CatBoost ROC-AUC : "
        f"{catboost_metrics['roc_auc']:.4f}"
    )

    print(
        f"LightGBM ROC-AUC : "
        f"{lightgbm_metrics['roc_auc']:.4f}"
    )

    print(
        f"Ensemble ROC-AUC : "
        f"{ensemble_metrics['roc_auc']:.4f}"
    )

    print()

    print(
        f"Ensemble Accuracy : "
        f"{ensemble_metrics['accuracy']:.4f}"
    )

    print(
        f"Ensemble Precision: "
        f"{ensemble_metrics['precision']:.4f}"
    )

    print(
        f"Ensemble Recall   : "
        f"{ensemble_metrics['recall']:.4f}"
    )

    print(
        f"Ensemble F1       : "
        f"{ensemble_metrics['f1']:.4f}"
    )

    print()

    print(
        "Saved files:"
    )

    print(
        f"  {MODEL_DIR}/catboost_model.pkl"
    )

    print(
        f"  {MODEL_DIR}/lightgbm_model.pkl"
    )

    print(
        f"  {MODEL_DIR}/ensemble_model.pkl"
    )

    print(
        f"  {MODEL_DIR}/metrics.json"
    )

    print(
        f"  {MODEL_DIR}/feature_importance.csv"
    )

    print(
        f"  {MODEL_DIR}/test_predictions.csv"
    )

    print()

    print(
        "[SUCCESS] FLITZZ ML training pipeline finished."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()