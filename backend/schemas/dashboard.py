from pydantic import BaseModel


class DashboardResponse(BaseModel):

    total_passengers: int
    total_flights: int

    high_risk_flights: int
    medium_risk_flights: int
    low_risk_flights: int

    pending_rebookings: int
    pending_notifications: int