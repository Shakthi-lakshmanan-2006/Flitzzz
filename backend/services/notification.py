# backend/services/notification.py

import os
import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from sqlalchemy import text

from database import engine


# ============================================================
# SEND FLIGHT DELAY NOTIFICATION
# ============================================================

def send_notification(
    flight_id: int,
    expected_delay_minutes: float | None = None,
    reason: str | None = None,
    recommended_flight: str | None = None,
):

    # ========================================================
    # 1. FETCH REAL FLIGHT FROM POSTGRESQL
    # ========================================================

    with engine.connect() as conn:

        flight = conn.execute(
            text(
                """
                SELECT
                    f.flight_id,
                    f.flight_number,
                    f.flight_date,
                    f.scheduled_departure,
                    f.scheduled_arrival,

                    al.airline_name,

                    oa.iata_code AS origin,
                    da.iata_code AS destination

                FROM flights f

                LEFT JOIN airlines al
                    ON al.airline_id = f.airline_id

                LEFT JOIN airports oa
                    ON oa.airport_id = f.origin_airport_id

                LEFT JOIN airports da
                    ON da.airport_id = f.destination_airport_id

                WHERE f.flight_id = :flight_id

                LIMIT 1
                """
            ),
            {
                "flight_id": flight_id
            }
        ).mappings().first()

        # ----------------------------------------------------
        # Flight does not exist
        # ----------------------------------------------------

        if not flight:

            raise ValueError(
                f"Flight {flight_id} not found."
            )

        # ========================================================
        # 2. FETCH 8 DEMO PASSENGERS
        # ========================================================
        #
        # IMPORTANT:
        # These passengers are intentionally used for the
        # hackathon demonstration.
        #
        # They do NOT need to actually be booked on the
        # selected flight.
        #
        # Flight data remains completely real.
        # Passenger data comes from PostgreSQL.
        # ========================================================

        passengers = conn.execute(
            text(
                """
                SELECT
                    passenger_id,
                    passenger_code,
                    first_name,
                    last_name,
                    email,
                    notification_channel,
                    notification_enabled

                FROM passengers

                                WHERE notification_enabled = TRUE
                  AND email IS NOT NULL
                  AND TRIM(email) <> ''

                ORDER BY passenger_id

                LIMIT 8
                """
            )
        ).mappings().all()

    # ========================================================
    # 3. VERIFY PASSENGERS
    # ========================================================

    if not passengers:

        raise ValueError(
            "No enabled passenger email addresses found "
            "in the passengers table."
        )

    # ========================================================
    # 4. SMTP CONFIGURATION
    # ========================================================

    smtp_host = os.getenv(
        "SMTP_HOST",
        "smtp.gmail.com"
    )

    smtp_port = int(
        os.getenv(
            "SMTP_PORT",
            "587"
        )
    )

    smtp_user = os.getenv(
        "SMTP_USER"
    )

    smtp_password = os.getenv(
        "SMTP_PASSWORD"
    )

    if not smtp_user:

        raise ValueError(
            "SMTP_USER is missing from .env"
        )

    if not smtp_password:

        raise ValueError(
            "SMTP_PASSWORD is missing from .env"
        )

    # ========================================================
    # 5. SEND EMAIL TO ALL 8 PASSENGERS
    # ========================================================

    sent = []
    failed = []

    with smtplib.SMTP(
        smtp_host,
        smtp_port,
        timeout=30
    ) as server:

        server.ehlo()

        # Gmail SMTP TLS
        server.starttls()

        server.ehlo()

        # Gmail App Password authentication
        try:
            server.login(
                smtp_user,
                smtp_password
            )
        except smtplib.SMTPAuthenticationError as exc:
            provider = (
                "Brevo"
                if "brevo" in smtp_host.lower()
                else "Gmail"
                if "gmail" in smtp_host.lower()
                else smtp_host
            )
            raise ValueError(
                f"{provider} SMTP authentication failed. Verify "
                "SMTP_USER and SMTP_PASSWORD; use the provider's SMTP "
                "key, not an API key or normal account password."
            ) from exc

        # ====================================================
        # SEND INDIVIDUAL EMAIL
        # ====================================================

        for passenger in passengers:

            # ------------------------------------------------
            # Passenger name
            # ------------------------------------------------

            name = " ".join(
                part
                for part in [
                    passenger["first_name"],
                    passenger["last_name"]
                ]
                if part
            )

            if not name:

                name = "Passenger"

            # ------------------------------------------------
            # Create email
            # ------------------------------------------------

            message = MIMEMultipart()

            message["From"] = smtp_user

            message["To"] = passenger["email"]

            message["Subject"] = (
                "FLITZZ Flight Operations Update — "
                f"Flight {flight['flight_number']}"
            )

            # =================================================
            # EMAIL BODY
            # =================================================

            body = f"""
Dear {name},

This is an operational flight update from
FLITZZ Aviation Intelligence.

==================================================
FLIGHT DETAILS
==================================================

Flight Number:
{flight['flight_number']}

Airline:
{flight['airline_name'] or 'FLITZZ Partner Airline'}

Route:
{flight['origin']} → {flight['destination']}

Flight Date:
{flight['flight_date']}

Scheduled Departure:
{flight['scheduled_departure']}

Scheduled Arrival:
{flight['scheduled_arrival']}


==================================================
AI FLIGHT STATUS
==================================================

Our AI-powered flight monitoring system has detected
a significant delay risk associated with this flight.

Expected arrival delay:
{f"{expected_delay_minutes:.2f} minutes" if expected_delay_minutes is not None else "See the latest FLITZZ operations update"}

Primary reason:
{reason or "Elevated operational delay risk detected by the prediction engine."}

The FLITZZ prediction engine continuously analyzes
historical flight behaviour, route performance,
airline performance and operational conditions.

Our flight operations team has therefore initiated
the disruption recovery workflow.


==================================================
REBOOKING SUPPORT
==================================================

FLITZZ is evaluating upcoming alternative flights
for the affected route.

Recommended alternatives are evaluated using:

• Same origin airport
• Same destination airport
• Upcoming departure time
• Operational availability
• Passenger convenience


==================================================
PASSENGER ACTION
==================================================

If rebooking becomes necessary, FLITZZ operations
will provide suitable alternative flight options.

Recommended upcoming flight:
{recommended_flight or "The operations team will confirm the best available flight."}

Please wait for the next official operational update.


==================================================
FLITZZ AVIATION INTELLIGENCE
==================================================

This notification was generated automatically by
the FLITZZ AI Flight Disruption Recovery System.

Regards,

FLITZZ Aviation Intelligence
Flight Operations Team
"""

            message.attach(
                MIMEText(
                    body,
                    "plain",
                    "utf-8"
                )
            )

            # =================================================
            # SEND
            # =================================================

            try:

                server.sendmail(
                    smtp_user,
                    [passenger["email"]],
                    message.as_string()
                )

                sent.append(
                    {
                        "passenger_id":
                            passenger["passenger_id"],

                        "passenger_code":
                            passenger["passenger_code"],

                        "name":
                            name,

                        "email":
                            passenger["email"]
                    }
                )

            except Exception as e:

                failed.append(
                    {
                        "passenger_id":
                            passenger["passenger_id"],

                        "passenger_code":
                            passenger["passenger_code"],

                        "name":
                            name,

                        "email":
                            passenger["email"],

                        "error":
                            str(e)
                    }
                )

    # ========================================================
    # 6. RETURN RESULT TO API
    # ========================================================

    return {
        "status":
            "success",

        "flight_id":
            flight["flight_id"],

        "flight_number":
            flight["flight_number"],

        "origin":
            flight["origin"],

        "destination":
            flight["destination"],

        "passenger_mode":
            "DEMO_TEAM_PASSENGERS",

        "total_passengers":
            len(passengers),

        "recipient_count":
            len(sent),

        "recipients":
            sent,

        "failed_count":
            len(failed),

        "failed":
            failed,

        "message":
            (
                f"Flight notification processed for "
                f"{len(sent)} passenger(s)."
            )
    }