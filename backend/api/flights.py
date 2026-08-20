from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from database import engine


router = APIRouter(
    prefix="/api/flights",
    tags=["Flights"],
)


@router.get("")
def list_flights(limit: int = 200):
    limit = max(1, min(limit, 1000))

    with engine.connect() as conn:
        summary = conn.execute(
            text(
                """
                SELECT
                    COUNT(*) AS total_flights,
                    COUNT(DISTINCT al.airline_id) AS total_airlines,
                    COUNT(DISTINCT oa.airport_id) AS origin_airports,
                    COUNT(DISTINCT da.airport_id) AS destination_airports
                FROM flights f
                LEFT JOIN airlines al ON al.airline_id = f.airline_id
                LEFT JOIN airports oa ON oa.airport_id = f.origin_airport_id
                LEFT JOIN airports da ON da.airport_id = f.destination_airport_id
                """
            )
        ).mappings().one()

        airline_counts = conn.execute(
            text(
                """
                SELECT
                    al.iata_code AS airline_code,
                    al.airline_name,
                    COUNT(*) AS flight_count
                FROM flights f
                LEFT JOIN airlines al ON al.airline_id = f.airline_id
                GROUP BY al.iata_code, al.airline_name
                ORDER BY flight_count DESC, al.airline_name
                """
            )
        ).mappings().all()

        airport_counts = conn.execute(
            text(
                """
                SELECT airport_code, airport_name, airport_type, SUM(flight_count) AS flight_count
                FROM (
                    SELECT
                        oa.iata_code AS airport_code,
                        oa.airport_name,
                        'Origin' AS airport_type,
                        COUNT(*) AS flight_count
                    FROM flights f
                    LEFT JOIN airports oa ON oa.airport_id = f.origin_airport_id
                    GROUP BY oa.iata_code, oa.airport_name
                    UNION ALL
                    SELECT
                        da.iata_code AS airport_code,
                        da.airport_name,
                        'Destination' AS airport_type,
                        COUNT(*) AS flight_count
                    FROM flights f
                    LEFT JOIN airports da ON da.airport_id = f.destination_airport_id
                    GROUP BY da.iata_code, da.airport_name
                ) airport_activity
                GROUP BY airport_code, airport_name, airport_type
                ORDER BY flight_count DESC, airport_name
                """
            )
        ).mappings().all()

        rows = conn.execute(
            text(
                """
                SELECT
                    f.flight_id,
                    f.flight_number,
                    al.iata_code AS airline_code,
                    al.airline_name,
                    oa.iata_code AS origin_airport,
                    da.iata_code AS destination_airport,
                    f.scheduled_departure,
                    f.scheduled_arrival,
                    f.distance_miles,
                    COALESCE(fd.departure_delay_minutes, 0) AS departure_delay_minutes,
                    COALESCE(fd.arrival_delay_minutes, 0) AS arrival_delay_minutes,
                    COALESCE(fd.delayed_15, FALSE) AS delayed_15
                FROM flights f
                LEFT JOIN airlines al ON al.airline_id = f.airline_id
                LEFT JOIN airports oa ON oa.airport_id = f.origin_airport_id
                LEFT JOIN airports da ON da.airport_id = f.destination_airport_id
                LEFT JOIN flight_delay fd ON fd.flight_id = f.flight_id
                ORDER BY f.flight_date DESC, f.flight_id DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()

    flights = []
    for row in rows:
        delay = float(row["arrival_delay_minutes"] or row["departure_delay_minutes"] or 0)
        risk = "High" if delay >= 30 else "Medium" if delay >= 15 else "Low"
        probability = 1 if row["delayed_15"] else max(0, min(delay / 30, 0.99))
        flights.append(
            {
                **dict(row),
                "probability": probability,
                "risk_level": risk,
            }
        )

    return {
        "status": "success",
        "summary": dict(summary),
        "airline_counts": [dict(row) for row in airline_counts],
        "airport_counts": [dict(row) for row in airport_counts],
        "flights": flights,
    }


@router.get("/{flight_id}")
def get_flight(flight_id: int):

    with engine.connect() as conn:

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
                    ON oa.airport_id = f.origin_airport_id

                LEFT JOIN airports da
                    ON da.airport_id = f.destination_airport_id

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
            detail="Flight not found."
        )

    return {
        "status": "success",
        "flight": dict(flight),
    }