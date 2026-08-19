"""Report upload, retrieval, and role-scoped view assembly. Row-level RBAC
enforcement lives here (not just the router): a patient can never fetch
another patient's report by guessing an ID, and the plain-language summary
is withheld until a doctor has approved it — independent of what the
Patient Communication agent claimed about itself.
"""
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.config import Settings
from backend.db.repositories import pipeline_repo, report_repo
from backend.documents.processor import DocumentProcessor
from backend.llm.openai_client import OpenAIClient
from backend.vectorstore.chroma_store import ChromaStore


class NotFoundError(Exception):
    pass


class ForbiddenError(Exception):
    pass


def upload_report(conn: sqlite3.Connection, *, vector_store: ChromaStore, llm_client: OpenAIClient,
                   settings: Settings, patient_id: int, uploaded_by_user_id: int, report_type: str,
                   category: str, uploader_notes: str | None = None, raw_text: str | None = None,
                   file_bytes: bytes | None = None, original_filename: str | None = None) -> int:
    file_path = None
    file_format = "txt"
    table_text = ""

    if file_bytes is not None and original_filename:
        suffix = Path(original_filename).suffix.lower().lstrip(".")
        file_format = suffix if suffix in ("docx", "pdf") else "txt"

        upload_dir = Path(settings.UPLOAD_DIR) / str(patient_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        dest = upload_dir / f"{uuid.uuid4().hex}_{original_filename}"
        dest.write_bytes(file_bytes)
        file_path = str(dest)

        if file_format in ("docx", "pdf"):
            parsed = DocumentProcessor().process_file(dest)
            if parsed:
                raw_text = parsed["full_text"]
                table_text = parsed["table_text"]
            else:
                raw_text = raw_text or ""
        else:
            raw_text = file_bytes.decode("utf-8", errors="replace")
    else:
        raw_text = raw_text or ""

    report_id = report_repo.create_report(
        conn, patient_id=patient_id, uploaded_by_user_id=uploaded_by_user_id,
        report_type=report_type, category=category, original_filename=original_filename,
        file_path=file_path, file_format=file_format, raw_text=raw_text, table_text=table_text,
        uploader_notes=uploader_notes,
    )

    full_text = f"{raw_text}\n{table_text}".strip()
    if full_text:
        vector_store.add_document(
            "patient_reports", doc_id=f"report-{report_id}", text=full_text,
            metadata={
                "patient_id": patient_id, "report_id": report_id, "report_type": report_type,
                "category": category, "report_date": datetime.now(timezone.utc).isoformat(),
            },
            embed_fn=llm_client.embed,
        )
    return report_id


def _report_to_dict(report: sqlite3.Row) -> dict[str, Any]:
    return dict(report)


def get_patient_report_view(conn: sqlite3.Connection, report_id: int, patient_id: int) -> dict[str, Any]:
    report = report_repo.get_by_id(conn, report_id)
    if report is None:
        raise NotFoundError(f"Report {report_id} not found")
    if report["patient_id"] != patient_id:
        raise ForbiddenError("This report does not belong to the current patient")

    result = _report_to_dict(report)
    result["extractions"] = [dict(e) for e in report_repo.list_extractions(conn, report_id)]

    insight = pipeline_repo.get_insight_by_report(conn, report_id)
    if insight is None:
        result["insight"] = None
        return result

    result["insight"] = {
        "id": insight["id"], "risk_level": insight["risk_level"], "status": insight["status"],
        "key_findings": json.loads(insight["key_findings_json"]),
        "risk_indicators": json.loads(insight["risk_indicators_json"]),
        "recommendations": json.loads(insight["recommendations_json"]),
    }

    summary = pipeline_repo.get_patient_summary(conn, insight["id"])
    if summary and summary["clinician_approved"]:
        result["patient_summary"] = {
            "plain_language_summary": summary["plain_language_summary"],
            "what_this_means": json.loads(summary["what_this_means_json"]),
            "what_you_should_do": json.loads(summary["what_you_should_do_json"]),
            "disclaimer": summary["disclaimer"],
        }
    else:
        result["patient_summary"] = None
        result["patient_summary_pending_review"] = summary is not None

    result["doctor_reviews"] = [
        {
            "id": r["id"], "action": r["action"], "comments": r["comments"],
            "doctor_name": r["doctor_name"], "created_at": r["created_at"],
        }
        for r in pipeline_repo.list_doctor_reviews(conn, insight["id"])
    ]
    return result


def get_doctor_report_view(conn: sqlite3.Connection, report_id: int) -> dict[str, Any]:
    report = report_repo.get_by_id(conn, report_id)
    if report is None:
        raise NotFoundError(f"Report {report_id} not found")

    result = _report_to_dict(report)
    result["extractions"] = [dict(e) for e in report_repo.list_extractions(conn, report_id)]

    run = pipeline_repo.get_run_by_report(conn, report_id)
    result["pipeline_run"] = dict(run) if run else None
    result["agent_outputs"] = (
        [{**dict(row), "output_json": json.loads(row["output_json"])}
         for row in pipeline_repo.list_agent_outputs(conn, run["id"])]
        if run else []
    )

    insight = pipeline_repo.get_insight_by_report(conn, report_id)
    if insight is None:
        result["insight"] = None
        return result

    result["insight"] = {
        "id": insight["id"], "risk_level": insight["risk_level"], "status": insight["status"],
        "requires_review": bool(insight["requires_review"]),
        "clinical_inconsistency": bool(insight["clinical_inconsistency"]),
        "key_findings": json.loads(insight["key_findings_json"]),
        "risk_indicators": json.loads(insight["risk_indicators_json"]),
        "recommendations": json.loads(insight["recommendations_json"]),
    }
    summary = pipeline_repo.get_patient_summary(conn, insight["id"])
    result["patient_summary"] = dict(summary) if summary else None
    result["doctor_reviews"] = [dict(r) for r in pipeline_repo.list_doctor_reviews(conn, insight["id"])]
    return result


def list_patient_reports(conn: sqlite3.Connection, patient_id: int) -> list[dict]:
    return [dict(r) for r in report_repo.list_by_patient(conn, patient_id)]


def list_all_reports(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in report_repo.list_all(conn)]


def list_reports_by_uploader(conn: sqlite3.Connection, uploader_user_id: int) -> list[dict]:
    return [dict(r) for r in report_repo.list_by_uploader(conn, uploader_user_id)]


def update_report_correction(conn: sqlite3.Connection, *, report_id: int, uploader_user_id: int,
                              raw_text: str | None = None, table_text: str | None = None,
                              uploader_notes: str | None = None) -> None:
    report = report_repo.get_by_id(conn, report_id)
    if report is None:
        raise NotFoundError(f"Report {report_id} not found")
    if report["uploaded_by_user_id"] != uploader_user_id:
        raise ForbiddenError("Only the original uploader can correct this report")
    report_repo.update_report_content(
        conn, report_id, raw_text=raw_text, table_text=table_text, uploader_notes=uploader_notes,
    )
