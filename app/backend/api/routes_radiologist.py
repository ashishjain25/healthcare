import sqlite3

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from backend.agents.pipeline import ClinicalPipeline
from backend.auth.rbac import UserRole, require_role
from backend.config import Settings, get_settings
from backend.db.repositories import message_repo, patient_repo, report_repo, user_repo
from backend.dependencies import get_db, get_llm_client, get_pipeline, get_vector_store
from backend.llm.openai_client import OpenAIClient
from backend.services import pipeline_trigger, report_service
from backend.services.report_service import ForbiddenError, NotFoundError
from backend.vectorstore.chroma_store import ChromaStore

router = APIRouter(prefix="/api/radiologist", tags=["radiologist"])
_require_radiologist = require_role(UserRole.RADIOLOGIST)


@router.get("/reports")
def list_my_uploads(user: dict = Depends(_require_radiologist), conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    return report_service.list_reports_by_uploader(conn, user["user_id"])


@router.get("/patients")
def list_patients(user: dict = Depends(_require_radiologist), conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    return [dict(p) for p in patient_repo.list_all(conn)]


@router.get("/doctors")
def list_doctors(user: dict = Depends(_require_radiologist), conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    return [{"id": u["id"], "full_name": u["full_name"], "email": u["email"]}
            for u in user_repo.list_by_role(conn, "doctor")]


@router.post("/reports/upload")
async def upload_report(
    background_tasks: BackgroundTasks,
    patient_id: int = Form(...),
    report_type: str = Form(...),
    category: str = Form(...),
    uploader_notes: str | None = Form(None),
    raw_text: str | None = Form(None),
    file: UploadFile | None = File(None),
    user: dict = Depends(_require_radiologist),
    conn: sqlite3.Connection = Depends(get_db),
    vector_store: ChromaStore = Depends(get_vector_store),
    llm_client: OpenAIClient = Depends(get_llm_client),
    settings: Settings = Depends(get_settings),
    pipeline: ClinicalPipeline = Depends(get_pipeline),
) -> dict:
    if not settings.openai_configured:
        raise HTTPException(status_code=503, detail="AI features unavailable: OPENAI_API_KEY is not configured.")
    if patient_repo.get_by_id(conn, patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    file_bytes = await file.read() if file else None
    original_filename = file.filename if file else None
    if not raw_text and not file_bytes:
        raise HTTPException(status_code=400, detail="Provide either raw_text or a file.")

    report_id = report_service.upload_report(
        conn, vector_store=vector_store, llm_client=llm_client, settings=settings,
        patient_id=patient_id, uploaded_by_user_id=user["user_id"],
        report_type=report_type, category=category, uploader_notes=uploader_notes,
        raw_text=raw_text, file_bytes=file_bytes, original_filename=original_filename,
    )
    background_tasks.add_task(
        pipeline_trigger.run_pipeline_in_background,
        database_path=settings.DATABASE_PATH, pipeline=pipeline, report_id=report_id,
    )
    return {"report_id": report_id, "status": "processing"}


@router.patch("/reports/{report_id}")
def correct_report(report_id: int, payload: dict, user: dict = Depends(_require_radiologist),
                    conn: sqlite3.Connection = Depends(get_db)) -> dict:
    try:
        report_service.update_report_correction(
            conn, report_id=report_id, uploader_user_id=user["user_id"],
            raw_text=payload.get("raw_text"), table_text=payload.get("table_text"),
            uploader_notes=payload.get("uploader_notes"),
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"ok": True}


@router.patch("/reports/{report_id}/status")
def update_status(report_id: int, payload: dict, user: dict = Depends(_require_radiologist),
                   conn: sqlite3.Connection = Depends(get_db)) -> dict:
    if report_repo.get_by_id(conn, report_id) is None:
        raise HTTPException(status_code=404, detail="Report not found")
    report_repo.update_status(conn, report_id, payload["status"])
    return {"ok": True}


@router.get("/messages")
def list_messages(patient_id: int | None = None, user: dict = Depends(_require_radiologist),
                   conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    if patient_id is not None:
        return [dict(m) for m in message_repo.list_for_patient(conn, patient_id)]
    return [dict(m) for m in message_repo.list_for_user(conn, user["user_id"])]


@router.post("/messages")
def send_message(payload: dict, user: dict = Depends(_require_radiologist),
                  conn: sqlite3.Connection = Depends(get_db)) -> dict:
    message_id = message_repo.send_message(
        conn, sender_user_id=user["user_id"], recipient_user_id=payload["recipient_user_id"],
        patient_id=payload["patient_id"], report_id=payload.get("report_id"), body=payload["body"],
    )
    return {"id": message_id}
