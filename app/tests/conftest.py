import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Must be set before `backend.main` (or anything importing backend.config) is
# imported anywhere in the test session, since Settings() reads env vars at
# first get_settings() call and the result is lru_cached. conftest.py is
# collected before test modules, so this runs first.
_TEST_DATA_DIR = Path(__file__).resolve().parent / "_test_data"
os.environ.setdefault("DATABASE_PATH", str(_TEST_DATA_DIR / "test.db"))
os.environ.setdefault("CHROMA_PERSIST_DIR", str(_TEST_DATA_DIR / "chroma_db"))
os.environ.setdefault("UPLOAD_DIR", str(_TEST_DATA_DIR / "uploads"))
os.environ.setdefault("SESSION_SECRET", "test-session-secret")

# Forced (not setdefault): a real .env with a real OPENAI_API_KEY may exist in
# app/ (e.g. after a developer has run scripts/seed_data.py against live
# services). pydantic-settings' precedence is process env > .env file, so
# without this the test suite would silently start making real, billed
# OpenAI API calls the moment settings.openai_configured is read — breaking
# this project's "no network/API key required" test guarantee. Tests that
# specifically need a configured key exercise it via mocked
# TracedAgent.invoke_llm / a fake OpenAIClient instance, never real settings.
os.environ["OPENAI_API_KEY"] = ""
os.environ["LANGFUSE_PUBLIC_KEY"] = ""
os.environ["LANGFUSE_SECRET_KEY"] = ""

from backend.db.database import get_connection, init_db  # noqa: E402


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


@pytest.fixture
def conn(db_path):
    connection = get_connection(db_path)
    yield connection
    connection.close()
