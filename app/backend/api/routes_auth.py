import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from backend.auth.security import verify_password
from backend.db.repositories import patient_repo, user_repo
from backend.dependencies import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(payload: LoginRequest, request: Request, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    user = user_repo.get_by_email(conn, payload.email)
    if not user or not verify_password(payload.password, user["password_hash"], user["password_salt"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    session_user = {"user_id": user["id"], "role": user["role"], "full_name": user["full_name"]}
    if user["role"] == "patient":
        patient = patient_repo.get_by_user_id(conn, user["id"])
        session_user["patient_id"] = patient["id"] if patient else None
    request.session["user"] = session_user
    return session_user


@router.post("/logout")
def logout(request: Request) -> dict:
    request.session.clear()
    return {"ok": True}


@router.get("/me")
def me(request: Request) -> dict:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
