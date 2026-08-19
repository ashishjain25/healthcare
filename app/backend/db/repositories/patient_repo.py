"""Patient profile, allergies, and medical history CRUD."""
import sqlite3


def create_patient(conn: sqlite3.Connection, *, user_id: int, mrn: str, dob: str | None,
                    sex: str | None, blood_group: str | None, known_conditions: str | None,
                    primary_doctor_id: int | None) -> int:
    cur = conn.execute(
        "INSERT INTO patients (user_id, mrn, dob, sex, blood_group, known_conditions, primary_doctor_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, mrn, dob, sex, blood_group, known_conditions, primary_doctor_id),
    )
    conn.commit()
    return cur.lastrowid


def get_by_id(conn: sqlite3.Connection, patient_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT patients.*, users.full_name, users.email "
        "FROM patients JOIN users ON users.id = patients.user_id "
        "WHERE patients.id = ?",
        (patient_id,),
    ).fetchone()


def get_by_user_id(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT patients.*, users.full_name, users.email "
        "FROM patients JOIN users ON users.id = patients.user_id "
        "WHERE patients.user_id = ?",
        (user_id,),
    ).fetchone()


def list_all(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT patients.*, users.full_name, users.email "
        "FROM patients JOIN users ON users.id = patients.user_id "
        "ORDER BY users.full_name"
    ).fetchall()


def add_allergy(conn: sqlite3.Connection, *, patient_id: int, allergen: str, category: str,
                 severity: str | None, reaction_notes: str | None, source: str = "self_reported") -> int:
    cur = conn.execute(
        "INSERT INTO allergies (patient_id, allergen, category, severity, reaction_notes, source) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (patient_id, allergen, category, severity, reaction_notes, source),
    )
    conn.commit()
    return cur.lastrowid


def list_allergies(conn: sqlite3.Connection, patient_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM allergies WHERE patient_id = ? ORDER BY created_at DESC", (patient_id,)
    ).fetchall()


def add_medical_history(conn: sqlite3.Connection, *, patient_id: int, entry_type: str,
                         description: str, entry_date: str | None) -> int:
    cur = conn.execute(
        "INSERT INTO medical_history (patient_id, entry_type, description, entry_date) "
        "VALUES (?, ?, ?, ?)",
        (patient_id, entry_type, description, entry_date),
    )
    conn.commit()
    return cur.lastrowid


def list_medical_history(conn: sqlite3.Connection, patient_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM medical_history WHERE patient_id = ? ORDER BY entry_date DESC, created_at DESC",
        (patient_id,),
    ).fetchall()
