from fastapi import APIRouter

from schemas.dashboard import DashboardResponse


router = APIRouter(
    prefix="/api",
    tags=["Dashboard"]
)


@router.get(
    "/dashboard",
    response_model=DashboardResponse
)
def dashboard():

    # TODO:
    # Replace with PostgreSQL aggregation.

    return {
        "total_passengers": 8,
        "total_flights": 8,

        "high_risk_flights": 0,
        "medium_risk_flights": 0,
        "low_risk_flights": 0,

        "pending_rebookings": 0,
        "pending_notifications": 0
    }