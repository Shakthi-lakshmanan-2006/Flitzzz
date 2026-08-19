"""
FLITZZ - LIVE PREDICTION

DUAL MODEL PREDICTION
=====================

XGBoost:
    Predicts probability that arrival delay >= 15 minutes.

LightGBM:
    Predicts estimated arrival delay in minutes.

Feature contracts:
    XGBoost  -> 24 features
    LightGBM -> 34 features

The predictor also exposes the model evaluation metrics saved by train.py:
    Classification:
        accuracy
        precision
        recall
        f1
        ROC-AUC

    Regression:
        MAE
        RMSE
        R²

IMPORTANT
---------
These evaluation metrics describe the trained model on the final test set.
They are NOT recalculated for an individual live flight.

Weather is completely excluded.
"""

from __future__ import annotations

from pathlib import Path
import json
import pickle

import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
ARTIFACT_DIR = BASE_DIR / "artifacts"

XGB_MODEL_PATH = MODEL_DIR / "xgboost_classifier.pkl"
LGB_MODEL_PATH = MODEL_DIR / "lightgbm_regressor.pkl"
SCHEMA_PATH = MODEL_DIR / "feature_schema.pkl"

METRICS_PATH = ARTIFACT_DIR / "metrics.json"
METADATA_PATH = MODEL_DIR / "model_metadata.json"


# ============================================================
# BUSINESS THRESHOLDS
# ============================================================

DELAY_TARGET_MINUTES = 15.0

DEFAULT_CLASSIFICATION_THRESHOLD = 0.50

NORMAL_DELAY_MAX = 15.0
MANUAL_ACTION_MAX = 30.0

LOW_RISK_THRESHOLD = 0.30
HIGH_RISK_THRESHOLD = 0.50
VERY_HIGH_RISK_THRESHOLD = 0.70


# ============================================================
# WEATHER BLOCKLIST
# ============================================================

WEATHER_KEYWORDS = [
    "weather",
    "temperature",
    "temp",
    "humidity",
    "wind",
    "wind_speed",
    "wind_direction",
    "precipitation",
    "rain",
    "snow",
    "visibility",
    "pressure",
    "cloud",
    "dew_point",
    "heat_index",
    "storm",
    "condition",
]


class FlightPredictor:

    # ========================================================
    # INIT
    # ========================================================

    def __init__(self):

        print("[INFO] Loading FLITZZ models...")

        self.xgb_model = self._load(XGB_MODEL_PATH)
        self.lgb_model = self._load(LGB_MODEL_PATH)
        self.schema = self._load(SCHEMA_PATH)

        # ----------------------------------------------------
        # Dual-model schema
        # ----------------------------------------------------

        if "xgboost" not in self.schema:
            raise RuntimeError(
                "feature_schema.pkl does not contain the new "
                "dual-model XGBoost schema. Retrain using updated train.py."
            )

        if "lightgbm" not in self.schema:
            raise RuntimeError(
                "feature_schema.pkl does not contain the new "
                "dual-model LightGBM schema. Retrain using updated train.py."
            )

        self.xgb_schema = self.schema["xgboost"]
        self.lgb_schema = self.schema["lightgbm"]

        self.xgb_features = list(
            self.xgb_schema["feature_columns"]
        )

        self.lgb_features = list(
            self.lgb_schema["feature_columns"]
        )

        self.xgb_categorical = list(
            self.xgb_schema.get(
                "categorical_features",
                [],
            )
        )

        self.lgb_categorical = list(
            self.lgb_schema.get(
                "categorical_features",
                [],
            )
        )

        self.xgb_numerical = list(
            self.xgb_schema.get(
                "numerical_features",
                [
                    c
                    for c in self.xgb_features
                    if c not in self.xgb_categorical
                ],
            )
        )

        self.lgb_numerical = list(
            self.lgb_schema.get(
                "numerical_features",
                [
                    c
                    for c in self.lgb_features
                    if c not in self.lgb_categorical
                ],
            )
        )

        self.xgb_encoder = self.xgb_schema.get("encoder")
        self.lgb_encoder = self.lgb_schema.get("encoder")

        self.xgb_medians = self.xgb_schema.get(
            "numerical_medians",
            {},
        )

        self.lgb_medians = self.lgb_schema.get(
            "numerical_medians",
            {},
        )

        self.classification_threshold = float(
            self.schema.get(
                "classification_threshold",
                DEFAULT_CLASSIFICATION_THRESHOLD,
            )
        )

        # ----------------------------------------------------
        # Validate model contracts
        # ----------------------------------------------------

        if len(self.xgb_features) != 24:
            raise RuntimeError(
                "XGBoost must use exactly 24 features. "
                f"Found {len(self.xgb_features)}."
            )

        if len(self.lgb_features) != 34:
            raise RuntimeError(
                "LightGBM must use exactly 34 features. "
                f"Found {len(self.lgb_features)}."
            )

        self._validate_no_weather(
            self.xgb_features,
            "XGBoost",
        )

        self._validate_no_weather(
            self.lgb_features,
            "LightGBM",
        )

        # ----------------------------------------------------
        # Load evaluation metrics
        # ----------------------------------------------------

        self.metrics = self._load_metrics()
        self.metadata = self._load_metadata()

        print(
            f"[OK] XGBoost features : {len(self.xgb_features)}"
        )

        print(
            f"[OK] LightGBM features: {len(self.lgb_features)}"
        )

        print(
            f"[OK] Classification threshold: "
            f"{self.classification_threshold:.2f}"
        )

        print("[OK] Weather: REMOVED")
        print("[OK] XGBoost model loaded.")
        print("[OK] LightGBM model loaded.")

        if self.metrics:
            print("[OK] Evaluation metrics loaded.")

    # ========================================================
    # LOAD PICKLE
    # ========================================================

    @staticmethod
    def _load(path: Path):

        if not path.exists():
            raise FileNotFoundError(
                f"Required model file not found: {path}\n"
                "Run the updated train.py first."
            )

        with open(
            path,
            "rb",
        ) as file:
            return pickle.load(file)

    # ========================================================
    # LOAD METRICS
    # ========================================================

    @staticmethod
    def _load_json(
        path: Path,
    ) -> dict:

        if not path.exists():
            return {}

        try:
            with open(
                path,
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            return data if isinstance(data, dict) else {}

        except Exception:
            return {}

    def _load_metrics(self) -> dict:
        return self._load_json(
            METRICS_PATH
        )

    def _load_metadata(self) -> dict:
        return self._load_json(
            METADATA_PATH
        )

    # ========================================================
    # WEATHER SAFETY
    # ========================================================

    @staticmethod
    def _is_weather_column(
        column: str,
    ) -> bool:

        name = str(column).lower().strip()

        return any(
            keyword in name
            for keyword in WEATHER_KEYWORDS
        )

    @classmethod
    def _validate_no_weather(
        cls,
        columns: list[str],
        model_name: str,
    ) -> None:

        weather_features = [
            column
            for column in columns
            if cls._is_weather_column(column)
        ]

        if weather_features:
            raise RuntimeError(
                f"{model_name} contains weather features: "
                + ", ".join(weather_features)
            )

    # ========================================================
    # INPUT VALIDATION
    # ========================================================

    def _validate_input(
        self,
        features: dict,
    ) -> None:

        if not isinstance(
            features,
            dict,
        ):
            raise TypeError(
                "features must be a dictionary."
            )

        weather_input = [
            key
            for key in features
            if self._is_weather_column(key)
        ]

        if weather_input:
            raise ValueError(
                "Weather data is not supported by FLITZZ. "
                "Remove: "
                + ", ".join(weather_input)
            )

    # ========================================================
    # PREPARE ONE MODEL'S FEATURES
    # ========================================================

    def _prepare_model_features(
        self,
        features: dict,
        feature_columns: list[str],
        categorical_features: list[str],
        numerical_features: list[str],
        encoder,
        numerical_medians: dict,
        model_name: str,
    ) -> pd.DataFrame:
        """
        Build the exact matrix expected by one model.

        XGBoost and LightGBM intentionally use separate matrices.
        """

        df = pd.DataFrame(
            [features]
        )

        # ----------------------------------------------------
        # Ensure all required columns exist
        # ----------------------------------------------------

        for column in feature_columns:
            if column not in df.columns:
                df[column] = np.nan

        # Keep exact model order.
        df = df[
            feature_columns
        ].copy()

        # ----------------------------------------------------
        # Categorical features
        # ----------------------------------------------------

        for column in categorical_features:
            df[column] = (
                df[column]
                .fillna("UNKNOWN")
                .astype(str)
            )

        # ----------------------------------------------------
        # Numerical features
        # ----------------------------------------------------

        for column in numerical_features:

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
            )

            fallback = numerical_medians.get(
                column,
                0.0,
            )

            if fallback is None or pd.isna(fallback):
                fallback = 0.0

            df[column] = df[column].fillna(
                float(fallback)
            )

        # ----------------------------------------------------
        # Saved training encoder
        # ----------------------------------------------------

        if categorical_features:

            if encoder is None:
                raise RuntimeError(
                    f"{model_name} has categorical features but "
                    "no saved encoder was found."
                )

            df[categorical_features] = (
                encoder.transform(
                    df[categorical_features]
                )
            )

        # ----------------------------------------------------
        # Final matrix
        # ----------------------------------------------------

        result = df.astype(
            np.float32
        )

        if result.isna().any().any():
            raise RuntimeError(
                f"{model_name} still contains NaN values."
            )

        return result

    # ========================================================
    # PREPARE BOTH MODELS
    # ========================================================

    def prepare_features(
        self,
        features: dict,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:

        self._validate_input(
            features
        )

        X_xgb = self._prepare_model_features(
            features=features,
            feature_columns=self.xgb_features,
            categorical_features=self.xgb_categorical,
            numerical_features=self.xgb_numerical,
            encoder=self.xgb_encoder,
            numerical_medians=self.xgb_medians,
            model_name="XGBoost",
        )

        X_lgb = self._prepare_model_features(
            features=features,
            feature_columns=self.lgb_features,
            categorical_features=self.lgb_categorical,
            numerical_features=self.lgb_numerical,
            encoder=self.lgb_encoder,
            numerical_medians=self.lgb_medians,
            model_name="LightGBM",
        )

        return X_xgb, X_lgb

    # ========================================================
    # RISK
    # ========================================================

    @staticmethod
    def classify_probability_risk(
        probability: float,
    ) -> str:

        if probability < LOW_RISK_THRESHOLD:
            return "LOW"

        if probability < HIGH_RISK_THRESHOLD:
            return "MEDIUM"

        if probability < VERY_HIGH_RISK_THRESHOLD:
            return "HIGH"

        return "VERY_HIGH"

    # ========================================================
    # DELAY STATUS
    # ========================================================

    def classify_delay_status(
        self,
        probability: float,
    ) -> str:

        if probability >= self.classification_threshold:
            return "DELAYED"

        return "NOT_DELAYED"

    # ========================================================
    # DELAY SEVERITY
    # ========================================================

    @staticmethod
    def classify_delay_severity(
        predicted_minutes: float,
    ) -> str:

        if predicted_minutes < NORMAL_DELAY_MAX:
            return "NORMAL"

        if predicted_minutes < MANUAL_ACTION_MAX:
            return "MODERATE"

        return "SEVERE"

    # ========================================================
    # OPERATIONAL ACTION
    # ========================================================

    @staticmethod
    def classify_recommended_action(
        predicted_minutes: float,
    ) -> str:

        if predicted_minutes < NORMAL_DELAY_MAX:
            return "NORMAL_WAIT"

        if predicted_minutes < MANUAL_ACTION_MAX:
            return "MANUAL_ACTION"

        return "AUTOMATIC_ACTION"

    # ========================================================
    # COMBINED RISK
    # ========================================================

    @staticmethod
    def classify_combined_risk(
        probability: float,
        predicted_minutes: float,
    ) -> str:

        if (
            predicted_minutes >= 30
            or probability >= 0.70
        ):
            return "CRITICAL"

        if (
            predicted_minutes >= 15
            or probability >= 0.50
        ):
            return "HIGH"

        if (
            predicted_minutes >= 10
            or probability >= 0.30
        ):
            return "MEDIUM"

        return "LOW"

    # ========================================================
    # MODEL EVALUATION METRICS
    # ========================================================

    def get_evaluation_metrics(self) -> dict:
        """
        Return the final test-set evaluation metrics generated by train.py.

        These metrics describe the trained models overall.
        They are NOT metrics for the current individual flight.
        """

        classification = self.metrics.get(
            "classification",
            {},
        )

        regression = self.metrics.get(
            "regression",
            {},
        )

        return {
            "classification": {
                "accuracy": classification.get(
                    "accuracy"
                ),
                "precision": classification.get(
                    "precision"
                ),
                "recall": classification.get(
                    "recall"
                ),
                "f1_score": classification.get(
                    "f1_score"
                ),
                "roc_auc": classification.get(
                    "roc_auc"
                ),
                "threshold": classification.get(
                    "threshold",
                    self.classification_threshold,
                ),
            },
            "regression": {
                "mae_minutes": regression.get(
                    "mae_minutes"
                ),
                "rmse_minutes": regression.get(
                    "rmse_minutes"
                ),
                "r2": regression.get(
                    "r2"
                ),
            },
        }

    # ========================================================
    # PREDICT
    # ========================================================

    def predict(
        self,
        features: dict,
    ) -> dict:
        """
        Complete FLITZZ live prediction.

        Returns:
            Individual flight prediction
            +
            trained-model evaluation metrics
        """

        X_xgb, X_lgb = self.prepare_features(
            features
        )

        # ----------------------------------------------------
        # XGBoost classification
        # ----------------------------------------------------

        delay_probability = float(
            self.xgb_model
            .predict_proba(X_xgb)[0][1]
        )

        delay_probability = min(
            max(
                delay_probability,
                0.0,
            ),
            1.0,
        )

        delayed_15 = (
            delay_probability
            >= self.classification_threshold
        )

        delay_status = self.classify_delay_status(
            delay_probability
        )

        probability_risk = (
            self.classify_probability_risk(
                delay_probability
            )
        )

        # ----------------------------------------------------
        # LightGBM regression
        # ----------------------------------------------------

        predicted_minutes = float(
            self.lgb_model
            .predict(X_lgb)[0]
        )

        # Delay cannot be negative.
        predicted_minutes = max(
            0.0,
            predicted_minutes,
        )

        delay_severity = (
            self.classify_delay_severity(
                predicted_minutes
            )
        )

        recommended_action = (
            self.classify_recommended_action(
                predicted_minutes
            )
        )

        combined_risk = (
            self.classify_combined_risk(
                delay_probability,
                predicted_minutes,
            )
        )

        # ----------------------------------------------------
        # Evaluation metrics
        # ----------------------------------------------------

        evaluation = self.get_evaluation_metrics()

        # ----------------------------------------------------
        # Final response
        # ----------------------------------------------------

        return {

            # =================================================
            # LIVE CLASSIFICATION
            # =================================================

            "prediction": {
                "delay_probability": round(
                    delay_probability,
                    4,
                ),

                "delay_probability_percent": round(
                    delay_probability * 100.0,
                    2,
                ),

                "delayed_15": bool(
                    delayed_15
                ),

                "delay_status": delay_status,
            },

            # =================================================
            # LIVE REGRESSION
            # =================================================

            "delay_estimation": {
                "predicted_delay_minutes": round(
                    predicted_minutes,
                    2,
                ),

                "delay_target_minutes": (
                    DELAY_TARGET_MINUTES
                ),

                "delay_range": (
                    "<15"
                    if predicted_minutes < 15
                    else "15-29"
                    if predicted_minutes < 30
                    else ">=30"
                ),

                "severity": delay_severity,
            },

            # =================================================
            # OPERATIONAL RISK
            # =================================================

            "risk": {
                "probability_risk": probability_risk,
                "combined_risk": combined_risk,
            },

            # =================================================
            # ACTION
            # =================================================

            "decision": {
                "recommended_action": (
                    recommended_action
                ),
            },

            # =================================================
            # MODEL EVALUATION
            # =================================================

            "model_evaluation": {
                "classification": {
                    "model": "XGBoost",
                    "features": len(
                        self.xgb_features
                    ),
                    "accuracy": evaluation[
                        "classification"
                    ]["accuracy"],
                    "precision": evaluation[
                        "classification"
                    ]["precision"],
                    "recall": evaluation[
                        "classification"
                    ]["recall"],
                    "f1_score": evaluation[
                        "classification"
                    ]["f1_score"],
                    "roc_auc": evaluation[
                        "classification"
                    ]["roc_auc"],
                    "threshold": evaluation[
                        "classification"
                    ]["threshold"],
                },

                "regression": {
                    "model": "LightGBM",
                    "features": len(
                        self.lgb_features
                    ),
                    "mae_minutes": evaluation[
                        "regression"
                    ]["mae_minutes"],
                    "rmse_minutes": evaluation[
                        "regression"
                    ]["rmse_minutes"],
                    "r2": evaluation[
                        "regression"
                    ]["r2"],
                },
            },

            # =================================================
            # MODEL / SYSTEM INFO
            # =================================================

            "model_info": {
                "classification_model": "XGBoost",
                "regression_model": "LightGBM",
                "xgboost_feature_count": len(
                    self.xgb_features
                ),
                "lightgbm_feature_count": len(
                    self.lgb_features
                ),
                "weather_used": False,
                "classification_threshold": (
                    self.classification_threshold
                ),
            },
        }


# ============================================================
# SINGLETON
# ============================================================

_predictor = None


def get_predictor() -> FlightPredictor:

    global _predictor

    if _predictor is None:
        _predictor = FlightPredictor()

    return _predictor


# ============================================================
# FASTAPI FUNCTION
# ============================================================

def predict_flight(
    features: dict,
) -> dict:

    predictor = get_predictor()

    return predictor.predict(
        features
    )


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("FLITZZ LIVE PREDICTION")
    print("=" * 70)

    predictor = get_predictor()

    print()
    print("XGBoost features:")
    for feature in predictor.xgb_features:
        print(f"  - {feature}")

    print()
    print("LightGBM features:")
    for feature in predictor.lgb_features:
        print(f"  - {feature}")

    print()
    print("MODEL EVALUATION")
    print("-" * 70)

    evaluation = predictor.get_evaluation_metrics()

    print("XGBoost")
    print(
        f"  Accuracy : "
        f"{evaluation['classification']['accuracy']}"
    )
    print(
        f"  Precision: "
        f"{evaluation['classification']['precision']}"
    )
    print(
        f"  Recall   : "
        f"{evaluation['classification']['recall']}"
    )
    print(
        f"  F1 Score : "
        f"{evaluation['classification']['f1_score']}"
    )
    print(
        f"  ROC-AUC  : "
        f"{evaluation['classification']['roc_auc']}"
    )

    print()
    print("LightGBM")
    print(
        f"  MAE : "
        f"{evaluation['regression']['mae_minutes']}"
    )
    print(
        f"  RMSE: "
        f"{evaluation['regression']['rmse_minutes']}"
    )
    print(
        f"  R²  : "
        f"{evaluation['regression']['r2']}"
    )

    print()
    print(
        "[INFO] Use predict_flight(features) "
        "from FastAPI."
    )