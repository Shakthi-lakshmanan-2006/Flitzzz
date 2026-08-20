from sqlalchemy import text

from database import engine


def generate_recommendations(
    flight_id: int,
    max_results: int = 6,
):

    with engine.connect() as conn:

        # ====================================================
        # CURRENT FLIGHT
        # ====================================================

        current = conn.execute(
            text(
                """
                SELECT
                    f.flight_id,
                    f.flight_number,
                    f.flight_date,
                    f.scheduled_departure,
                    f.scheduled_arrival,

                    al.iata_code AS airline_code,
                    al.airline_name,

                    oa.iata_code AS origin,
                    da.iata_code AS destination,

                    f.origin_airport_id,
                    f.destination_airport_id

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
                "flight_id":
                    flight_id
            },
        ).mappings().first()

        if not current:

            raise ValueError(
                f"Flight {flight_id} not found."
            )

        # ====================================================
        # UPCOMING SAME-ROUTE FLIGHTS
        # ====================================================

        alternatives = conn.execute(
            text(
                """
                SELECT
                    f.flight_id,
                    f.flight_number,
                    f.flight_date,
                    f.scheduled_departure,
                    f.scheduled_arrival,

                    al.iata_code AS airline_code,
                    al.airline_name,

                    oa.iata_code AS origin,
                    da.iata_code AS destination

                FROM flights f

                LEFT JOIN airlines al
                    ON al.airline_id = f.airline_id

                LEFT JOIN airports oa
                    ON oa.airport_id =
                       f.origin_airport_id

                LEFT JOIN airports da
                    ON da.airport_id =
                       f.destination_airport_id

                WHERE
                    f.flight_id != :flight_id

                    AND f.origin_airport_id =
                        :origin_airport_id

                    AND f.destination_airport_id =
                        :destination_airport_id

                    AND (
                        f.flight_date >
                            :flight_date

                        OR (
                            f.flight_date =
                                :flight_date

                            AND f.scheduled_departure >
                                :scheduled_departure
                        )
                    )

                ORDER BY
                    f.flight_date ASC,
                    f.scheduled_departure ASC

                LIMIT :max_results
                """
            ),
            {
                "flight_id":
                    flight_id,

                "origin_airport_id":
                    current[
                        "origin_airport_id"
                    ],

                "destination_airport_id":
                    current[
                        "destination_airport_id"
                    ],

                "flight_date":
                    current[
                        "flight_date"
                    ],

                "scheduled_departure":
                    current[
                        "scheduled_departure"
                    ],

                "max_results":
                    max_results,
            },
        ).mappings().all()

    recommendations = []

    for index, flight in enumerate(
        alternatives,
        start=1,
    ):

        score = max(
            95 - ((index - 1) * 5),
            70,
        )

        recommendations.append(
            {
                "recommendation_id":
                    f"{flight_id}-{flight['flight_id']}",

                "original_flight_id":
                    current["flight_id"],

                "alternative_flight_id":
                    flight["flight_id"],

                "original_flight_number":
                    current["flight_number"],

                "alternative_flight_number":
                    flight["flight_number"],

                "airline_code":
                    flight["airline_code"],

                "airline_name":
                    flight["airline_name"],

                "origin":
                    flight["origin"],

                "destination":
                    flight["destination"],

                "flight_date":
                    flight["flight_date"],

                "scheduled_departure":
                    flight[
                        "scheduled_departure"
                    ],

                "scheduled_arrival":
                    flight[
                        "scheduled_arrival"
                    ],

                "recommendation_score":
                    score,

                "reason":
                    "Upcoming flight on the same "
                    "origin and destination route, "
                    "ordered by earliest departure.",

                "status":
                    "PENDING",
            }
        )

    return recommendations


def accept_rebooking(
    recommendation_id,
    passenger_confirmation: bool,
    accept_price_difference: bool = True,
):

    if not passenger_confirmation:

        return {
            "recommendation_id":
                recommendation_id,

            "status":
                "REJECTED",

            "message":
                "Passenger did not confirm rebooking.",
        }

    return {
        "recommendation_id":
            recommendation_id,

        "status":
            "ACCEPTED",

        "message":
            "Passenger rebooking accepted.",
    }