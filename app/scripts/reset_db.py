"""Recreates data/cis.db from schema.sql. Run from the app/ directory:
    python scripts/reset_db.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import get_settings  # noqa: E402
from backend.db.database import init_db  # noqa: E402


def main() -> None:
    settings = get_settings()
    db_path = Path(settings.DATABASE_PATH)
    if db_path.exists():
        db_path.unlink()
        print(f"Removed existing database at {db_path}")
    init_db(settings.DATABASE_PATH)
    print(f"Initialized fresh database at {settings.DATABASE_PATH}")


if __name__ == "__main__":
    main()
