"""Doctor <-> radiologist (or any two users) in-app messaging, grouped by patient."""
import sqlite3


def build_thread_id(user_a: int, user_b: int, patient_id: int) -> str:
    lo, hi = sorted((user_a, user_b))
    return f"{lo}_{hi}_{patient_id}"


def send_message(conn: sqlite3.Connection, *, sender_user_id: int, recipient_user_id: int,
                  patient_id: int, report_id: int | None, body: str) -> int:
    thread_id = build_thread_id(sender_user_id, recipient_user_id, patient_id)
    cur = conn.execute(
        "INSERT INTO messages (thread_id, sender_user_id, recipient_user_id, patient_id, report_id, body) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (thread_id, sender_user_id, recipient_user_id, patient_id, report_id, body),
    )
    conn.commit()
    return cur.lastrowid


def list_thread(conn: sqlite3.Connection, thread_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM messages WHERE thread_id = ? ORDER BY created_at", (thread_id,)
    ).fetchall()


def list_for_user(conn: sqlite3.Connection, user_id: int) -> list[sqlite3.Row]:
    """All messages involving this user, newest first — used to build a thread/inbox list."""
    return conn.execute(
        "SELECT messages.*, u_sender.full_name AS sender_name, u_recipient.full_name AS recipient_name, "
        "patients.mrn, u_patient.full_name AS patient_name "
        "FROM messages "
        "JOIN users u_sender ON u_sender.id = messages.sender_user_id "
        "JOIN users u_recipient ON u_recipient.id = messages.recipient_user_id "
        "JOIN patients ON patients.id = messages.patient_id "
        "JOIN users u_patient ON u_patient.id = patients.user_id "
        "WHERE messages.sender_user_id = ? OR messages.recipient_user_id = ? "
        "ORDER BY messages.created_at DESC",
        (user_id, user_id),
    ).fetchall()


def list_for_patient(conn: sqlite3.Connection, patient_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT messages.*, u_sender.full_name AS sender_name, u_recipient.full_name AS recipient_name "
        "FROM messages "
        "JOIN users u_sender ON u_sender.id = messages.sender_user_id "
        "JOIN users u_recipient ON u_recipient.id = messages.recipient_user_id "
        "WHERE messages.patient_id = ? ORDER BY messages.created_at",
        (patient_id,),
    ).fetchall()


def mark_read(conn: sqlite3.Connection, message_id: int) -> None:
    conn.execute("UPDATE messages SET read_at = datetime('now') WHERE id = ?", (message_id,))
    conn.commit()
