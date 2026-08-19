"""User account CRUD."""
import sqlite3


def create_user(conn: sqlite3.Connection, *, email: str, password_hash: str,
                 password_salt: str, full_name: str, role: str) -> int:
    cur = conn.execute(
        "INSERT INTO users (email, password_hash, password_salt, full_name, role) "
        "VALUES (?, ?, ?, ?, ?)",
        (email, password_hash, password_salt, full_name, role),
    )
    conn.commit()
    return cur.lastrowid


def get_by_email(conn: sqlite3.Connection, email: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def get_by_id(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def list_by_role(conn: sqlite3.Connection, role: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM users WHERE role = ? ORDER BY full_name", (role,)
    ).fetchall()
