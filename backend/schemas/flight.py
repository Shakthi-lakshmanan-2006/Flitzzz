from pydantic import BaseModel
from typing import Optional
from datetime import date, time


# =========================================================
# PASSENGER FLIGHT RESPONSE
# =========================================================

class PassengerFlightResponse(BaseModel):

    passenger_id: int
    passenger_code: str
    passenger_name: str

    age: Optional[int] = None
    gender: Optional[str] = None
    email: str

    booking_id: int
    booking_reference: str

    cabin_class: str
    seat_number: Optional[str] = None
    ticket_price: float

    flight_id: int
    flight_number: str

    route: str

    flight_date: date

    scheduled_departure: Optional[time] = None
    scheduled_arrival: Optional[time] = None

    delay_probability: Optional[float] = None
    expected_delay_minutes: Optional[float] = None
    risk_level: Optional[str] = None


# =========================================================
# FLIGHT RESPONSE
# =========================================================

class FlightResponse(BaseModel):

    flight_id: int
    flight_number: str

    airline_id: int
    aircraft_id: Optional[int] = None

    origin_airport_id: int
    destination_airport_id: int

    route: str

    flight_date: date

    scheduled_departure: Optional[time] = None
    scheduled_arrival: Optional[time] = None

    scheduled_time_minutes: Optional[int] = None
    distance: Optional[float] = None

    cancelled: bool
    diverted: bool


# =========================================================
# AFFECTED PASSENGER RESPONSE
# =========================================================

class AffectedPassengerResponse(BaseModel):

    passenger_id: int

    passenger_code: str

    passenger_name: str

    email: str

    booking_id: int

    booking_reference: str

    cabin_class: str

    seat_number: Optional[str] = None

    booking_status: str