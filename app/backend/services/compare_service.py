"""Field-by-field report comparison (Patient/Doctor 'compare previous and
latest reports' action from the PDF's actor list)."""
import sqlite3
from typing import Any

from backend.db.repositories import report_repo
from backend.services.report_service import ForbiddenError, NotFoundError


class CategoryMismatchError(Exception):
    pass


def compare_reports(conn: sqlite3.Connection, report_id_a: int, report_id_b: int,
                     *, patient_id: int | None = None) -> dict[str, Any]:
    report_a = report_repo.get_by_id(conn, report_id_a)
    report_b = report_repo.get_by_id(conn, report_id_b)
    if report_a is None or report_b is None:
        raise NotFoundError("One or both reports not found")
    if patient_id is not None and (report_a["patient_id"] != patient_id or report_b["patient_id"] != patient_id):
        raise ForbiddenError("Reports do not belong to the current patient")
    if report_a["category"] != report_b["category"]:
        raise CategoryMismatchError(
            "Reports must be the same investigation type to compare "
            f"(got '{report_a['category']}' and '{report_b['category']}')"
        )

    # Order chronologically regardless of argument order.
    earlier, later = sorted((report_a, report_b), key=lambda r: r["uploaded_at"])

    extractions_earlier = {e["parameter_name"]: e for e in report_repo.list_extractions(conn, earlier["id"])}
    extractions_later = {e["parameter_name"]: e for e in report_repo.list_extractions(conn, later["id"])}

    rows = []
    for name in sorted(set(extractions_earlier) | set(extractions_later)):
        e = extractions_earlier.get(name)
        l = extractions_later.get(name)
        rows.append({
            "parameter": name,
            "earlier": {"value": e["value"], "unit": e["unit"], "status": e["status"]} if e else None,
            "later": {"value": l["value"], "unit": l["unit"], "status": l["status"]} if l else None,
            "changed": (e["value"] if e else None) != (l["value"] if l else None),
        })

    return {
        "earlier_report": dict(earlier),
        "later_report": dict(later),
        "rows": rows,
    }
