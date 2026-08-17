from fastapi import APIRouter, HTTPException

from database import get_connection

from schemas.flight import (
    PassengerFlightResponse,
    FlightResponse,
    AffectedPassengerResponse
)

from schemas.prediction import (
    PredictionRequest,
    PredictionResponse,
    DelayCauseResponse
)

from services.prediction import (
    run_prediction,
    get_dummy_why_delay
)


router = APIRouter(
    prefix="/api",
    tags=["Flights"]
)


# =========================================================
# PASSENGER FLIGHTS
# =========================================================

@router.get(
    "/passenger-flights",
    response_model=list[PassengerFlightResponse]
)
def get_passenger_flights():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT

                p.passenger_id,
                p.passenger_code,

                p.first_name || ' ' || p.last_name
                    AS passenger_name,

                p.age,
                p.gender,
                p.email,

                b.booking_id,
                b.booking_reference,
                b.cabin_class,
                b.seat_number,
                b.ticket_price,

                f.flight_id,
                f.flight_number,
                f.route,
                f.flight_date,

                f.scheduled_departure,
                f.scheduled_arrival,

                fp.delay_probability,
                fp.expected_delay_minutes,
                fp.risk_level

            FROM passengers p

            JOIN bookings b
                ON b.passenger_id = p.passenger_id

            JOIN flights f
                ON f.flight_id = b.flight_id

            LEFT JOIN LATERAL (

                SELECT
                    delay_probability,
                    expected_delay_minutes,
                    risk_level

                FROM flight_predictions

                WHERE flight_id = f.flight_id

                ORDER BY prediction_timestamp DESC

                LIMIT 1

            ) fp ON TRUE

            WHERE p.passenger_code LIKE 'PAX%'

            ORDER BY p.passenger_id;
        """)

        rows = cursor.fetchall()

        return rows

    finally:

        cursor.close()
        conn.close()


# =========================================================
# FLIGHT DETAILS
# =========================================================

@router.get(
    "/flights/{flight_id}",
    response_model=FlightResponse
)
def get_flight(flight_id: int):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT

                flight_id,
                flight_number,
                airline_id,
                aircraft_id,
                origin_airport_id,
                destination_airport_id,
                route,
                flight_date,
                scheduled_departure,
                scheduled_arrival,
                scheduled_time_minutes,
                distance,
                cancelled,
                diverted

            FROM flights

            WHERE flight_id = %s
        """, (flight_id,))

        flight = cursor.fetchone()

        if not flight:

            raise HTTPException(
                status_code=404,
                detail="Flight not found"
            )

        return flight

    finally:

        cursor.close()
        conn.close()


# =========================================================
# PREDICT
# =========================================================

@router.post(
    "/flights/{flight_id}/predict",
    response_model=PredictionResponse
)
def predict_flight(
    flight_id: int,
    request: PredictionRequest
):

    # TODO:
    # Later replace dummy service with:
    #
    # feature_builder
    # CatBoost
    # LightGBM
    # ensemble
    # SHAP
    # database insert

    result = run_prediction(flight_id)

    return result


# =========================================================
# LATEST PREDICTION
# =========================================================

@router.get(
    "/flights/{flight_id}/prediction",
    response_model=PredictionResponse
)
def latest_prediction(flight_id: int):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT

                prediction_id,
                flight_id,
                delay_probability,
                expected_delay_minutes,
                risk_level,
                model_name,
                model_version,
                prediction_timestamp

            FROM flight_predictions

            WHERE flight_id = %s

            ORDER BY prediction_timestamp DESC

            LIMIT 1
        """, (flight_id,))

        prediction = cursor.fetchone()

        if not prediction:

            raise HTTPException(
                status_code=404,
                detail="No prediction available"
            )

        # flight number
        cursor.execute("""
            SELECT flight_number
            FROM flights
            WHERE flight_id = %s
        """, (flight_id,))

        flight = cursor.fetchone()

        prediction["flight_number"] = (
            flight["flight_number"]
            if flight else "UNKNOWN"
        )

        return prediction

    finally:

        cursor.close()
        conn.close()


# =========================================================
# WHY DELAY
# =========================================================

@router.get(
    "/flights/{flight_id}/why-delay",
    response_model=DelayCauseResponse
)
def why_delay(flight_id: int):

    return get_dummy_why_delay(flight_id)


# =========================================================
# AFFECTED PASSENGERS
# =========================================================

@router.get(
    "/flights/{flight_id}/passengers",
    response_model=list[AffectedPassengerResponse]
)
def affected_passengers(flight_id: int):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT

                p.passenger_id,
                p.passenger_code,

                p.first_name || ' ' || p.last_name
                    AS passenger_name,

                p.email,

                b.booking_id,
                b.booking_reference,

                b.cabin_class,
                b.seat_number,

                b.status AS booking_status

            FROM passengers p

            JOIN bookings b
                ON b.passenger_id = p.passenger_id

            WHERE b.flight_id = %s

            ORDER BY p.passenger_id
        """, (flight_id,))

        return cursor.fetchall()

    finally:

        cursor.close()
        conn.close()