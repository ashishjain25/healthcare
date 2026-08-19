"""Clinical alert CRUD (critical findings surfaced to doctors)."""
import sqlite3


def create_alert(conn: sqlite3.Connection, *, patient_id: int, report_id: int | None,
                  pipeline_run_id: int | None, alert_type: str, severity: str, message: str) -> int:
    cur = conn.execute(
        "INSERT INTO alerts (patient_id, report_id, pipeline_run_id, alert_type, severity, message) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (patient_id, report_id, pipeline_run_id, alert_type, severity, message),
    )
    conn.commit()
    return cur.lastrowid


def get_by_id(conn: sqlite3.Connection, alert_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()


def list_by_patient(conn: sqlite3.Connection, patient_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM alerts WHERE patient_id = ? ORDER BY created_at DESC", (patient_id,)
    ).fetchall()


def list_open(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT alerts.*, patients.mrn, users.full_name AS patient_name "
        "FROM alerts JOIN patients ON patients.id = alerts.patient_id "
        "JOIN users ON users.id = patients.user_id "
        "WHERE alerts.status = 'open' ORDER BY alerts.created_at DESC"
    ).fetchall()


def acknowledge(conn: sqlite3.Connection, alert_id: int, user_id: int) -> None:
    conn.execute(
        "UPDATE alerts SET status = 'acknowledged', acknowledged_by_user_id = ?, "
        "acknowledged_at = datetime('now') WHERE id = ?",
        (user_id, alert_id),
    )
    conn.commit()
