from pydantic import BaseModel
from typing import Optional


class RebookingRequest(BaseModel):

    max_results: int = 3

    same_route_only: bool = True

    same_cabin_only: bool = True

    allow_lower_price: bool = True

    allow_higher_price: bool = False

    max_price_difference: Optional[float] = None


class RebookingRecommendationResponse(BaseModel):

    recommendation_id: int

    booking_id: int

    original_flight_id: int
    alternative_flight_id: int

    original_flight_number: str
    alternative_flight_number: str

    cabin_class: str

    original_price: float
    alternative_price: float

    price_difference: float

    available_seats: int

    recommendation_score: float

    reason: str

    status: str


class BookingRecommendationsResponse(BaseModel):

    booking_id: int
    booking_reference: str

    recommendations: list[
        RebookingRecommendationResponse
    ]


class AcceptRebookingRequest(BaseModel):

    passenger_confirmation: bool

    accept_price_difference: bool = False


class AcceptRebookingResponse(BaseModel):

    recommendation_id: int

    booking_id: int

    status: str

    old_flight_id: int
    new_flight_id: int

    message: str