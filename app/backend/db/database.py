"""SQLite connection factory + schema initialization.

No ORM: repositories issue plain SQL against sqlite3.Row-factory connections.
This keeps the data layer transparent and matches the project's scale.
"""
import sqlite3
from pathlib import Path

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection(database_path: str) -> sqlite3.Connection:
    db_path = Path(database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: FastAPI's `get_db` dependency (a sync generator)
    # is resolved in a threadpool thread even when the endpoint itself is
    # `async def` (e.g. the upload endpoints, which need `await file.read()`),
    # so the connection is created on one thread and used on another. That
    # handoff is sequential, never concurrent, within a single request's
    # lifecycle, so disabling sqlite3's same-thread check is safe here.
    conn = sqlite3.connect(database_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(database_path: str) -> None:
    conn = get_connection(database_path)
    try:
        schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()
