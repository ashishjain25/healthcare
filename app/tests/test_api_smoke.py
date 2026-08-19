"""FastAPI TestClient smoke test against a seeded temp DB (env vars for
DATABASE_PATH/CHROMA_PERSIST_DIR/UPLOAD_DIR/SESSION_SECRET are set in
conftest.py before backend.main is ever imported). No OPENAI_API_KEY is
configured in this environment, which is itself exercised below: AI-calling
endpoints must degrade to 503, not crash.
"""
import shutil

import pytest
from fastapi.testclient import TestClient

from backend.auth.security import hash_password
from backend.config import get_settings
from backend.db.database import get_connection, init_db
from backend.db.repositories import patient_repo, user_repo
from backend.main import app


@pytest.fixture(scope="module", autouse=True)
def _clean_test_data():
    settings = get_settings()
    yield
    for path in (settings.DATABASE_PATH, settings.CHROMA_PERSIST_DIR, settings.UPLOAD_DIR):
        p = __import__("pathlib").Path(path)
        if p.is_file():
            p.unlink(missing_ok=True)
        elif p.is_dir():
            shutil.rmtree(p, ignore_errors=True)


@pytest.fixture(scope="module")
def seeded_users():
    settings = get_settings()
    init_db(settings.DATABASE_PATH)
    conn = get_connection(settings.DATABASE_PATH)

    doctor_hash, doctor_salt = hash_password("password123")
    doctor_id = user_repo.create_user(
        conn, email="doctor@cis.com", password_hash=doctor_hash, password_salt=doctor_salt,
        full_name="Dr. Smoke Test", role="doctor",
    )

    radiologist_hash, radiologist_salt = hash_password("password123")
    radiologist_id = user_repo.create_user(
        conn, email="radiologist@cis.com", password_hash=radiologist_hash, password_salt=radiologist_salt,
        full_name="Rad Smoke Test", role="radiologist",
    )

    patient_user_hash, patient_user_salt = hash_password("password123")
    patient_user_id = user_repo.create_user(
        conn, email="patient@cis.com", password_hash=patient_user_hash, password_salt=patient_user_salt,
        full_name="Pat Smoke Test", role="patient",
    )
    patient_id = patient_repo.create_patient(
        conn, user_id=patient_user_id, mrn="SMOKE-001", dob="1990-01-01", sex="F",
        blood_group="O+", known_conditions=None, primary_doctor_id=doctor_id,
    )
    conn.close()
    return {"doctor_id": doctor_id, "radiologist_id": radiologist_id,
            "patient_user_id": patient_user_id, "patient_id": patient_id}


def _login(client: TestClient, email: str) -> dict:
    resp = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_login_each_role_and_me(seeded_users):
    with TestClient(app) as client:
        for email, role in [("doctor@cis.com", "doctor"),
                             ("radiologist@cis.com", "radiologist"),
                             ("patient@cis.com", "patient")]:
            user = _login(client, email)
            assert user["role"] == role
            me = client.get("/api/auth/me")
            assert me.status_code == 200
            assert me.json()["role"] == role
            client.post("/api/auth/logout")


def test_login_wrong_password_rejected(seeded_users):
    with TestClient(app) as client:
        resp = client.post("/api/auth/login", json={"email": "doctor@cis.com", "password": "wrong"})
        assert resp.status_code == 401


def test_unauthenticated_request_returns_401(seeded_users):
    with TestClient(app) as client:
        resp = client.get("/api/doctor/patients")
        assert resp.status_code == 401


def test_patient_cannot_access_doctor_routes(seeded_users):
    with TestClient(app) as client:
        _login(client, "patient@cis.com")
        resp = client.get("/api/doctor/patients")
        assert resp.status_code == 403


def test_doctor_can_list_patients_and_reports(seeded_users):
    with TestClient(app) as client:
        _login(client, "doctor@cis.com")
        resp = client.get("/api/doctor/patients")
        assert resp.status_code == 200
        assert any(p["mrn"] == "SMOKE-001" for p in resp.json())

        resp2 = client.get("/api/doctor/reports")
        assert resp2.status_code == 200


def test_patient_can_list_own_reports_and_history(seeded_users):
    with TestClient(app) as client:
        _login(client, "patient@cis.com")
        resp = client.get("/api/patient/reports")
        assert resp.status_code == 200
        assert resp.json() == []

        resp2 = client.get("/api/patient/history")
        assert resp2.status_code == 200
        assert resp2.json()["allergies"] == []


def test_upload_without_openai_key_returns_503(seeded_users):
    """Proves the graceful-degradation contract: with no OPENAI_API_KEY configured
    (true in this test environment), AI-calling endpoints must return a clear 503
    rather than raising an unhandled exception."""
    with TestClient(app) as client:
        _login(client, "patient@cis.com")
        resp = client.post(
            "/api/patient/reports/upload",
            data={"report_type": "lab", "category": "cbc", "raw_text": "Hemoglobin: 13.5 g/dL"},
        )
        assert resp.status_code == 503


def test_doctor_compare_route_not_shadowed_by_report_id_path(seeded_users):
    """Regression test: /reports/compare must not be matched by the dynamic
    /reports/{report_id} route registered elsewhere in the router (a real bug
    caught during manual verification — route order matters in FastAPI)."""
    with TestClient(app) as client:
        _login(client, "doctor@cis.com")
        resp = client.get("/api/doctor/reports/compare?a=1&b=2")
        assert resp.status_code in (200, 404)  # never 422 (path-param parse failure)


def test_radiologist_can_list_own_uploads_and_patients(seeded_users):
    with TestClient(app) as client:
        _login(client, "radiologist@cis.com")
        resp = client.get("/api/radiologist/reports")
        assert resp.status_code == 200
        resp2 = client.get("/api/radiologist/patients")
        assert resp2.status_code == 200


@pytest.mark.parametrize("path", ["/login", "/patient", "/doctor", "/radiologist"])
def test_page_shells_render(seeded_users, path):
    with TestClient(app) as client:
        resp = client.get(path)
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
