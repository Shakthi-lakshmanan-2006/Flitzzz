from fastapi import APIRouter

from schemas.rebooking import (
    RebookingRequest,
    RebookingRecommendationResponse,
    BookingRecommendationsResponse,
    AcceptRebookingRequest,
    AcceptRebookingResponse
)

from services.rebooking import (
    generate_recommendations,
    accept_rebooking
)


router = APIRouter(
    prefix="/api",
    tags=["Rebooking"]
)


# =========================================================
# GENERATE REBOOKING
# =========================================================

@router.post(
    "/flights/{flight_id}/rebooking",
    response_model=list[
        RebookingRecommendationResponse
    ]
)
def generate_rebooking(
    flight_id: int,
    request: RebookingRequest
):

    return generate_recommendations(
        flight_id=flight_id,
        max_results=request.max_results
    )


# =========================================================
# BOOKING RECOMMENDATIONS
# =========================================================

@router.get(
    "/bookings/{booking_id}/recommendations",
    response_model=BookingRecommendationsResponse
)
def get_recommendations(booking_id: int):

    recommendations = generate_recommendations(
        flight_id=1
    )

    return {
        "booking_id": booking_id,
        "booking_reference": f"FLZ-PAX{booking_id:03d}",
        "recommendations": recommendations
    }


# =========================================================
# ACCEPT REBOOKING
# =========================================================

@router.post(
    "/rebooking/{recommendation_id}/accept",
    response_model=AcceptRebookingResponse
)
def accept(
    recommendation_id: int,
    request: AcceptRebookingRequest
):

    return accept_rebooking(
        recommendation_id,
        request.passenger_confirmation,
        request.accept_price_difference
    )