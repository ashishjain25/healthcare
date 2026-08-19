import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from backend.auth.rbac import UserRole, require_role
from backend.config import Settings, get_settings
from backend.db.repositories import (
    alert_repo, appointment_repo, message_repo, patient_repo, pipeline_repo, report_repo, user_repo,
)
from backend.dependencies import get_db, get_llm_client, get_vector_store
from backend.llm.openai_client import OpenAIClient
from backend.services import chat_service, compare_service, report_service
from backend.services.report_service import ForbiddenError, NotFoundError
from backend.vectorstore.chroma_store import ChromaStore

router = APIRouter(prefix="/api/doctor", tags=["doctor"])
_require_doctor = require_role(UserRole.DOCTOR)


@router.get("/patients")
def list_patients(user: dict = Depends(_require_doctor), conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    return [dict(p) for p in patient_repo.list_all(conn)]


@router.get("/radiologists")
def list_radiologists(user: dict = Depends(_require_doctor), conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    return [{"id": u["id"], "full_name": u["full_name"], "email": u["email"]}
            for u in user_repo.list_by_role(conn, "radiologist")]


@router.get("/patients/{patient_id}/reports")
def list_patient_reports(patient_id: int, user: dict = Depends(_require_doctor),
                          conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    return report_service.list_patient_reports(conn, patient_id)


@router.get("/patients/{patient_id}/history")
def get_patient_history(patient_id: int, user: dict = Depends(_require_doctor),
                         conn: sqlite3.Connection = Depends(get_db)) -> dict:
    patient = patient_repo.get_by_id(conn, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {
        "patient": dict(patient),
        "allergies": [dict(a) for a in patient_repo.list_allergies(conn, patient_id)],
        "medical_history": [dict(h) for h in patient_repo.list_medical_history(conn, patient_id)],
    }


@router.get("/reports")
def list_all_reports(user: dict = Depends(_require_doctor), conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    return report_service.list_all_reports(conn)


@router.get("/reports/compare")
def compare(a: int, b: int, user: dict = Depends(_require_doctor), conn: sqlite3.Connection = Depends(get_db)) -> dict:
    try:
        return compare_service.compare_reports(conn, a, b)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except compare_service.CategoryMismatchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/reports/{report_id}")
def get_report(report_id: int, user: dict = Depends(_require_doctor),
                conn: sqlite3.Connection = Depends(get_db)) -> dict:
    try:
        return report_service.get_doctor_report_view(conn, report_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/insights/{insight_id}/review")
def review_insight(insight_id: int, payload: dict, user: dict = Depends(_require_doctor),
                    conn: sqlite3.Connection = Depends(get_db)) -> dict:
    action = payload["action"]
    if action not in ("validated", "modified", "rejected", "finalized"):
        raise HTTPException(status_code=400, detail="Invalid action")
    if pipeline_repo.get_insight(conn, insight_id) is None:
        raise HTTPException(status_code=404, detail="Insight not found")

    review_id = pipeline_repo.add_doctor_review(
        conn, insight_id=insight_id, doctor_user_id=user["user_id"], action=action,
        modified_findings=payload.get("modified_findings"), comments=payload.get("comments"),
    )
    return {"review_id": review_id, "insight": dict(pipeline_repo.get_insight(conn, insight_id))}


@router.get("/appointments")
def list_appointments(user: dict = Depends(_require_doctor), conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    return [dict(a) for a in appointment_repo.list_by_doctor(conn, user["user_id"])]


@router.get("/alerts")
def list_open_alerts(user: dict = Depends(_require_doctor), conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    return [dict(a) for a in alert_repo.list_open(conn)]


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: int, user: dict = Depends(_require_doctor),
                       conn: sqlite3.Connection = Depends(get_db)) -> dict:
    if alert_repo.get_by_id(conn, alert_id) is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert_repo.acknowledge(conn, alert_id, user["user_id"])
    return {"ok": True}


@router.get("/messages")
def list_messages(patient_id: int | None = None, user: dict = Depends(_require_doctor),
                   conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    if patient_id is not None:
        return [dict(m) for m in message_repo.list_for_patient(conn, patient_id)]
    return [dict(m) for m in message_repo.list_for_user(conn, user["user_id"])]


@router.post("/messages")
def send_message(payload: dict, user: dict = Depends(_require_doctor),
                  conn: sqlite3.Connection = Depends(get_db)) -> dict:
    message_id = message_repo.send_message(
        conn, sender_user_id=user["user_id"], recipient_user_id=payload["recipient_user_id"],
        patient_id=payload["patient_id"], report_id=payload.get("report_id"), body=payload["body"],
    )
    return {"id": message_id}


@router.post("/chat")
def chat(payload: dict, user: dict = Depends(_require_doctor), conn: sqlite3.Connection = Depends(get_db),
         vector_store: ChromaStore = Depends(get_vector_store),
         llm_client: OpenAIClient = Depends(get_llm_client),
         settings: Settings = Depends(get_settings)) -> dict:
    if not settings.openai_configured:
        raise HTTPException(status_code=503, detail="AI features unavailable: OPENAI_API_KEY is not configured.")
    answer = chat_service.ask(
        conn, vector_store=vector_store, llm_client=llm_client, user_id=user["user_id"],
        patient_id=payload["patient_id"], role="doctor", question=payload["question"],
    )
    return {"answer": answer}
