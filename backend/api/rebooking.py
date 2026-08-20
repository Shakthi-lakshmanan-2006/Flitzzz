from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from database import engine

from services.rebooking import (
    generate_recommendations,
    accept_rebooking,
)


router = APIRouter(
    prefix="/api/rebooking",
    tags=["Rebooking"],
)


# ============================================================
# 1. COMPLETE REBOOKING PAGE DATA
# ============================================================
#
# Frontend calls:
#
# GET /api/rebooking/{flight_id}
#
# This endpoint gives the Rebooking page EVERYTHING it needs.
#
# ============================================================

@router.get("/{flight_id}")
def get_rebooking_overview(flight_id: int):

    if flight_id < 1:
        raise HTTPException(
            status_code=400,
            detail="Invalid flight ID."
        )

    try:

        with engine.connect() as conn:

            # ------------------------------------------------
            # REAL FLIGHT
            # ------------------------------------------------

            flight = conn.execute(
                text(
                    """
                    SELECT
                        f.flight_id,
                        f.flight_number,
                        f.flight_date,

                        al.iata_code AS airline_code,
                        al.airline_name,

                        oa.iata_code AS origin_airport,
                        oa.airport_name AS origin_name,

                        da.iata_code AS destination_airport,
                        da.airport_name AS destination_name,

                        f.scheduled_departure,
                        f.scheduled_arrival

                    FROM flights f

                    LEFT JOIN airlines al
                        ON al.airline_id = f.airline_id

                    LEFT JOIN airports oa
                        ON oa.airport_id =
                           f.origin_airport_id

                    LEFT JOIN airports da
                        ON da.airport_id =
                           f.destination_airport_id

                    WHERE f.flight_id = :flight_id
                    """
                ),
                {
                    "flight_id": flight_id
                },
            ).mappings().first()

            if not flight:
                raise HTTPException(
                    status_code=404,
                    detail=f"Flight {flight_id} not found."
                )

            # ------------------------------------------------
            # 8 DEMO PASSENGERS
            # ------------------------------------------------
            #
            # IMPORTANT:
            # These passengers are intentionally reused
            # for every delayed flight.
            #
            # We DO NOT check booking/flight_id here.
            #
            # ------------------------------------------------

            passengers = conn.execute(
                text(
                    """
                    SELECT
                        passenger_id,
                        passenger_code,
                        first_name,
                        last_name,
                        email,
                        notification_channel,
                        notification_enabled

                    FROM passengers

                                        WHERE notification_enabled = TRUE
                      AND email IS NOT NULL

                    ORDER BY passenger_id

                    LIMIT 8
                    """
                )
            ).mappings().all()

        # ----------------------------------------------------
        # REAL UPCOMING ALTERNATIVE FLIGHTS
        # ----------------------------------------------------

        alternatives = generate_recommendations(
            flight_id=flight_id,
            max_results=6,
        )

        return {
            "status": "success",

            # ------------------------------------------------
            # FLIGHT
            # ------------------------------------------------

            "flight": dict(flight),

            # ------------------------------------------------
            # PASSENGERS
            # ------------------------------------------------

            "passenger_mode": "DEMO_TEAM_PASSENGERS",

            "passenger_count":
                len(passengers),

            "total_passengers":
                len(passengers),

            "passengers": [
                dict(passenger)
                for passenger in passengers
            ],

            # ------------------------------------------------
            # ALTERNATIVES
            # ------------------------------------------------

            "alternative_count":
                len(alternatives),

            "alternatives":
                alternatives,

            "alternative_flights":
                alternatives,
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# 2. GET PASSENGERS ONLY
# ============================================================

@router.get("/{flight_id}/passengers")
def get_impacted_passengers(flight_id: int):

    try:

        with engine.connect() as conn:

            # Verify flight exists
            flight = conn.execute(
                text(
                    """
                    SELECT flight_id
                    FROM flights
                    WHERE flight_id = :flight_id
                    """
                ),
                {
                    "flight_id": flight_id
                },
            ).scalar_one_or_none()

            if flight is None:

                raise HTTPException(
                    status_code=404,
                    detail="Flight not found."
                )

            # Always use first 8 enabled passengers
            passengers = conn.execute(
                text(
                    """
                    SELECT
                        passenger_id,
                        passenger_code,
                        first_name,
                        last_name,
                        email,
                        notification_channel,
                        notification_enabled

                    FROM passengers

                                        WHERE notification_enabled = TRUE
                      AND email IS NOT NULL

                    ORDER BY passenger_id

                    LIMIT 8
                    """
                )
            ).mappings().all()

        return {
            "status": "success",

            "flight_id":
                flight_id,

            "passenger_mode":
                "DEMO_TEAM_PASSENGERS",

            "count":
                len(passengers),

            "passengers": [
                dict(passenger)
                for passenger in passengers
            ],
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# 3. GET UPCOMING ALTERNATIVE FLIGHTS
# ============================================================

@router.get("/{flight_id}/alternatives")
def get_alternative_flights(flight_id: int):

    try:

        alternatives = generate_recommendations(
            flight_id=flight_id,
            max_results=6,
        )

        return {
            "status": "success",

            "flight_id":
                flight_id,

            "count":
                len(alternatives),

            "alternatives":
                alternatives,
        }

    except ValueError as e:

        raise HTTPException(
            status_code=404,
            detail=str(e)
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# 4. REBOOK PASSENGER
# ============================================================

@router.post("/{flight_id}/rebook")
def rebook_passenger(
    flight_id: int,
    passenger_id: int,
    alternative_flight_id: int,
):

    try:

        with engine.connect() as conn:

            passenger = conn.execute(
                text(
                    """
                    SELECT
                        passenger_id,
                        passenger_code,
                        first_name,
                        last_name,
                        email

                    FROM passengers

                    WHERE passenger_id =
                          :passenger_id
                    """
                ),
                {
                    "passenger_id":
                        passenger_id
                },
            ).mappings().first()

            if not passenger:

                raise HTTPException(
                    status_code=404,
                    detail="Passenger not found."
                )

            alternative = conn.execute(
                text(
                    """
                    SELECT
                        f.flight_id,
                        f.flight_number,
                        f.flight_date,
                        f.scheduled_departure,
                        f.scheduled_arrival,

                        al.airline_name,

                        oa.iata_code AS origin,
                        da.iata_code AS destination

                    FROM flights f

                    LEFT JOIN airlines al
                        ON al.airline_id =
                           f.airline_id

                    LEFT JOIN airports oa
                        ON oa.airport_id =
                           f.origin_airport_id

                    LEFT JOIN airports da
                        ON da.airport_id =
                           f.destination_airport_id

                    WHERE f.flight_id =
                          :flight_id
                    """
                ),
                {
                    "flight_id":
                        alternative_flight_id
                },
            ).mappings().first()

            if not alternative:

                raise HTTPException(
                    status_code=404,
                    detail="Alternative flight not found."
                )

        return {
            "status":
                "success",

            "message":
                "Passenger rebooking selected.",

            "flight_id":
                flight_id,

            "passenger":
                dict(passenger),

            "alternative_flight":
                dict(alternative),
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# 5. ACCEPT REBOOKING
# ============================================================

@router.post(
    "/recommendation/{recommendation_id}/accept"
)
def accept_rebooking_route(
    recommendation_id: str,
    passenger_confirmation: bool = True,
    accept_price_difference: bool = True,
):

    try:

        result = accept_rebooking(
            recommendation_id=
                recommendation_id,

            passenger_confirmation=
                passenger_confirmation,

            accept_price_difference=
                accept_price_difference,
        )

        return {
            "status":
                "success",

            "result":
                result,
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )