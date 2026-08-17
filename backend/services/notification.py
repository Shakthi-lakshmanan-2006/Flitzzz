from datetime import datetime


def send_notification(
    notification_id: int,
    channel: str,
    force_resend: bool
):

    # =====================================================
    # DUMMY IMPLEMENTATION
    # =====================================================
    #
    # Later:
    #
    # notification record
    #       ↓
    # email service
    #       ↓
    # SMTP / email provider
    #       ↓
    # update notification status
    #
    # =====================================================

    return {
        "notification_id": notification_id,

        "booking_id": 1,
        "passenger_id": 1,

        "channel": channel,

        "status": "SENT",

        "recipient": "sripoojaka11@gmail.com",

        "sent_at": datetime.now().isoformat(),

        "message":
            "Demo notification sent successfully."
    }