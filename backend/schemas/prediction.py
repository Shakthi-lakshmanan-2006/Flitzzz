from pydantic import BaseModel
from typing import Optional


# =========================================================
# PREDICTION REQUEST
# =========================================================

class PredictionRequest(BaseModel):
    """
    Request body for running a flight delay prediction.

    Currently used as a dummy request.
    Later this can contain options for forcing
    recalculation or selecting a model version.
    """

    force_recalculate: bool = False


# =========================================================
# PREDICTION RESPONSE
# =========================================================

class PredictionResponse(BaseModel):

    prediction_id: int

    flight_id: int

    flight_number: str

    delay_probability: float

    expected_delay_minutes: float

    risk_level: str

    model_name: str

    model_version: Optional[str] = None

    prediction_timestamp: str


# =========================================================
# SHAP FEATURE
# =========================================================

class SHAPFeature(BaseModel):

    feature_name: str

    shap_value: float

    direction: str


# =========================================================
# WHY DELAY RESPONSE
# =========================================================

class DelayCauseResponse(BaseModel):

    primary_cause: str

    secondary_causes: list[str]

    cause_scores: dict[str, float]

    shap_features: list[SHAPFeature]

    weather_context: Optional[dict] = None

    congestion_context: Optional[dict] = None

    passenger_explanation: Optional[str] = None

    management_explanation: Optional[str] = None