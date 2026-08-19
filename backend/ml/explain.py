"""
FLITZZ - WHY DELAY / SHAP EXPLANATION

Purpose:
    Explain why XGBoost predicted a flight delay.

Flow:

    Feature dictionary
          |
          v
      predict.py
          |
          v
    XGBoost model
          |
          v
        SHAP
          |
          v
    Feature contributions
          |
          v
    Human-readable reasons
"""


from pathlib import Path
import pickle

import numpy as np
import pandas as pd
import shap


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MODEL_DIR = BASE_DIR / "models"


XGB_MODEL_PATH = (
    MODEL_DIR / "xgboost_classifier.pkl"
)

SCHEMA_PATH = (
    MODEL_DIR / "feature_schema.pkl"
)


# ============================================================
# FEATURE DISPLAY NAMES
# ============================================================

FEATURE_NAMES = {

    # Flight
    "distance":
        "Flight distance",

    # Time
    "departure_hour":
        "Departure hour",

    "departure_day_of_week":
        "Day of week",

    "departure_month":
        "Departure month",

    "is_weekend":
        "Weekend",

    "is_peak_departure":
        "Peak departure period",


    # Route history
    "route_previous_flights":
        "Previous flights on this route",

    "route_previous_delays":
        "Previous route delays",

    "route_delay_rate":
        "Historical route delay rate",


    # Airline history
    "airline_previous_flights":
        "Previous flights by airline",

    "airline_previous_delays":
        "Previous airline delays",

    "airline_delay_rate":
        "Historical airline delay rate",


    # Congestion
    "origin_flights_1h":
        "Origin airport traffic",

    "destination_flights_1h":
        "Destination airport traffic",

    "route_flights_1h":
        "Route traffic",

    "origin_congestion_ratio":
        "Origin airport congestion",

    "destination_congestion_ratio":
        "Destination airport congestion",

    "route_congestion_ratio":
        "Route congestion",

    "origin_congestion_level":
        "Origin congestion level",

    "destination_congestion_level":
        "Destination congestion level",

    "route_congestion_level":
        "Route congestion",


    # Origin weather
    "origin_temperature":
        "Origin temperature",

    "origin_precipitation":
        "Origin precipitation",

    "origin_rain":
        "Origin rain",

    "origin_snowfall":
        "Origin snowfall",

    "origin_cloud_cover":
        "Origin cloud cover",

    "origin_wind_speed":
        "Origin wind speed",


    # Destination weather
    "destination_temperature":
        "Destination temperature",

    "destination_precipitation":
        "Destination precipitation",

    "destination_rain":
        "Destination rain",

    "destination_snowfall":
        "Destination snowfall",

    "destination_cloud_cover":
        "Destination cloud cover",

    "destination_wind_speed":
        "Destination wind speed",


    # Combined
    "origin_weather_severity":
        "Origin weather severity",

    "destination_weather_severity":
        "Destination weather severity",
}


# ============================================================
# LOAD MODEL
# ============================================================

def load_pickle(path: Path):

    if not path.exists():

        raise FileNotFoundError(
            f"Required model file not found: {path}"
        )

    with open(
        path,
        "rb",
    ) as file:

        return pickle.load(file)


# ============================================================
# EXPLAINER
# ============================================================

class FlightExplainer:

    def __init__(self):

        self.model = load_pickle(
            XGB_MODEL_PATH
        )

        self.schema = load_pickle(
            SCHEMA_PATH
        )

        self.feature_columns = (
            self.schema["feature_columns"]
        )

        self.categorical_features = (
            self.schema["categorical_features"]
        )

        self.encoder = (
            self.schema["encoder"]
        )

        # ----------------------------------------------------
        # TreeSHAP
        # ----------------------------------------------------

        self.explainer = shap.TreeExplainer(
            self.model
        )


    # ========================================================
    # PREPARE FEATURES
    # ========================================================

    def prepare_features(
        self,
        features: dict,
    ) -> pd.DataFrame:

        """
        Prepare live features exactly as the model
        expects them.
        """

        df = pd.DataFrame(
            [features]
        )


        # ----------------------------------------------------
        # Add missing features
        # ----------------------------------------------------

        for column in self.feature_columns:

            if column not in df.columns:

                df[column] = np.nan


        # ----------------------------------------------------
        # Correct feature order
        # ----------------------------------------------------

        df = df[
            self.feature_columns
        ].copy()


        # ----------------------------------------------------
        # Categorical features
        # ----------------------------------------------------

        for column in self.categorical_features:

            df[column] = (

                df[column]

                .fillna("UNKNOWN")

                .astype(str)
            )


        # ----------------------------------------------------
        # Numerical features
        # ----------------------------------------------------

        numerical_features = [

            column

            for column in self.feature_columns

            if column
            not in self.categorical_features
        ]


        for column in numerical_features:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )


            df[column] = (
                df[column]
                .fillna(0)
            )


        # ----------------------------------------------------
        # Apply SAME encoder used during training
        # ----------------------------------------------------

        if self.categorical_features:

            df[
                self.categorical_features
            ] = self.encoder.transform(
                df[
                    self.categorical_features
                ]
            )


        return df.astype(
            np.float32
        )


    # ========================================================
    # SHAP VALUES
    # ========================================================

    def calculate_shap(
        self,
        X: pd.DataFrame,
    ):

        """
        Calculate SHAP contributions for this flight.
        """

        shap_values = self.explainer.shap_values(
            X
        )


        # ----------------------------------------------------
        # XGBoost binary classifier
        #
        # Depending on SHAP version, the result can be:
        #
        # 1. numpy array
        # 2. list of arrays
        # 3. Explanation object
        # ----------------------------------------------------

        if hasattr(
            shap_values,
            "values",
        ):

            values = shap_values.values

        elif isinstance(
            shap_values,
            list,
        ):

            values = shap_values[-1]

        else:

            values = shap_values


        values = np.asarray(
            values
        )


        # ----------------------------------------------------
        # Single prediction
        # ----------------------------------------------------

        if values.ndim == 2:

            values = values[0]

        elif values.ndim == 3:

            values = values[0, :, -1]


        return values


    # ========================================================
    # CATEGORY
    # ========================================================

    @staticmethod
    def get_category(
        feature: str,
    ) -> str:

        if (
            "weather" in feature
            or "temperature" in feature
            or "precipitation" in feature
            or "rain" in feature
            or "snowfall" in feature
            or "cloud" in feature
            or "wind" in feature
        ):

            return "WEATHER"


        if (
            "congestion" in feature
            or "traffic" in feature
            or "flights_1h" in feature
        ):

            return "CONGESTION"


        if (
            "route" in feature
            or "previous" in feature
            or "delay_rate" in feature
        ):

            return "HISTORICAL"


        if (
            "departure" in feature
            or "weekend" in feature
            or "peak" in feature
        ):

            return "SCHEDULE"


        if feature in [
            "airline",
            "origin_airport",
            "destination_airport",
        ]:

            return "FLIGHT"


        return "OTHER"


    # ========================================================
    # EXPLAIN
    # ========================================================

    def explain(
        self,
        features: dict,
        top_n: int = 8,
    ) -> dict:

        """
        Generate complete Why-Delay explanation.
        """

        X = self.prepare_features(
            features
        )


        # ----------------------------------------------------
        # SHAP
        # ----------------------------------------------------

        shap_values = self.calculate_shap(
            X
        )


        # ----------------------------------------------------
        # Prediction probability
        # ----------------------------------------------------

        probability = float(

            self.model
            .predict_proba(X)[0][1]
        )


        # ----------------------------------------------------
        # Build contribution dataframe
        # ----------------------------------------------------

        explanation = pd.DataFrame({

            "feature":
                self.feature_columns,

            "shap_value":
                shap_values,

            "feature_value":
                X.iloc[0].values,
        })


        explanation[
            "absolute_shap"
        ] = explanation[
            "shap_value"
        ].abs()


        explanation = (

            explanation

            .sort_values(
                "absolute_shap",
                ascending=False,
            )

            .head(top_n)
        )


        # ----------------------------------------------------
        # Convert to API-friendly records
        # ----------------------------------------------------

        factors = []


        for _, row in explanation.iterrows():

            feature = row[
                "feature"
            ]


            shap_value = float(
                row["shap_value"]
            )


            # Positive SHAP:
            # pushes toward delay.
            #
            # Negative SHAP:
            # pushes away from delay.

            if shap_value > 0:

                direction = (
                    "INCREASES_DELAY_RISK"
                )

            else:

                direction = (
                    "REDUCES_DELAY_RISK"
                )


            factors.append({

                "feature":
                    feature,

                "display_name":
                    FEATURE_NAMES.get(
                        feature,
                        feature.replace(
                            "_",
                            " ",
                        ).title(),
                    ),

                "category":
                    self.get_category(
                        feature
                    ),

                "value":
                    self._clean_value(
                        row[
                            "feature_value"
                        ]
                    ),

                "shap_value":
                    round(
                        shap_value,
                        4,
                    ),

                "impact":
                    round(
                        abs(shap_value),
                        4,
                    ),

                "direction":
                    direction,
            })


        # ----------------------------------------------------
        # Category summary
        # ----------------------------------------------------

        category_summary = {}


        for factor in factors:

            category = factor[
                "category"
            ]


            category_summary.setdefault(
                category,
                0.0,
            )


            category_summary[
                category
            ] += factor[
                "impact"
            ]


        category_summary = dict(

            sorted(
                category_summary.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        )


        # ----------------------------------------------------
        # Main reason
        # ----------------------------------------------------

        positive_factors = [

            factor

            for factor in factors

            if factor[
                "shap_value"
            ] > 0
        ]


        if positive_factors:

            primary_reason = (
                positive_factors[0]
            )

            summary = (

                f"{primary_reason['display_name']} "
                f"is the strongest factor increasing "
                f"the predicted delay risk."
            )

        else:

            summary = (
                "No major feature is strongly "
                "increasing the predicted delay risk."
            )


        # ----------------------------------------------------
        # Final result
        # ----------------------------------------------------

        return {

            "delay_probability":
                round(
                    probability,
                    4,
                ),

            "delay_probability_percent":
                round(
                    probability * 100,
                    2,
                ),

            "summary":
                summary,

            "primary_reason":

                positive_factors[0]
                if positive_factors
                else None,

            "top_delay_factors":
                factors,

            "category_contribution":
                {
                    key: round(
                        value,
                        4,
                    )

                    for key, value
                    in category_summary.items()
                },
        }


    # ========================================================
    # CLEAN VALUES
    # ========================================================

    @staticmethod
    def _clean_value(
        value,
    ):

        if isinstance(
            value,
            np.generic,
        ):

            value = value.item()


        if isinstance(
            value,
            float,
        ):

            if np.isnan(value):

                return None

            return round(
                value,
                4,
            )


        return value


# ============================================================
# SINGLETON
# ============================================================

_explainer = None


def get_explainer():

    global _explainer


    if _explainer is None:

        _explainer = FlightExplainer()


    return _explainer


# ============================================================
# FASTAPI HELPER
# ============================================================

def explain_flight(
    features: dict,
    top_n: int = 8,
) -> dict:

    explainer = get_explainer()

    return explainer.explain(
        features,
        top_n,
    )