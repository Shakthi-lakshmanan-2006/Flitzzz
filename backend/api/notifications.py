from fastapi import APIRouter

from schemas.notification import (
    SendNotificationRequest,
    NotificationResponse
)

from services.notification import send_notification


router = APIRouter(
    prefix="/api",
    tags=["Notifications"]
)


@router.post(
    "/notifications/{notification_id}/send",
    response_model=NotificationResponse
)
def send(
    notification_id: int,
    request: SendNotificationRequest
):

    return send_notification(
        notification_id=notification_id,
        channel=request.channel,
        force_resend=request.force_resend
    )