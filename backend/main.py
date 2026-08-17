from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import FRONTEND_URL

from api.dashboard import router as dashboard_router
from api.flights import router as flights_router
from api.rebooking import router as rebooking_router
from api.notifications import router as notification_router
from api.crew import router as crew_router


app = FastAPI(
    title="FLITZZ Airline Disruption Management API",
    description="""
    FLITZZ backend API.

    Provides:

    - Flight management
    - Passenger bookings
    - Delay prediction
    - SHAP / Why-Delay insights
    - Rebooking recommendations
    - Notifications
    - Crew management

    ML prediction, SHAP, weather and congestion
    integrations are currently running in dummy mode.
    """,
    version="1.0.0"
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        FRONTEND_URL,
        "http://localhost:5500",
        "http://127.0.0.1:5500"
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"]
)


# =========================================================
# ROUTERS
# =========================================================

app.include_router(dashboard_router)
app.include_router(flights_router)
app.include_router(rebooking_router)
app.include_router(notification_router)
app.include_router(crew_router)


# =========================================================
# ROOT
# =========================================================

@app.get(
    "/",
    tags=["System"]
)
def root():

    return {
        "application": "FLITZZ",
        "description":
            "Airline Disruption Management System",

        "status": "ONLINE",

        "mode": "DEVELOPMENT"
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get(
    "/health",
    tags=["System"]
)
def health():

    return {
        "status": "healthy"
    }