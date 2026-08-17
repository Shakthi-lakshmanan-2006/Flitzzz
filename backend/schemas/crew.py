from pydantic import BaseModel
from typing import Optional


# =========================================================
# CREW RESPONSE
# =========================================================

class CrewResponse(BaseModel):

    crew_id: int

    crew_code: str

    first_name: str

    last_name: str

    crew_type: str

    role: str

    email: Optional[str] = None

    status: str


# =========================================================
# SINGLE CREW MEMBER ASSIGNMENT
# =========================================================

class CrewMemberAssignment(BaseModel):

    crew_id: int

    assignment_role: str


# =========================================================
# ASSIGN CREW REQUEST
# =========================================================

class CrewAssignmentRequest(BaseModel):

    flight_id: int

    assignments: list[CrewMemberAssignment]

    notes: Optional[str] = None


# =========================================================
# CREW ASSIGNMENT RESPONSE
# =========================================================

class CrewAssignmentResponse(BaseModel):

    assignment_id: int

    flight_id: int

    crew_id: int

    crew_name: str

    assignment_role: str

    status: str

    assigned_at: str