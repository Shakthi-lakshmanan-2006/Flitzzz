from pydantic import BaseModel
from typing import Optional


# =========================================================
# SEND NOTIFICATION REQUEST
# =========================================================

class SendNotificationRequest(BaseModel):
    """
    Request used when sending a passenger notification.
    """

    channel: str = "EMAIL"

    force_resend: bool = False


# =========================================================
# NOTIFICATION RESPONSE
# =========================================================

class NotificationResponse(BaseModel):

    notification_id: int

    booking_id: Optional[int] = None

    passenger_id: int

    channel: str

    status: str

    recipient: str

    sent_at: Optional[str] = None

    message: str        