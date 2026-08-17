import os
from dotenv import load_dotenv

load_dotenv()


DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "flitzz")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
WEATHER_API_URL = os.getenv("WEATHER_API_URL", "")

TRAFFIC_API_KEY = os.getenv("TRAFFIC_API_KEY", "")
TRAFFIC_API_URL = os.getenv("TRAFFIC_API_URL", "")

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://127.0.0.1:5500"
)