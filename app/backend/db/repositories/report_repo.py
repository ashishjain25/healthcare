"""Diagnostic report CRUD + per-parameter extraction rows (used for compare)."""
import sqlite3


def create_report(conn: sqlite3.Connection, *, patient_id: int, uploaded_by_user_id: int,
                   report_type: str, category: str, original_filename: str | None,
                   file_path: str | None, file_format: str | None, raw_text: str,
                   table_text: str = "", uploader_notes: str | None = None) -> int:
    cur = conn.execute(
        "INSERT INTO reports (patient_id, uploaded_by_user_id, report_type, category, "
        "original_filename, file_path, file_format, raw_text, table_text, uploader_notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (patient_id, uploaded_by_user_id, report_type, category, original_filename,
         file_path, file_format, raw_text, table_text, uploader_notes),
    )
    conn.commit()
    return cur.lastrowid


def get_by_id(conn: sqlite3.Connection, report_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()


def list_by_patient(conn: sqlite3.Connection, patient_id: int, category: str | None = None) -> list[sqlite3.Row]:
    if category:
        return conn.execute(
            "SELECT * FROM reports WHERE patient_id = ? AND category = ? ORDER BY uploaded_at DESC",
            (patient_id, category),
        ).fetchall()
    return conn.execute(
        "SELECT * FROM reports WHERE patient_id = ? ORDER BY uploaded_at DESC", (patient_id,)
    ).fetchall()


def list_all(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT reports.*, patients.mrn, users.full_name AS patient_name "
        "FROM reports JOIN patients ON patients.id = reports.patient_id "
        "JOIN users ON users.id = patients.user_id "
        "ORDER BY reports.uploaded_at DESC"
    ).fetchall()


def list_by_uploader(conn: sqlite3.Connection, uploaded_by_user_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT reports.*, patients.mrn, users.full_name AS patient_name "
        "FROM reports JOIN patients ON patients.id = reports.patient_id "
        "JOIN users ON users.id = patients.user_id "
        "WHERE reports.uploaded_by_user_id = ? ORDER BY reports.uploaded_at DESC",
        (uploaded_by_user_id,),
    ).fetchall()


def update_status(conn: sqlite3.Connection, report_id: int, status: str) -> None:
    conn.execute(
        "UPDATE reports SET status = ?, updated_at = datetime('now') WHERE id = ?",
        (status, report_id),
    )
    conn.commit()


def update_report_content(conn: sqlite3.Connection, report_id: int, *, raw_text: str | None = None,
                           table_text: str | None = None, uploader_notes: str | None = None) -> None:
    fields, values = [], []
    if raw_text is not None:
        fields.append("raw_text = ?")
        values.append(raw_text)
    if table_text is not None:
        fields.append("table_text = ?")
        values.append(table_text)
    if uploader_notes is not None:
        fields.append("uploader_notes = ?")
        values.append(uploader_notes)
    if not fields:
        return
    fields.append("updated_at = datetime('now')")
    values.append(report_id)
    conn.execute(f"UPDATE reports SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()


def add_extraction(conn: sqlite3.Connection, *, report_id: int, parameter_name: str, value: str,
                    unit: str | None, reference_range: str | None, status: str, confidence: float) -> int:
    cur = conn.execute(
        "INSERT INTO report_extractions (report_id, parameter_name, value, unit, reference_range, status, confidence) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (report_id, parameter_name, value, unit, reference_range, status, confidence),
    )
    conn.commit()
    return cur.lastrowid


def list_extractions(conn: sqlite3.Connection, report_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM report_extractions WHERE report_id = ? ORDER BY parameter_name", (report_id,)
    ).fetchall()


def list_previous_reports(conn: sqlite3.Connection, patient_id: int, category: str,
                           before_report_id: int, limit: int = 3) -> list[sqlite3.Row]:
    """Prior reports of the same category for this patient, oldest exclusion of the
    current report — feeds the Insight Generation Agent's historical-comparison step."""
    return conn.execute(
        "SELECT * FROM reports WHERE patient_id = ? AND category = ? AND id != ? "
        "AND status = 'processed' ORDER BY uploaded_at DESC LIMIT ?",
        (patient_id, category, before_report_id, limit),
    ).fetchall()
