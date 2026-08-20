from fastapi import APIRouter
from typing import Optional

from sqlalchemy import text

from database import engine

from schemas.crew import (
    CrewResponse,
    CrewAssignmentRequest,
    CrewAssignmentResponse
)


router = APIRouter(
    prefix="/api",
    tags=["Crew"]
)


# =========================================================
# GET CREW
# =========================================================

@router.get(
    "/crew",
    response_model=list[CrewResponse]
)
def get_crew(
    crew_type: Optional[str] = None,
    role: Optional[str] = None,
    status: str = "ACTIVE"
):

    query = """
            SELECT

                crew_member_id AS crew_id,
                employee_code AS crew_code,
                first_name,
                last_name,
                crew_type,
                role,
                email,
                status

            FROM crew_members

            WHERE status = :status
        """

    params = {"status": status}

    if crew_type:

        query += """
            AND crew_type = :crew_type
        """

        params["crew_type"] = crew_type

    if role:

        query += """
            AND role = :role
        """

        params["role"] = role

    query += """
        ORDER BY crew_id
    """

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).mappings().all()

    return [dict(row) for row in rows]


# =========================================================
# ASSIGN CREW
# =========================================================

@router.post(
    "/crew-assignments",
    response_model=list[CrewAssignmentResponse]
)
def assign_crew(
    request: CrewAssignmentRequest
):

    result = []

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                DELETE FROM crew_assignments
                WHERE flight_id = :flight_id
                """
            ),
            {"flight_id": request.flight_id},
        )

        for assignment in request.assignments:
            row = conn.execute(
                text(
                    """
                    INSERT INTO crew_assignments
                        (flight_id, crew_member_id, assignment_role)
                    VALUES
                        (:flight_id, :crew_member_id, :assignment_role)
                    RETURNING assignment_id, flight_id, crew_member_id,
                              assignment_role, assigned_at
                    """
                ),
                {
                    "flight_id": request.flight_id,
                    "crew_member_id": assignment.crew_id,
                    "assignment_role": assignment.assignment_role,
                },
            ).mappings().one()

            crew = conn.execute(
                text(
                    """
                    SELECT first_name, last_name
                    FROM crew_members
                    WHERE crew_member_id = :crew_member_id
                    """
                ),
                {"crew_member_id": assignment.crew_id},
            ).mappings().one()

            result.append({
                "assignment_id": row["assignment_id"],
                "flight_id": row["flight_id"],
                "crew_id": row["crew_member_id"],
                "crew_name": f"{crew['first_name']} {crew['last_name']}",
                "assignment_role": row["assignment_role"],
                "assigned_at": row["assigned_at"].isoformat(),
            })

    return result


# =========================================================
# GET FLIGHT ASSIGNMENTS
# =========================================================

@router.get(
    "/crew-assignments/{flight_id}",
    response_model=list[CrewAssignmentResponse]
)
def get_flight_assignments(flight_id: int):

    query = """
        SELECT
            ca.assignment_id,
            ca.flight_id,
            ca.crew_member_id AS crew_id,
            CONCAT(cm.first_name, ' ', cm.last_name) AS crew_name,
            ca.assignment_role,
            ca.assigned_at
        FROM crew_assignments ca
        JOIN crew_members cm
          ON cm.crew_member_id = ca.crew_member_id
        WHERE ca.flight_id = :flight_id
        ORDER BY ca.assigned_at, ca.assignment_id
    """

    with engine.connect() as conn:
        rows = conn.execute(
            text(query),
            {"flight_id": flight_id},
        ).mappings().all()

    return [
        {
            **dict(row),
            "assigned_at": row["assigned_at"].isoformat(),
        }
        for row in rows
    ]