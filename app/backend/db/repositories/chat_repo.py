"""AI chatbot session/message history (backs both AI Health Assistant and AI Clinical Assistant)."""
import json
import sqlite3


def get_or_create_session(conn: sqlite3.Connection, *, user_id: int, patient_id: int, role: str) -> int:
    row = conn.execute(
        "SELECT id FROM chat_sessions WHERE user_id = ? AND patient_id = ? ORDER BY id DESC LIMIT 1",
        (user_id, patient_id),
    ).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO chat_sessions (user_id, patient_id, role) VALUES (?, ?, ?)",
        (user_id, patient_id, role),
    )
    conn.commit()
    return cur.lastrowid


def add_message(conn: sqlite3.Connection, *, chat_session_id: int, role: str, content: str,
                 retrieved_chunk_ids: list[str] | None = None) -> int:
    cur = conn.execute(
        "INSERT INTO chat_messages (chat_session_id, role, content, retrieved_chunk_ids_json) "
        "VALUES (?, ?, ?, ?)",
        (chat_session_id, role, content, json.dumps(retrieved_chunk_ids or [])),
    )
    conn.commit()
    return cur.lastrowid


def list_messages(conn: sqlite3.Connection, chat_session_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM chat_messages WHERE chat_session_id = ? ORDER BY created_at", (chat_session_id,)
    ).fetchall()
