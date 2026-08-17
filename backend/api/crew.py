from fastapi import APIRouter
from typing import Optional

from database import get_connection

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

    conn = get_connection()
    cursor = conn.cursor()

    try:

        query = """
            SELECT

                crew_id,
                crew_code,
                first_name,
                last_name,
                crew_type,
                role,
                email,
                status

            FROM crew_members

            WHERE status = %s
        """

        params = [status]

        if crew_type:

            query += """
                AND crew_type = %s
            """

            params.append(crew_type)

        if role:

            query += """
                AND role = %s
            """

            params.append(role)

        query += """
            ORDER BY crew_id
        """

        cursor.execute(
            query,
            tuple(params)
        )

        return cursor.fetchall()

    finally:

        cursor.close()
        conn.close()


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

    # =====================================================
    # DUMMY IMPLEMENTATION
    # =====================================================
    #
    # Later:
    #
    # validate flight
    # validate crew
    # check availability
    # check role
    # check duplicate assignment
    # INSERT into crew_assignments
    #
    # =====================================================

    result = []

    for index, assignment in enumerate(
        request.assignments,
        start=1
    ):

        result.append({

            "assignment_id": index,

            "flight_id": request.flight_id,

            "crew_id": assignment.crew_id,

            "crew_name": "Demo Crew",

            "assignment_role":
                assignment.assignment_role,

            "status": "ASSIGNED",

            "assigned_at":
                "2026-08-16T20:00:00"
        })

    return result