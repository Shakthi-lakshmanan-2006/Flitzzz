from datetime import datetime


def run_prediction(flight_id: int):

    # =====================================================
    # DUMMY ML IMPLEMENTATION
    # =====================================================
    #
    # Later this will:
    #
    # PostgreSQL
    #     ↓
    # Feature Builder
    #     ↓
    # CatBoost
    #     +
    # LightGBM
    #     ↓
    # Ensemble
    #     ↓
    # SHAP
    #
    # =====================================================

    dummy_probability = 0.82
    dummy_delay = 42.0

    if dummy_probability >= 0.75:
        risk = "HIGH"

    elif dummy_probability >= 0.50:
        risk = "MEDIUM"

    else:
        risk = "LOW"

    return {
        "prediction_id": 999999,
        "flight_id": flight_id,
        "flight_number": "DUMMY",
        "delay_probability": dummy_probability,
        "expected_delay_minutes": dummy_delay,
        "risk_level": risk,
        "model_name": "FLITZZ-DUMMY-ENSEMBLE",
        "model_version": "0.0.1",
        "prediction_timestamp": datetime.now().isoformat()
    }


def get_dummy_why_delay(flight_id: int):

    return {
        "primary_cause": "WEATHER",

        "secondary_causes": [
            "AIRPORT_CONGESTION",
            "HISTORICAL_ROUTE"
        ],

        "cause_scores": {
            "WEATHER": 0.45,
            "AIRPORT_CONGESTION": 0.30,
            "HISTORICAL_ROUTE": 0.25
        },

        "shap_features": [
            {
                "feature_name": "weather_severity_score",
                "shap_value": 0.21,
                "direction": "INCREASES_RISK"
            },
            {
                "feature_name": "route_delay_rate",
                "shap_value": 0.17,
                "direction": "INCREASES_RISK"
            },
            {
                "feature_name": "destination_congestion",
                "shap_value": 0.13,
                "direction": "INCREASES_RISK"
            }
        ],

        "weather_context": {
            "severity_score": 0.78,
            "status": "SEVERE"
        },

        "congestion_context": {
            "airport_score": 0.71,
            "status": "HIGH"
        },

        "passenger_explanation":
            "Weather conditions are currently the "
            "strongest contributor to the predicted "
            "delay risk.",

        "management_explanation":
            "The dummy explanation indicates weather, "
            "airport congestion and historical route "
            "delay as the major contributing factors."
    }