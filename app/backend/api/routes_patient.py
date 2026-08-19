import sqlite3

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from backend.agents.pipeline import ClinicalPipeline
from backend.auth.rbac import UserRole, require_role
from backend.config import Settings, get_settings
from backend.db.repositories import alert_repo, appointment_repo, patient_repo, user_repo
from backend.dependencies import get_db, get_llm_client, get_pipeline, get_vector_store
from backend.llm.openai_client import OpenAIClient
from backend.services import appointment_service, chat_service, compare_service, pipeline_trigger, report_service
from backend.services.report_service import ForbiddenError, NotFoundError
from backend.vectorstore.chroma_store import ChromaStore

router = APIRouter(prefix="/api/patient", tags=["patient"])
_require_patient = require_role(UserRole.PATIENT)


@router.get("/reports")
def list_reports(user: dict = Depends(_require_patient), conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    return report_service.list_patient_reports(conn, user["patient_id"])


@router.post("/reports/upload")
async def upload_report(
    background_tasks: BackgroundTasks,
    report_type: str = Form(...),
    category: str = Form(...),
    uploader_notes: str | None = Form(None),
    raw_text: str | None = Form(None),
    file: UploadFile | None = File(None),
    user: dict = Depends(_require_patient),
    conn: sqlite3.Connection = Depends(get_db),
    vector_store: ChromaStore = Depends(get_vector_store),
    llm_client: OpenAIClient = Depends(get_llm_client),
    settings: Settings = Depends(get_settings),
    pipeline: ClinicalPipeline = Depends(get_pipeline),
) -> dict:
    if not settings.openai_configured:
        raise HTTPException(status_code=503, detail="AI features unavailable: OPENAI_API_KEY is not configured.")

    file_bytes = await file.read() if file else None
    original_filename = file.filename if file else None
    if not raw_text and not file_bytes:
        raise HTTPException(status_code=400, detail="Provide either raw_text or a file.")

    report_id = report_service.upload_report(
        conn, vector_store=vector_store, llm_client=llm_client, settings=settings,
        patient_id=user["patient_id"], uploaded_by_user_id=user["user_id"],
        report_type=report_type, category=category, uploader_notes=uploader_notes,
        raw_text=raw_text, file_bytes=file_bytes, original_filename=original_filename,
    )
    background_tasks.add_task(
        pipeline_trigger.run_pipeline_in_background,
        database_path=settings.DATABASE_PATH, pipeline=pipeline, report_id=report_id,
    )
    return {"report_id": report_id, "status": "processing"}


@router.get("/reports/compare")
def compare(a: int, b: int, user: dict = Depends(_require_patient),
            conn: sqlite3.Connection = Depends(get_db)) -> dict:
    try:
        return compare_service.compare_reports(conn, a, b, patient_id=user["patient_id"])
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except compare_service.CategoryMismatchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/reports/{report_id}")
def get_report(report_id: int, user: dict = Depends(_require_patient),
               conn: sqlite3.Connection = Depends(get_db)) -> dict:
    try:
        return report_service.get_patient_report_view(conn, report_id, user["patient_id"])
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/history")
def get_history(user: dict = Depends(_require_patient), conn: sqlite3.Connection = Depends(get_db)) -> dict:
    return {
        "allergies": [dict(a) for a in patient_repo.list_allergies(conn, user["patient_id"])],
        "medical_history": [dict(h) for h in patient_repo.list_medical_history(conn, user["patient_id"])],
    }


@router.post("/history/allergy")
def add_allergy(payload: dict, user: dict = Depends(_require_patient),
                 conn: sqlite3.Connection = Depends(get_db)) -> dict:
    allergy_id = patient_repo.add_allergy(
        conn, patient_id=user["patient_id"], allergen=payload["allergen"],
        category=payload["category"], severity=payload.get("severity"),
        reaction_notes=payload.get("reaction_notes"), source="self_reported",
    )
    return {"id": allergy_id}


@router.post("/history/entry")
def add_history_entry(payload: dict, user: dict = Depends(_require_patient),
                       conn: sqlite3.Connection = Depends(get_db)) -> dict:
    entry_id = patient_repo.add_medical_history(
        conn, patient_id=user["patient_id"], entry_type=payload["entry_type"],
        description=payload["description"], entry_date=payload.get("entry_date"),
    )
    return {"id": entry_id}


@router.post("/chat")
def chat(payload: dict, user: dict = Depends(_require_patient), conn: sqlite3.Connection = Depends(get_db),
         vector_store: ChromaStore = Depends(get_vector_store),
         llm_client: OpenAIClient = Depends(get_llm_client),
         settings: Settings = Depends(get_settings)) -> dict:
    if not settings.openai_configured:
        raise HTTPException(status_code=503, detail="AI features unavailable: OPENAI_API_KEY is not configured.")
    answer = chat_service.ask(
        conn, vector_store=vector_store, llm_client=llm_client, user_id=user["user_id"],
        patient_id=user["patient_id"], role="patient", question=payload["question"],
    )
    return {"answer": answer}


@router.get("/chat/history")
def chat_history(user: dict = Depends(_require_patient), conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    return chat_service.get_history(conn, user_id=user["user_id"], patient_id=user["patient_id"], role="patient")


@router.get("/appointments")
def list_appointments(user: dict = Depends(_require_patient), conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    return [dict(a) for a in appointment_repo.list_by_patient(conn, user["patient_id"])]


@router.get("/doctors")
def list_doctors(user: dict = Depends(_require_patient), conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    return [{"id": u["id"], "full_name": u["full_name"], "email": u["email"]}
            for u in user_repo.list_by_role(conn, "doctor")]


@router.get("/appointments/availability")
def appointment_availability(doctor_user_id: int, date: str, user: dict = Depends(_require_patient),
                              conn: sqlite3.Connection = Depends(get_db)) -> dict:
    try:
        slots = appointment_service.list_available_slots(conn, doctor_user_id, date)
    except appointment_service.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except appointment_service.ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"available_times": slots}


@router.post("/appointments/book")
def book_appointment(payload: dict, user: dict = Depends(_require_patient),
                      conn: sqlite3.Connection = Depends(get_db)) -> dict:
    try:
        appointment_id = appointment_service.book_appointment(
            conn, patient_id=user["patient_id"], doctor_user_id=payload["doctor_user_id"],
            date_str=payload["date"], time_str=payload["time"], reason=payload.get("reason"),
        )
    except appointment_service.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except appointment_service.ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except appointment_service.ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"id": appointment_id}


@router.patch("/appointments/{appointment_id}/cancel")
def cancel_appointment(appointment_id: int, user: dict = Depends(_require_patient),
                        conn: sqlite3.Connection = Depends(get_db)) -> dict:
    try:
        appointment_service.cancel_appointment(
            conn, appointment_id=appointment_id, patient_id=user["patient_id"],
        )
    except appointment_service.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except appointment_service.ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except appointment_service.ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.get("/alerts")
def list_alerts(user: dict = Depends(_require_patient), conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    return [dict(a) for a in alert_repo.list_by_patient(conn, user["patient_id"])]
