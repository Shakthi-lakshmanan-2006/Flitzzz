"""
FLITZZ - DELAY DECISION ENGINE

Prediction:
    XGBoost  -> probability of >= 15 min delay
    LightGBM -> predicted delay minutes

Decision:
    < 15 min
        NORMAL / WAIT

    15-29 min
        MANUAL ACTION

    >= 30 min
        AUTOMATIC ACTION
"""


# ============================================================
# THRESHOLDS
# ============================================================

WAIT_THRESHOLD = 15

AUTOMATIC_THRESHOLD = 30


# ============================================================
# DECISION ENGINE
# ============================================================

def decide_action(
    predicted_delay_minutes: float,
    delay_probability: float,
) -> dict:

    """
    Convert ML prediction into an operational decision.
    """

    minutes = max(
        0.0,
        float(predicted_delay_minutes),
    )

    probability = min(
        1.0,
        max(
            0.0,
            float(delay_probability),
        ),
    )


    # ========================================================
    # NORMAL
    # ========================================================

    if minutes < WAIT_THRESHOLD:

        return {

            "decision": "NORMAL",

            "severity": "LOW",

            "predicted_delay_minutes": round(
                minutes,
                2,
            ),

            "delay_probability": round(
                probability,
                4,
            ),

            "message":
                "Flight is expected to operate with less than 15 minutes delay.",

            "automatic_trigger": False,

            "manual_action_required": False,

            "actions": [],
        }


    # ========================================================
    # MANUAL
    # ========================================================

    if minutes < AUTOMATIC_THRESHOLD:

        return {

            "decision": "MANUAL",

            "severity": "MEDIUM",

            "predicted_delay_minutes": round(
                minutes,
                2,
            ),

            "delay_probability": round(
                probability,
                4,
            ),

            "message":
                "Flight may be delayed. Operations team should review the situation.",

            "automatic_trigger": False,

            "manual_action_required": True,

            "actions": [

                "NOTIFY_OPERATIONS",

                "REVIEW_FLIGHT",

                "OFFER_REBOOKING_IF_REQUIRED",
            ],
        }


    # ========================================================
    # AUTOMATIC
    # ========================================================

    return {

        "decision": "AUTOMATIC",

        "severity": "HIGH",

        "predicted_delay_minutes": round(
            minutes,
            2,
        ),

        "delay_probability": round(
            probability,
            4,
        ),

        "message":
            "Significant flight delay predicted. Automatic disruption workflow should be triggered.",

        "automatic_trigger": True,

        "manual_action_required": False,

        "actions": [

            "NOTIFY_PASSENGERS",

            "GENERATE_REBOOKING_OPTIONS",

            "UPDATE_PASSENGER_BOOKINGS",

            "CHECK_CREW_AVAILABILITY",

            "RESCHEDULE_CREW",

            "UPDATE_FLIGHT_STATUS",
        ],
    }


# ============================================================
# COMPLETE PREDICTION + DECISION
# ============================================================

def build_prediction_result(
    prediction: dict,
) -> dict:

    """
    Combine ML prediction with operational decision.
    """

    delay_probability = prediction.get(
        "delay_probability",
        0.0,
    )

    predicted_delay_minutes = prediction.get(
        "predicted_delay_minutes",
        0.0,
    )


    decision = decide_action(

        predicted_delay_minutes,

        delay_probability,
    )


    return {

        # ----------------------------------------------------
        # ML OUTPUT
        # ----------------------------------------------------

        "prediction": {

            "delay_probability":
                prediction.get(
                    "delay_probability"
                ),

            "delay_probability_percent":
                prediction.get(
                    "delay_probability_percent"
                ),

            "delayed_15":
                prediction.get(
                    "delayed_15"
                ),

            "predicted_delay_minutes":
                prediction.get(
                    "predicted_delay_minutes"
                ),
        },


        # ----------------------------------------------------
        # OPERATIONAL DECISION
        # ----------------------------------------------------

        "decision": decision,
    }


# ============================================================
# HELPER
# ============================================================

def get_decision_from_prediction(
    prediction: dict,
) -> dict:

    """
    Simple helper for FastAPI/service layer.
    """

    return build_prediction_result(
        prediction
    )