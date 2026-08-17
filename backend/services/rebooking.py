def generate_recommendations(
    flight_id: int,
    max_results: int = 3
):

    # =====================================================
    # DUMMY IMPLEMENTATION
    # =====================================================
    #
    # Later:
    #
    # prediction
    #     ↓
    # affected bookings
    #     ↓
    # same route
    #     ↓
    # same cabin
    #     ↓
    # inventory
    #     ↓
    # price
    #     ↓
    # arrival time
    #     ↓
    # recommendation score
    #
    # =====================================================

    return [
        {
            "recommendation_id": 999,
            "booking_id": 1,

            "original_flight_id": flight_id,
            "alternative_flight_id": 105,

            "original_flight_number": "98",
            "alternative_flight_number": "105",

            "cabin_class": "ECONOMY",

            "original_price": 8500.0,
            "alternative_price": 7900.0,

            "price_difference": -600.0,

            "available_seats": 24,

            "recommendation_score": 92.5,

            "reason":
                "Same route, same cabin, "
                "available inventory and lower fare.",

            "status": "PENDING"
        }
    ][:max_results]


def accept_rebooking(
    recommendation_id: int,
    passenger_confirmation: bool,
    accept_price_difference: bool
):

    if not passenger_confirmation:

        return {
            "recommendation_id": recommendation_id,
            "booking_id": 1,
            "status": "REJECTED",
            "old_flight_id": 1,
            "new_flight_id": 105,
            "message": "Passenger did not confirm rebooking."
        }

    return {
        "recommendation_id": recommendation_id,
        "booking_id": 1,
        "status": "ACCEPTED",
        "old_flight_id": 1,
        "new_flight_id": 105,
        "message": "Demo rebooking accepted."
    }