"""Simulated appointment suggestion CRUD (no real calendar/EHR is ever contacted)."""
import sqlite3


def create_appointment(conn: sqlite3.Connection, *, patient_id: int, doctor_user_id: int | None,
                        alert_id: int | None, suggested_reason: str, proposed_datetime: str) -> int:
    cur = conn.execute(
        "INSERT INTO appointments (patient_id, doctor_user_id, alert_id, suggested_reason, proposed_datetime) "
        "VALUES (?, ?, ?, ?, ?)",
        (patient_id, doctor_user_id, alert_id, suggested_reason, proposed_datetime),
    )
    conn.commit()
    return cur.lastrowid


def get_by_id(conn: sqlite3.Connection, appointment_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,)).fetchone()


def list_by_patient(conn: sqlite3.Connection, patient_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT appointments.*, users.full_name AS doctor_name "
        "FROM appointments LEFT JOIN users ON users.id = appointments.doctor_user_id "
        "WHERE appointments.patient_id = ? ORDER BY appointments.proposed_datetime DESC",
        (patient_id,),
    ).fetchall()


def list_by_doctor(conn: sqlite3.Connection, doctor_user_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT appointments.*, patients.mrn, users.full_name AS patient_name "
        "FROM appointments "
        "JOIN patients ON patients.id = appointments.patient_id "
        "JOIN users ON users.id = patients.user_id "
        "WHERE appointments.doctor_user_id = ? AND appointments.status != 'cancelled' "
        "ORDER BY appointments.proposed_datetime ASC",
        (doctor_user_id,),
    ).fetchall()


def update_status(conn: sqlite3.Connection, appointment_id: int, status: str) -> None:
    conn.execute("UPDATE appointments SET status = ? WHERE id = ?", (status, appointment_id))
    conn.commit()


def list_booked_times(conn: sqlite3.Connection, doctor_user_id: int, date_str: str) -> list[str]:
    """HH:MM slots already taken for this doctor on this date (any non-cancelled appointment)."""
    rows = conn.execute(
        "SELECT proposed_datetime FROM appointments "
        "WHERE doctor_user_id = ? AND date(proposed_datetime) = ? AND status != 'cancelled'",
        (doctor_user_id, date_str),
    ).fetchall()
    return [r["proposed_datetime"][11:16] for r in rows]


def has_conflict(conn: sqlite3.Connection, doctor_user_id: int, proposed_datetime: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM appointments WHERE doctor_user_id = ? AND proposed_datetime = ? AND status != 'cancelled'",
        (doctor_user_id, proposed_datetime),
    ).fetchone()
    return row is not None
