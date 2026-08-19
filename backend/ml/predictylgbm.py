"""
FLITZZ - UNIFIED LIVE PREDICTION

FLOW
----
Frontend
    ↓
FastAPI
    ↓
Feature Engineering
    ↓
    ├── XGBoost Classification
    │       ↓
    │   P(delay >= 15 min)
    │
    └── LightGBM Regression
            ↓
        SINGLE BEST MODEL
            ↓
        predicted delay minutes
    ↓
Risk / Decision
    ↓
Frontend

CLASSIFICATION
--------------
Uses:
    xgboost_classifier.pkl

REGRESSION
----------
Uses ONLY:
    flight_delay_single_best.pkl

The regression pickle contains:
    model
    best_fold_number
    best_fold_mae
    global_mean
    lookup_priors
    final_features
    cat_targets

WEATHER
-------
Completely excluded.
"""

from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MODEL_DIR = BASE_DIR / "models"

XGB_MODEL_PATH = (
    MODEL_DIR / "xgboost_classifier.pkl"
)

XGB_SCHEMA_PATH = (
    MODEL_DIR / "feature_schema.pkl"
)

REGRESSION_MODEL_PATH = (
    MODEL_DIR / "flight_delay_champion.pkl"
)


# ============================================================
# BUSINESS RULES
# ============================================================

DELAY_THRESHOLD = 15.0

MANUAL_ACTION_THRESHOLD = 30.0

HIGH_DELAY_THRESHOLD = 45.0


# ============================================================
# REGRESSION FEATURES
# ============================================================

REGRESSION_FEATURES = [

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


REGRESSION_CATEGORICAL = [

    "AIRLINE",
    "ORIGIN_AIRPORT",
    "DESTINATION_AIRPORT",
    "ROUTE",
]


# ============================================================
# PREDICTOR
# ============================================================

class FlightPredictor:

    def __init__(self):

        print("=" * 70)
        print("FLITZZ MODEL LOADING")
        print("=" * 70)

        # ====================================================
        # XGBOOST
        # ====================================================

        self.xgb_model = self._load(
            XGB_MODEL_PATH
        )

        self.xgb_schema = self._load(
            XGB_SCHEMA_PATH
        )

        self._load_xgb_schema()

        # ====================================================
        # LIGHTGBM CHAMPION
        # ====================================================

        self.regression_artifact = self._load(
            REGRESSION_MODEL_PATH
        )

        self.regression_model = (
            self.regression_artifact["model"]
        )

        self.best_fold_number = (
            self.regression_artifact[
                "best_fold_number"
            ]
        )

        self.best_fold_mae = (
            self.regression_artifact[
                "best_fold_mae"
            ]
        )

        self.global_mean = (
            self.regression_artifact[
                "global_mean"
            ]
        )

        self.lookup_priors = (
            self.regression_artifact[
                "lookup_priors"
            ]
        )

        self.regression_features = list(
            self.regression_artifact[
                "final_features"
            ]
        )

        self.regression_cat_targets = list(
            self.regression_artifact[
                "cat_targets"
            ]
        )

        self._validate_regression_model()

        print()
        print(
            "[OK] XGBoost classifier loaded"
        )

        print(
            f"[OK] XGBoost features: "
            f"{len(self.xgb_features)}"
        )

        print(
            "[OK] LightGBM champion loaded"
        )

        print(
            f"[OK] Champion fold: "
            f"{self.best_fold_number}"
        )

        print(
            f"[OK] Champion MAE: "
            f"{self.best_fold_mae:.4f} min"
        )

        print(
            f"[OK] LightGBM features: "
            f"{len(self.regression_features)}"
        )

        print(
            "[OK] Weather: REMOVED"
        )

        print("=" * 70)

    # ========================================================
    # LOAD
    # ========================================================

    @staticmethod
    def _load(path):

        if not path.exists():

            raise FileNotFoundError(
                f"Model file not found:\n{path}"
            )

        return joblib.load(path)

    # ========================================================
    # XGBOOST SCHEMA
    # ========================================================

    def _load_xgb_schema(self):

        # New dual-schema format
        if (
            isinstance(
                self.xgb_schema,
                dict,
            )
            and "xgboost"
            in self.xgb_schema
        ):

            config = (
                self.xgb_schema[
                    "xgboost"
                ]
            )

            self.xgb_features = list(
                config[
                    "feature_columns"
                ]
            )

            self.xgb_categorical = list(
                config.get(
                    "categorical_features",
                    [],
                )
            )

            self.xgb_encoder = (
                config.get(
                    "encoder"
                )
            )

            self.xgb_medians = (
                config.get(
                    "numerical_medians",
                    {},
                )
            )

            return

        # Old schema compatibility
        self.xgb_features = list(
            self.xgb_schema.get(
                "feature_columns",
                [],
            )
        )

        self.xgb_categorical = list(
            self.xgb_schema.get(
                "categorical_features",
                [],
            )
        )

        self.xgb_encoder = (
            self.xgb_schema.get(
                "encoder"
            )
        )

        self.xgb_medians = (
            self.xgb_schema.get(
                "numerical_medians",
                {},
            )
        )

    # ========================================================
    # VALIDATE REGRESSION
    # ========================================================

    def _validate_regression_model(self):

        if (
            len(
                self.regression_features
            )
            != 17
        ):

            raise RuntimeError(
                "The champion LightGBM model "
                "must contain exactly 17 features. "
                f"Found: "
                f"{len(self.regression_features)}"
            )

        missing = [

            feature

            for feature
            in REGRESSION_FEATURES

            if feature
            not in self.regression_features
        ]

        if missing:

            raise RuntimeError(
                "Champion LightGBM artifact is "
                f"missing features: {missing}"
            )

        missing_cat = [

            feature

            for feature
            in REGRESSION_CATEGORICAL

            if feature
            not in self.regression_cat_targets
        ]

        if missing_cat:

            raise RuntimeError(
                "Champion LightGBM artifact is "
                f"missing categorical targets: "
                f"{missing_cat}"
            )

    # ========================================================
    # XGBOOST FEATURE PREPARATION
    # ========================================================

    def prepare_xgb_features(
        self,
        features: dict,
    ) -> pd.DataFrame:

        row = pd.DataFrame(
            [features]
        )

        # ----------------------------------------------------
        # Required columns
        # ----------------------------------------------------

        for column in self.xgb_features:

            if column not in row.columns:

                row[column] = np.nan

        row = row[
            self.xgb_features
        ].copy()

        # ----------------------------------------------------
        # Categorical
        # ----------------------------------------------------

        for column in self.xgb_categorical:

            row[column] = (

                row[column]

                .fillna("UNKNOWN")

                .astype(str)
            )

        # ----------------------------------------------------
        # Numerical
        # ----------------------------------------------------

        numerical = [

            column

            for column
            in self.xgb_features

            if column
            not in self.xgb_categorical
        ]

        for column in numerical:

            row[column] = pd.to_numeric(
                row[column],
                errors="coerce",
            )

            row[column] = (
                row[column]
                .replace(
                    [
                        np.inf,
                        -np.inf,
                    ],
                    np.nan,
                )
            )

            fallback = (
                self.xgb_medians.get(
                    column,
                    0.0,
                )
            )

            if (
                fallback is None
                or pd.isna(fallback)
            ):

                fallback = 0.0

            row[column] = (
                row[column]
                .fillna(
                    float(fallback)
                )
            )

        # ----------------------------------------------------
        # Encoder
        # ----------------------------------------------------

        if self.xgb_categorical:

            if self.xgb_encoder is None:

                raise RuntimeError(
                    "XGBoost categorical encoder "
                    "was not found."
                )

            row[
                self.xgb_categorical
            ] = self.xgb_encoder.transform(
                row[
                    self.xgb_categorical
                ]
            )

        return row.astype(
            np.float32
        )

    # ========================================================
    # XGBOOST PREDICTION
    # ========================================================

    def predict_classification(
        self,
        features: dict,
    ) -> dict:

        X = self.prepare_xgb_features(
            features
        )

        probability = float(
            self.xgb_model
            .predict_proba(
                X
            )[0][1]
        )

        probability = min(
            max(
                probability,
                0.0,
            ),
            1.0,
        )

        delayed = (
            probability >= 0.50
        )

        if probability >= 0.70:

            probability_risk = (
                "VERY_HIGH"
            )

        elif probability >= 0.50:

            probability_risk = (
                "HIGH"
            )

        elif probability >= 0.30:

            probability_risk = (
                "MEDIUM"
            )

        else:

            probability_risk = (
                "LOW"
            )

        return {

            "delay_probability": round(
                probability,
                4,
            ),

            "delay_probability_percent": round(
                probability * 100.0,
                2,
            ),

            "delayed_15": bool(
                delayed
            ),

            "classification_status": (
                "DELAYED"
                if delayed
                else "NOT_DELAYED"
            ),

            "probability_risk": (
                probability_risk
            ),
        }

    # ========================================================
    # REGRESSION FEATURE PREPARATION
    # ========================================================

    def prepare_regression_features(
        self,
        features: dict,
    ) -> pd.DataFrame:

        row = pd.DataFrame(
            [features]
        )

        # ----------------------------------------------------
        # Normalize categorical values
        # ----------------------------------------------------

        for column in (
            self.regression_cat_targets
        ):

            if column not in row.columns:

                row[column] = "UNKNOWN"

            row[column] = (

                row[column]

                .fillna("UNKNOWN")

                .astype(str)
            )

        # ----------------------------------------------------
        # Historical priors
        # ----------------------------------------------------

        for column in (
            self.regression_cat_targets
        ):

            prior_map = (
                self.lookup_priors.get(
                    column,
                    {},
                )
            )

            value = str(
                row[
                    column
                ].iloc[0]
            )

            historical_delay = (
                prior_map.get(
                    value,
                    self.global_mean,
                )
            )

            row[
                f"{column}_HIST_DELAY"
            ] = float(
                historical_delay
            )

        # ----------------------------------------------------
        # Add missing model columns
        # ----------------------------------------------------

        for column in (
            self.regression_features
        ):

            if column not in row.columns:

                row[column] = np.nan

        row = row[
            self.regression_features
        ].copy()

        # ----------------------------------------------------
        # Numeric
        # ----------------------------------------------------

        numerical = [

            column

            for column
            in self.regression_features

            if column
            not in self.regression_cat_targets
        ]

        for column in numerical:

            row[column] = pd.to_numeric(
                row[column],
                errors="coerce",
            )

            row[column] = (
                row[column]
                .replace(
                    [
                        np.inf,
                        -np.inf,
                    ],
                    np.nan,
                )
                .fillna(0.0)
            )

        # ----------------------------------------------------
        # Categorical
        # ----------------------------------------------------

        for column in (
            self.regression_cat_targets
        ):

            row[column] = (
                row[column]
                .fillna("UNKNOWN")
                .astype("category")
            )

        return row

    # ========================================================
    # LIGHTGBM CHAMPION PREDICTION
    # ========================================================

    def predict_regression(
        self,
        features: dict,
    ) -> dict:

        row = (
            self.prepare_regression_features(
                features
            )
        )

        # IMPORTANT:
        # Only ONE champion model is used.
        predicted_delay = float(
            self.regression_model.predict(
                row
            )[0]
        )

        # Delay cannot be negative.
        predicted_delay = max(
            0.0,
            predicted_delay,
        )

        # ----------------------------------------------------
        # Status
        # ----------------------------------------------------

        if predicted_delay > 15:

            status = "Delayed"

        elif predicted_delay >= -5:

            status = "On-Time"

        else:

            status = "Early"

        # ----------------------------------------------------
        # Risk
        # ----------------------------------------------------

        if predicted_delay > 45:

            risk_level = "Critical"

        elif predicted_delay > 30:

            risk_level = "High"

        elif predicted_delay > 15:

            risk_level = "Moderate"

        else:

            risk_level = "Low"

        # ----------------------------------------------------
        # Decision
        # ----------------------------------------------------

        if predicted_delay >= 30:

            action = (
                "AUTOMATIC_ACTION"
            )

        elif predicted_delay >= 15:

            action = (
                "MANUAL_ACTION"
            )

        else:

            action = (
                "NORMAL_WAIT"
            )

        return {

            "predicted_arrival_delay_minutes":
                round(
                    predicted_delay,
                    2,
                ),

            "delay_status":
                status,

            "risk_level":
                risk_level,

            "recommended_action":
                action,

            "model": {

                "type":
                    "LightGBM",

                "mode":
                    "single_best_model",

                "best_fold":
                    self.best_fold_number,

                "best_fold_mae":
                    round(
                        float(
                            self.best_fold_mae
                        ),
                        4,
                    ),

                "feature_count":
                    len(
                        self.regression_features
                    ),
            },
        }

    # ========================================================
    # COMPLETE PREDICTION
    # ========================================================

    def predict(
        self,
        features: dict,
    ) -> dict:

        classification = (
            self.predict_classification(
                features
            )
        )

        regression = (
            self.predict_regression(
                features
            )
        )

        probability = (
            classification[
                "delay_probability"
            ]
        )

        predicted_minutes = (
            regression[
                "predicted_arrival_delay_minutes"
            ]
        )

        # ----------------------------------------------------
        # Combined risk
        # ----------------------------------------------------

        if (
            predicted_minutes >= 45
            or probability >= 0.70
        ):

            combined_risk = "CRITICAL"

        elif (
            predicted_minutes >= 30
            or probability >= 0.50
        ):

            combined_risk = "HIGH"

        elif (
            predicted_minutes >= 15
            or probability >= 0.30
        ):

            combined_risk = "MEDIUM"

        else:

            combined_risk = "LOW"

        # ----------------------------------------------------
        # Final response
        # ----------------------------------------------------

        return {

            "classification":
                classification,

            "regression":
                regression,

            "combined_risk":
                combined_risk,

            "model_info": {

                "classification":
                    "XGBoost",

                "regression":
                    "LightGBM",

                "regression_mode":
                    "Single Best Fold",

                "weather_used":
                    False,
            },
        }


# ============================================================
# SINGLETON
# ============================================================

_predictor: Optional[
    FlightPredictor
] = None


def get_predictor():

    global _predictor

    if _predictor is None:

        _predictor = FlightPredictor()

    return _predictor


# ============================================================
# FASTAPI HELPER
# ============================================================

def predict_flight(
    features: dict,
):

    predictor = get_predictor()

    return predictor.predict(
        features
    )