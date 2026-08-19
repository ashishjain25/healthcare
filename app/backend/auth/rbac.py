"""Role-based access control. Auth uses Starlette's signed-cookie
SessionMiddleware (request.session) rather than a server-side session table
— {"user_id", "role", "full_name", "patient_id"} is stored directly in the
cookie. Row-level checks (e.g. a patient can't fetch another patient's
report by guessing an ID) live in the service layer, not here — this module
only gates by role.
"""
from enum import Enum

from fastapi import Depends, HTTPException, Request, status


class UserRole(str, Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    RADIOLOGIST = "radiologist"


def get_current_user(request: Request) -> dict:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def require_role(*roles: UserRole):
    allowed = {r.value for r in roles}

    def dependency(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return dependency
