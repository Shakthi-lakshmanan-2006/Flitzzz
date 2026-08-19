"""
FLITZZ - OFFLINE MODEL TRAINING

DUAL MODEL ARCHITECTURE
-----------------------
XGBoost
    -> classification
    -> probability that arrival delay >= 15 minutes
    -> uses XGB_FEATURES from features.py

LightGBM
    -> regression
    -> approximate arrival delay in minutes
    -> uses LGBM_FEATURES from features.py

DATA
----
datasets/feature_dataset.parquet

SPLIT
-----
Chronological 80% train / 20% test.
No validation split.

IMPORTANT
---------
Weather is not used.

XGBoost and LightGBM do NOT receive the same feature dataframe:
    XGBoost  -> 24-feature contract
    LightGBM -> 34-feature contract

This keeps the model inputs consistent with the updated features.py.
"""

from __future__ import annotations

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


# ============================================================================
# PATHS
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DATASET_FILE = BASE_DIR / "datasets" / "feature_dataset.parquet"
MODEL_DIR = BASE_DIR / "models"
ARTIFACT_DIR = BASE_DIR / "artifacts"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# FEATURES
# ============================================================================

from features import (
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

MAX_ROWS = None

TEST_SIZE = 0.20
RANDOM_STATE = 42

# XGBoost
XGB_TREES = 300
XGB_LEARNING_RATE = 0.05
XGB_MAX_DEPTH = 6
XGB_MIN_CHILD_WEIGHT = 3
XGB_SUBSAMPLE = 0.85
XGB_COLSAMPLE = 0.85
XGB_REG_ALPHA = 0.05
XGB_REG_LAMBDA = 1.0

# LightGBM
LGB_TREES = 400
LGB_LEARNING_RATE = 0.05
LGB_NUM_LEAVES = 31
LGB_MAX_DEPTH = -1
LGB_MIN_CHILD_SAMPLES = 30
LGB_SUBSAMPLE = 0.85
LGB_COLSAMPLE = 0.85

# Operational classification threshold.
# Keep this configurable because 0.50 is the neutral probability threshold.
CLASSIFICATION_THRESHOLD = 0.50


# ============================================================================
# HELPERS
# ============================================================================

def normalize_categorical_columns(
    frame: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """Return a copy with categorical values normalized to strings."""

    result = frame.copy()

    for column in columns:
        if column not in result.columns:
            raise RuntimeError(
                f"Required categorical feature missing: {column}"
            )

        result[column] = (
            result[column]
            .fillna("UNKNOWN")
            .astype(str)
        )

    return result


def validate_feature_contracts(df: pd.DataFrame) -> None:
    """Validate the feature contracts imported from features.py."""

    print()
    print("=" * 70)
    print("FEATURE CONTRACT VALIDATION")
    print("=" * 70)

    print(f"[INFO] Master features : {len(MODEL_FEATURES)}")
    print(f"[INFO] XGBoost features: {len(XGB_FEATURES)}")
    print(f"[INFO] LightGBM features: {len(LGBM_FEATURES)}")

    if len(XGB_FEATURES) != 24:
        raise RuntimeError(
            f"XGBoost must use exactly 24 features. "
            f"Got {len(XGB_FEATURES)}."
        )

    if len(LGBM_FEATURES) != 34:
        raise RuntimeError(
            f"LightGBM must use exactly 34 features. "
            f"Got {len(LGBM_FEATURES)}."
        )

    if len(set(XGB_FEATURES)) != len(XGB_FEATURES):
        raise RuntimeError("Duplicate XGBoost feature detected.")

    if len(set(LGBM_FEATURES)) != len(LGBM_FEATURES):
        raise RuntimeError("Duplicate LightGBM feature detected.")

    if not set(XGB_FEATURES).issubset(set(MODEL_FEATURES)):
        missing = sorted(set(XGB_FEATURES) - set(MODEL_FEATURES))
        raise RuntimeError(
            "XGBoost features missing from master feature set: "
            + ", ".join(missing)
        )

    if not set(LGBM_FEATURES).issubset(set(MODEL_FEATURES)):
        missing = sorted(set(LGBM_FEATURES) - set(MODEL_FEATURES))
        raise RuntimeError(
            "LightGBM features missing from master feature set: "
            + ", ".join(missing)
        )

    missing_xgb = [c for c in XGB_FEATURES if c not in df.columns]
    missing_lgb = [c for c in LGBM_FEATURES if c not in df.columns]

    if missing_xgb:
        raise RuntimeError(
            "Dataset missing XGBoost features:\n"
            + "\n".join(f"  - {c}" for c in missing_xgb)
        )

    if missing_lgb:
        raise RuntimeError(
            "Dataset missing LightGBM features:\n"
            + "\n".join(f"  - {c}" for c in missing_lgb)
        )

    # Explicit weather guard.
    weather_terms = (
        "weather",
        "temperature",
        "humidity",
        "wind",
        "precipitation",
        "visibility",
        "pressure",
        "rain",
        "snow",
        "cloud",
    )

    weather_features = [
        c
        for c in set(XGB_FEATURES + LGBM_FEATURES)
        if any(term in c.lower() for term in weather_terms)
    ]

    if weather_features:
        raise RuntimeError(
            "Weather-related model features detected: "
            + ", ".join(sorted(weather_features))
        )

    print("[OK] XGBoost = 24 features")
    print("[OK] LightGBM = 34 features")
    print("[OK] Weather = removed")
    print("[OK] Feature contracts are valid.")


# ============================================================================
# DATA LOADING
# ============================================================================

def load_dataset() -> pd.DataFrame:
    """Load the development parquet dataset."""

    print()
    print("=" * 70)
    print("LOADING FEATURE DATASET")
    print("=" * 70)

    print(f"[INFO] Dataset: {DATASET_FILE}")

    if not DATASET_FILE.exists():
        raise FileNotFoundError(
            "\nFeature dataset was not found.\n\n"
            f"Expected:\n{DATASET_FILE}\n\n"
            "Run:\n"
            "    python build_dataset.py\n"
            "first."
        )

    df = pd.read_parquet(
        DATASET_FILE,
        engine="pyarrow",
    )

    print(f"[OK] Loaded {len(df):,} rows")
    print(f"[OK] Loaded {len(df.columns):,} columns")

    if MAX_ROWS is not None and len(df) > MAX_ROWS:
        df = df.head(MAX_ROWS).copy()
        print(f"[INFO] MAX_ROWS applied: {MAX_ROWS:,}")

    print(f"[OK] Final dataset size: {len(df):,} rows")

    return df


# ============================================================================
# TARGET VALIDATION
# ============================================================================

def prepare_targets(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize both targets."""

    print()
    print("=" * 70)
    print("VALIDATING TARGETS")
    print("=" * 70)

    required = [
        TARGET_CLASSIFICATION,
        TARGET_REGRESSION,
    ]

    missing = [c for c in required if c not in df.columns]

    if missing:
        raise RuntimeError(
            "Missing target columns:\n"
            + "\n".join(f"  - {c}" for c in missing)
        )

    result = df.copy()

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
    ].copy()

    result = result[
        result[TARGET_REGRESSION].notna()
    ].copy()

    result[TARGET_REGRESSION] = (
        result[TARGET_REGRESSION]
        .clip(lower=0)
    )

    result[TARGET_CLASSIFICATION] = (
        result[TARGET_CLASSIFICATION]
        .astype(np.int8)
    )

    print(f"[OK] Usable rows: {len(result):,}")
    print(
        "[INFO] Delayed >=15 minutes: "
        f"{result[TARGET_CLASSIFICATION].mean() * 100:.2f}%"
    )
    print(
        "[INFO] Average actual delay: "
        f"{result[TARGET_REGRESSION].mean():.2f} minutes"
    )
    print(
        "[INFO] Maximum actual delay: "
        f"{result[TARGET_REGRESSION].max():.2f} minutes"
    )

    return result


# ============================================================================
# CHRONOLOGICAL 80/20 SPLIT
# ============================================================================

def chronological_split(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Sort chronologically and split 80% train / 20% test."""

    print()
    print("=" * 70)
    print("CHRONOLOGICAL 80/20 TRAIN / TEST SPLIT")
    print("=" * 70)

    if "flight_datetime" not in df.columns:
        raise RuntimeError(
            "flight_datetime is required for chronological splitting."
        )

    result = df.copy()

    result["flight_datetime"] = pd.to_datetime(
        result["flight_datetime"],
        errors="coerce",
        utc=True,
    )

    result = result[
        result["flight_datetime"].notna()
    ].copy()

    sort_columns = ["flight_datetime"]

    if "flight_id" in result.columns:
        sort_columns.append("flight_id")

    result = (
        result
        .sort_values(
            sort_columns,
            kind="mergesort",
        )
        .reset_index(drop=True)
    )

    split_index = int(len(result) * (1.0 - TEST_SIZE))

    if split_index <= 0 or split_index >= len(result):
        raise RuntimeError("Invalid chronological 80/20 split.")

    train_df = result.iloc[:split_index].copy()
    test_df = result.iloc[split_index:].copy()

    print(f"[OK] Total rows : {len(result):,}")
    print(f"[OK] Train rows : {len(train_df):,}")
    print(f"[OK] Test rows  : {len(test_df):,}")

    print()
    print("TRAIN DATE RANGE")
    print(
        f"  {train_df['flight_datetime'].min()} "
        f"-> "
        f"{train_df['flight_datetime'].max()}"
    )

    print()
    print("TEST DATE RANGE")
    print(
        f"  {test_df['flight_datetime'].min()} "
        f"-> "
        f"{test_df['flight_datetime'].max()}"
    )

    if (
        train_df["flight_datetime"].max()
        > test_df["flight_datetime"].min()
    ):
        raise RuntimeError(
            "Chronological leakage detected: "
            "training data extends into the test period."
        )

    print("[OK] No chronological overlap.")

    return train_df, test_df


# ============================================================================
# MODEL-SPECIFIC PREPROCESSING
# ============================================================================

def prepare_model_features(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_columns: list[str],
    model_name: str,
) -> tuple[pd.DataFrame, pd.DataFrame, OrdinalEncoder, list[str]]:
    """
    Prepare a feature matrix for ONE model.

    Encoder and numerical imputation are fitted on training data only.
    """

    print()
    print("-" * 70)
    print(f"PREPARING {model_name} FEATURES")
    print("-" * 70)

    missing_train = [
        c for c in feature_columns
        if c not in train_df.columns
    ]
    missing_test = [
        c for c in feature_columns
        if c not in test_df.columns
    ]

    if missing_train or missing_test:
        raise RuntimeError(
            f"{model_name} feature mismatch.\n"
            f"Missing from train: {missing_train}\n"
            f"Missing from test : {missing_test}"
        )

    X_train = train_df[feature_columns].copy()
    X_test = test_df[feature_columns].copy()

    categorical_features = [
        c for c in CATEGORICAL_FEATURES
        if c in feature_columns
    ]

    numerical_features = [
        c for c in feature_columns
        if c not in categorical_features
    ]

    encoder = OrdinalEncoder(
        handle_unknown="use_encoded_value",
        unknown_value=-1,
    )

    # Categorical encoding is fitted ONLY on training data.
    if categorical_features:
        X_train[categorical_features] = normalize_categorical_columns(
            X_train,
            categorical_features,
        )[categorical_features]

        X_test[categorical_features] = normalize_categorical_columns(
            X_test,
            categorical_features,
        )[categorical_features]

        X_train[categorical_features] = encoder.fit_transform(
            X_train[categorical_features]
        )

        X_test[categorical_features] = encoder.transform(
            X_test[categorical_features]
        )

    # Numerical conversion and training-only median imputation.
    for column in numerical_features:
        X_train[column] = pd.to_numeric(
            X_train[column],
            errors="coerce",
        )

        X_test[column] = pd.to_numeric(
            X_test[column],
            errors="coerce",
        )

        X_train[column] = X_train[column].replace(
            [np.inf, -np.inf],
            np.nan,
        )

        X_test[column] = X_test[column].replace(
            [np.inf, -np.inf],
            np.nan,
        )

        median_value = X_train[column].median()

        if pd.isna(median_value):
            median_value = 0.0

        X_train[column] = X_train[column].fillna(median_value)
        X_test[column] = X_test[column].fillna(median_value)

    # Consistent numeric dtype.
    X_train = X_train.astype(np.float32)
    X_test = X_test.astype(np.float32)

    print(f"[OK] {model_name} features: {len(feature_columns)}")
    print(f"[OK] Categorical: {len(categorical_features)}")
    print(f"[OK] Numerical: {len(numerical_features)}")
    print(f"[OK] Train shape: {X_train.shape}")
    print(f"[OK] Test shape : {X_test.shape}")

    return (
        X_train,
        X_test,
        encoder,
        numerical_features,
    )


# ============================================================================
# XGBOOST CLASSIFIER
# ============================================================================

def train_xgboost(
    X_train: pd.DataFrame,
    y_train: pd.Series,
) -> XGBClassifier:

    print()
    print("=" * 70)
    print("TRAINING XGBOOST CLASSIFIER")
    print("=" * 70)

    positive = int(y_train.sum())
    negative = int(len(y_train) - positive)

    if positive == 0 or negative == 0:
        raise RuntimeError(
            "Training classification target must contain both classes."
        )

    scale_pos_weight = negative / positive

    print(f"[INFO] Positive samples : {positive:,}")
    print(f"[INFO] Negative samples : {negative:,}")
    print(f"[INFO] Class weight     : {scale_pos_weight:.3f}")
    print(f"[INFO] Trees            : {XGB_TREES}")
    print(f"[INFO] Learning rate    : {XGB_LEARNING_RATE}")

    model = XGBClassifier(
        n_estimators=XGB_TREES,
        learning_rate=XGB_LEARNING_RATE,
        max_depth=XGB_MAX_DEPTH,
        min_child_weight=XGB_MIN_CHILD_WEIGHT,
        subsample=XGB_SUBSAMPLE,
        colsample_bytree=XGB_COLSAMPLE,
        reg_alpha=XGB_REG_ALPHA,
        reg_lambda=XGB_REG_LAMBDA,
        objective="binary:logistic",
        eval_metric="logloss",
        tree_method="hist",
        scale_pos_weight=scale_pos_weight,
        n_jobs=-1,
        random_state=RANDOM_STATE,
        verbosity=0,
    )

    print("[INFO] Training...")
    model.fit(X_train, y_train)

    print("[OK] XGBoost training complete.")

    return model


# ============================================================================
# LIGHTGBM REGRESSOR
# ============================================================================

def train_lightgbm(
    X_train: pd.DataFrame,
    y_train: pd.Series,
) -> LGBMRegressor:

    print()
    print("=" * 70)
    print("TRAINING LIGHTGBM REGRESSOR")
    print("=" * 70)

    print(f"[INFO] Trees         : {LGB_TREES}")
    print(f"[INFO] Learning rate : {LGB_LEARNING_RATE}")
    print(f"[INFO] Num leaves    : {LGB_NUM_LEAVES}")

    model = LGBMRegressor(
        n_estimators=LGB_TREES,
        learning_rate=LGB_LEARNING_RATE,
        num_leaves=LGB_NUM_LEAVES,
        max_depth=LGB_MAX_DEPTH,
        min_child_samples=LGB_MIN_CHILD_SAMPLES,
        subsample=LGB_SUBSAMPLE,
        colsample_bytree=LGB_COLSAMPLE,
        objective="regression",
        n_jobs=-1,
        random_state=RANDOM_STATE,
        verbosity=-1,
    )

    print("[INFO] Training...")
    model.fit(X_train, y_train)

    print("[OK] LightGBM training complete.")

    return model


# ============================================================================
# EVALUATION
# ============================================================================

def evaluate_classifier(
    model: XGBClassifier,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> tuple[dict, np.ndarray]:

    print()
    print("=" * 70)
    print("XGBOOST CLASSIFICATION RESULTS")
    print("=" * 70)

    probabilities = model.predict_proba(X_test)[:, 1]

    predictions = (
        probabilities >= CLASSIFICATION_THRESHOLD
    ).astype(np.int8)

    accuracy = accuracy_score(y_test, predictions)
    precision = precision_score(
        y_test,
        predictions,
        zero_division=0,
    )
    recall = recall_score(
        y_test,
        predictions,
        zero_division=0,
    )
    f1 = f1_score(
        y_test,
        predictions,
        zero_division=0,
    )
    auc = roc_auc_score(
        y_test,
        probabilities,
    )

    matrix = confusion_matrix(
        y_test,
        predictions,
    )

    report = classification_report(
        y_test,
        predictions,
        output_dict=True,
        zero_division=0,
    )

    print(f"Accuracy : {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall   : {recall:.4f}")
    print(f"F1 Score : {f1:.4f}")
    print(f"ROC-AUC  : {auc:.4f}")
    print(f"Threshold: {CLASSIFICATION_THRESHOLD:.2f}")

    print()
    print("Confusion Matrix:")
    print(matrix)

    metrics = {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "roc_auc": float(auc),
        "threshold": float(CLASSIFICATION_THRESHOLD),
        "confusion_matrix": matrix.tolist(),
        "classification_report": report,
    }

    return metrics, probabilities


def evaluate_regressor(
    model: LGBMRegressor,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> tuple[dict, np.ndarray]:

    print()
    print("=" * 70)
    print("LIGHTGBM REGRESSION RESULTS")
    print("=" * 70)

    predictions = model.predict(X_test)
    predictions = np.maximum(predictions, 0.0)

    mae = mean_absolute_error(
        y_test,
        predictions,
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_test,
            predictions,
        )
    )

    r2 = r2_score(
        y_test,
        predictions,
    )

    print(f"MAE : {mae:.4f} minutes")
    print(f"RMSE: {rmse:.4f} minutes")
    print(f"R²  : {r2:.4f}")

    metrics = {
        "mae_minutes": float(mae),
        "rmse_minutes": float(rmse),
        "r2": float(r2),
    }

    return metrics, predictions


# ============================================================================
# FEATURE IMPORTANCE
# ============================================================================

def save_feature_importance(
    xgb_model: XGBClassifier,
    lgb_model: LGBMRegressor,
) -> None:

    print()
    print("=" * 70)
    print("FEATURE IMPORTANCE")
    print("=" * 70)

    xgb_df = pd.DataFrame({
        "feature": XGB_FEATURES,
        "xgboost_importance": (
            xgb_model.feature_importances_
        ),
    })

    lgb_df = pd.DataFrame({
        "feature": LGBM_FEATURES,
        "lightgbm_importance": (
            lgb_model.feature_importances_
        ),
    })

    importance = pd.merge(
        xgb_df,
        lgb_df,
        on="feature",
        how="outer",
    ).fillna(0.0)

    importance = importance.sort_values(
        "xgboost_importance",
        ascending=False,
    )

    output_file = ARTIFACT_DIR / "feature_importance.csv"

    importance.to_csv(
        output_file,
        index=False,
    )

    print(f"[OK] Feature importance saved: {output_file}")

    print()
    print("TOP FEATURES")
    print("-" * 70)
    print(
        importance.head(20).to_string(index=False)
    )


# ============================================================================
# TEST PREDICTIONS
# ============================================================================

def decision_from_minutes(minutes: float) -> str:
    if minutes < 15:
        return "NORMAL_WAIT"

    if minutes < 30:
        return "MANUAL_ACTION"

    return "AUTOMATIC_ACTION"


def save_test_predictions(
    test_df: pd.DataFrame,
    xgb_model: XGBClassifier,
    lgb_model: LGBMRegressor,
    XGB_test: pd.DataFrame,
    LGBM_test: pd.DataFrame,
    classification_probabilities: np.ndarray,
    regression_predictions: np.ndarray,
) -> None:

    result = pd.DataFrame({
        "flight_id": test_df["flight_id"].values,
        "flight_datetime": test_df["flight_datetime"].values,
        "actual_delayed_15": (
            test_df[TARGET_CLASSIFICATION].values
        ),
        "actual_delay_minutes": (
            test_df[TARGET_REGRESSION].values
        ),
        "delay_probability": classification_probabilities,
        "predicted_delayed_15": (
            classification_probabilities
            >= CLASSIFICATION_THRESHOLD
        ).astype(np.int8),
        "predicted_delay_minutes": regression_predictions,
    })

    result["delay_probability_percent"] = (
        result["delay_probability"] * 100.0
    )

    result["risk_level"] = result.apply(
        lambda row: (
            "HIGH"
            if row["predicted_delay_minutes"] >= 30
            or row["delay_probability"] >= 0.70
            else (
                "MEDIUM"
                if row["predicted_delay_minutes"] >= 15
                or row["delay_probability"] >= 0.50
                else "LOW"
            )
        ),
        axis=1,
    )

    result["recommended_action"] = (
        result["predicted_delay_minutes"]
        .apply(decision_from_minutes)
    )

    output_file = ARTIFACT_DIR / "test_predictions.parquet"

    result.to_parquet(
        output_file,
        index=False,
        engine="pyarrow",
    )

    print(f"[OK] Test predictions saved: {output_file}")


# ============================================================================
# SAVE JSON
# ============================================================================

def save_json(
    filename: str,
    data: dict,
) -> None:

    output_file = ARTIFACT_DIR / filename

    with open(
        output_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
            default=str,
        )

    print(f"[OK] Saved: {output_file}")


# ============================================================================
# SAVE MODELS + DUAL FEATURE SCHEMA
# ============================================================================

def save_models(
    xgb_model: XGBClassifier,
    lgb_model: LGBMRegressor,
    xgb_encoder: OrdinalEncoder,
    lgb_encoder: OrdinalEncoder,
    metrics: dict,
) -> None:

    print()
    print("=" * 70)
    print("SAVING FINAL MODELS")
    print("=" * 70)

    xgb_file = MODEL_DIR / "xgboost_classifier.pkl"

    with open(xgb_file, "wb") as file:
        pickle.dump(
            xgb_model,
            file,
            protocol=pickle.HIGHEST_PROTOCOL,
        )

    print(f"[OK] XGBoost: {xgb_file}")

    lgb_file = MODEL_DIR / "lightgbm_regressor.pkl"

    with open(lgb_file, "wb") as file:
        pickle.dump(
            lgb_model,
            file,
            protocol=pickle.HIGHEST_PROTOCOL,
        )

    print(f"[OK] LightGBM: {lgb_file}")

    # IMPORTANT:
    # Keep separate encoders because the two models use different
    # feature sets.
    xgb_categorical = [
        c for c in CATEGORICAL_FEATURES
        if c in XGB_FEATURES
    ]

    lgb_categorical = [
        c for c in CATEGORICAL_FEATURES
        if c in LGBM_FEATURES
    ]

    xgb_numerical = [
        c for c in XGB_FEATURES
        if c not in xgb_categorical
    ]

    lgb_numerical = [
        c for c in LGBM_FEATURES
        if c not in lgb_categorical
    ]

    schema = {
        "architecture": "dual_model",
        "xgboost": {
            "feature_columns": XGB_FEATURES,
            "categorical_features": xgb_categorical,
            "numerical_features": xgb_numerical,
            "encoder": xgb_encoder,
        },
        "lightgbm": {
            "feature_columns": LGBM_FEATURES,
            "categorical_features": lgb_categorical,
            "numerical_features": lgb_numerical,
            "encoder": lgb_encoder,
        },
        "master_features": MODEL_FEATURES,
        "classification_target": TARGET_CLASSIFICATION,
        "regression_target": TARGET_REGRESSION,
        "classification_threshold": CLASSIFICATION_THRESHOLD,
        "decision_policy": {
            "normal_wait": "<15 minutes",
            "manual_action": "15-29 minutes",
            "automatic_action": ">=30 minutes",
        },
        "weather": "removed",
        "test_size": TEST_SIZE,
        "split": "chronological",
    }

    schema_file = MODEL_DIR / "feature_schema.pkl"

    with open(schema_file, "wb") as file:
        pickle.dump(
            schema,
            file,
            protocol=pickle.HIGHEST_PROTOCOL,
        )

    print(f"[OK] Feature schema: {schema_file}")

    metadata = {
        "project": "FLITZZ",
        "architecture": "XGBoost classification + LightGBM regression",
        "features": {
            "master": len(MODEL_FEATURES),
            "xgboost": len(XGB_FEATURES),
            "lightgbm": len(LGBM_FEATURES),
        },
        "targets": {
            "classification": TARGET_CLASSIFICATION,
            "regression": TARGET_REGRESSION,
        },
        "training": {
            "total_rows": metrics["data"]["total_rows"],
            "train_rows": metrics["data"]["train_rows"],
            "test_rows": metrics["data"]["test_rows"],
            "test_size": TEST_SIZE,
            "split": "chronological_80_20",
            "random_state": RANDOM_STATE,
        },
        "xgboost": {
            "trees": XGB_TREES,
            "learning_rate": XGB_LEARNING_RATE,
            "max_depth": XGB_MAX_DEPTH,
            "min_child_weight": XGB_MIN_CHILD_WEIGHT,
            "classification_threshold": CLASSIFICATION_THRESHOLD,
        },
        "lightgbm": {
            "trees": LGB_TREES,
            "learning_rate": LGB_LEARNING_RATE,
            "num_leaves": LGB_NUM_LEAVES,
            "max_depth": LGB_MAX_DEPTH,
            "min_child_samples": LGB_MIN_CHILD_SAMPLES,
        },
        "weather": "removed",
        "classification": metrics["classification"],
        "regression": metrics["regression"],
    }

    metadata_file = MODEL_DIR / "model_metadata.json"

    with open(
        metadata_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metadata,
            file,
            indent=2,
            default=str,
        )

    print(f"[OK] Metadata: {metadata_file}")


# ============================================================================
# MAIN
# ============================================================================

def main():

    start_time = time.time()

    print()
    print("=" * 70)
    print("FLITZZ - DUAL MODEL TRAINING")
    print("=" * 70)

    print()
    print("[INFO] XGBoost  -> classification >= 15 min")
    print("[INFO] LightGBM -> regression delay minutes")
    print("[INFO] Split     -> chronological 80/20")
    print("[INFO] Validation set -> NONE")
    print("[INFO] Weather -> REMOVED")

    # ------------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------------

    df = load_dataset()

    # ------------------------------------------------------------------------
    # Feature contract
    # ------------------------------------------------------------------------

    validate_feature_contracts(df)

    # ------------------------------------------------------------------------
    # Targets
    # ------------------------------------------------------------------------

    df = prepare_targets(df)

    # ------------------------------------------------------------------------
    # Split
    # ------------------------------------------------------------------------

    train_df, test_df = chronological_split(df)

    # ------------------------------------------------------------------------
    # Classification targets
    # ------------------------------------------------------------------------

    y_train_classification = (
        train_df[TARGET_CLASSIFICATION]
        .astype(np.int8)
    )

    y_test_classification = (
        test_df[TARGET_CLASSIFICATION]
        .astype(np.int8)
    )

    # ------------------------------------------------------------------------
    # Regression targets
    # ------------------------------------------------------------------------

    y_train_regression = (
        train_df[TARGET_REGRESSION]
        .astype(np.float32)
    )

    y_test_regression = (
        test_df[TARGET_REGRESSION]
        .astype(np.float32)
    )

    # ------------------------------------------------------------------------
    # XGBoost feature preparation
    # ------------------------------------------------------------------------

    (
        XGB_train,
        XGB_test,
        xgb_encoder,
        _,
    ) = prepare_model_features(
        train_df=train_df,
        test_df=test_df,
        feature_columns=XGB_FEATURES,
        model_name="XGBOOST",
    )

    # ------------------------------------------------------------------------
    # LightGBM feature preparation
    # ------------------------------------------------------------------------

    (
        LGBM_train,
        LGBM_test,
        lgb_encoder,
        _,
    ) = prepare_model_features(
        train_df=train_df,
        test_df=test_df,
        feature_columns=LGBM_FEATURES,
        model_name="LIGHTGBM",
    )

    # ------------------------------------------------------------------------
    # Train XGBoost
    # ------------------------------------------------------------------------

    xgb_model = train_xgboost(
        XGB_train,
        y_train_classification,
    )

    # ------------------------------------------------------------------------
    # Train LightGBM
    # ------------------------------------------------------------------------

    lgb_model = train_lightgbm(
        LGBM_train,
        y_train_regression,
    )

    # ------------------------------------------------------------------------
    # Evaluate
    # ------------------------------------------------------------------------

    classification_metrics, classification_probabilities = (
        evaluate_classifier(
            xgb_model,
            XGB_test,
            y_test_classification,
        )
    )

    regression_metrics, regression_predictions = (
        evaluate_regressor(
            lgb_model,
            LGBM_test,
            y_test_regression,
        )
    )

    # ------------------------------------------------------------------------
    # Feature importance
    # ------------------------------------------------------------------------

    save_feature_importance(
        xgb_model=xgb_model,
        lgb_model=lgb_model,
    )

    # ------------------------------------------------------------------------
    # Test predictions
    # ------------------------------------------------------------------------

    save_test_predictions(
        test_df=test_df,
        xgb_model=xgb_model,
        lgb_model=lgb_model,
        XGB_test=XGB_test,
        LGBM_test=LGBM_test,
        classification_probabilities=classification_probabilities,
        regression_predictions=regression_predictions,
    )

    # ------------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------------

    metrics = {
        "data": {
            "total_rows": int(len(df)),
            "train_rows": int(len(train_df)),
            "test_rows": int(len(test_df)),
            "xgboost_features": int(len(XGB_FEATURES)),
            "lightgbm_features": int(len(LGBM_FEATURES)),
            "master_features": int(len(MODEL_FEATURES)),
        },
        "classification": classification_metrics,
        "regression": regression_metrics,
    }

    save_json(
        "metrics.json",
        metrics,
    )

    save_json(
        "classification_report.json",
        classification_metrics["classification_report"],
    )

    save_json(
        "regression_metrics.json",
        regression_metrics,
    )

    # ------------------------------------------------------------------------
    # Save models
    # ------------------------------------------------------------------------

    save_models(
        xgb_model=xgb_model,
        lgb_model=lgb_model,
        xgb_encoder=xgb_encoder,
        lgb_encoder=lgb_encoder,
        metrics=metrics,
    )

    # ------------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------------

    elapsed = time.time() - start_time

    print()
    print("=" * 70)
    print("FLITZZ DUAL MODEL TRAINING COMPLETE")
    print("=" * 70)

    print()
    print("DATA")
    print("-" * 70)
    print(f"Total rows        : {len(df):,}")
    print(f"Training rows     : {len(train_df):,}")
    print(f"Test rows         : {len(test_df):,}")
    print(f"XGBoost features  : {len(XGB_FEATURES)}")
    print(f"LightGBM features : {len(LGBM_FEATURES)}")
    print("Split             : 80% train / 20% test")
    print("Validation        : NONE")
    print("Weather           : REMOVED")

    print()
    print("XGBOOST CLASSIFICATION")
    print("-" * 70)
    print(f"Accuracy : {classification_metrics['accuracy']:.4f}")
    print(f"Precision: {classification_metrics['precision']:.4f}")
    print(f"Recall   : {classification_metrics['recall']:.4f}")
    print(f"F1 Score : {classification_metrics['f1_score']:.4f}")
    print(f"ROC-AUC  : {classification_metrics['roc_auc']:.4f}")
    print(f"Threshold: {classification_metrics['threshold']:.2f}")

    print()
    print("LIGHTGBM REGRESSION")
    print("-" * 70)
    print(f"MAE : {regression_metrics['mae_minutes']:.4f} min")
    print(f"RMSE: {regression_metrics['rmse_minutes']:.4f} min")
    print(f"R²  : {regression_metrics['r2']:.4f}")

    print()
    print("MODEL FILES")
    print("-" * 70)
    print(MODEL_DIR / "xgboost_classifier.pkl")
    print(MODEL_DIR / "lightgbm_regressor.pkl")
    print(MODEL_DIR / "feature_schema.pkl")
    print(MODEL_DIR / "model_metadata.json")

    print()
    print(f"Training time: {elapsed:.2f} seconds")

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()