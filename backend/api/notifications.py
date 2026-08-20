from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.notification import send_notification


router = APIRouter(
    prefix="/api/notifications",
    tags=["Notifications"],
)


class NotificationRequest(BaseModel):
    expected_delay_minutes: float | None = None
    reason: str | None = None
    recommended_flight: str | None = None


@router.post("/{flight_id}/send")
def send_notification_for_flight(
    flight_id: int,
    request: NotificationRequest | None = None,
):

    try:

        result = send_notification(
            flight_id=flight_id,
            expected_delay_minutes=(
                request.expected_delay_minutes
                if request
                else None
            ),
            reason=request.reason if request else None,
            recommended_flight=(
                request.recommended_flight
                if request
                else None
            ),
        )

        return {
            "status":
                "success",

            "message":
                "Notifications sent successfully.",

            "result":
                result,

            "recipient_count":
                result.get(
                    "recipient_count",
                    0,
                ),

            "recipients":
                result.get(
                    "recipients",
                    [],
                ),
        }

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )