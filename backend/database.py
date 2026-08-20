import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# ============================================================
# LOAD .ENV
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(
    os.path.join(BASE_DIR, ".env")
)


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:

    DB_HOST = os.getenv(
        "DB_HOST",
        "localhost"
    )

    DB_PORT = os.getenv(
        "DB_PORT",
        "5432"
    )

    DB_NAME = os.getenv(
        "DB_NAME",
        "flitz"
    )

    DB_USER = os.getenv(
        "DB_USER",
        "postgres"
    )

    DB_PASSWORD = os.getenv(
        "DB_PASSWORD",
        ""
    )

    DATABASE_URL = (
        "postgresql+psycopg2://"
        f"{DB_USER}:{DB_PASSWORD}@"
        f"{DB_HOST}:{DB_PORT}/"
        f"{DB_NAME}"
    )


# ============================================================
# SQLALCHEMY ENGINE
# ============================================================

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
)


# ============================================================
# DATABASE TEST
# ============================================================

def test_database_connection():

    with engine.connect() as conn:

        conn.execute(
            text("SELECT 1")
        )

    return True