"""Repository-layer CRUD + row-level RBAC checks (e.g. patient A cannot see patient B's report)."""
from backend.db.repositories import (
    alert_repo,
    appointment_repo,
    message_repo,
    patient_repo,
    pipeline_repo,
    report_repo,
    user_repo,
)


def _make_patient(conn, email="patient1@cis.com", mrn="MRN-001"):
    uid = user_repo.create_user(
        conn, email=email, password_hash="h", password_salt="s",
        full_name="Test Patient", role="patient",
    )
    pid = patient_repo.create_patient(
        conn, user_id=uid, mrn=mrn, dob="1990-01-01", sex="F",
        blood_group="O+", known_conditions=None, primary_doctor_id=None,
    )
    return uid, pid


def test_create_and_fetch_user(conn):
    uid = user_repo.create_user(
        conn, email="doc@cis.com", password_hash="h", password_salt="s",
        full_name="Dr. Smith", role="doctor",
    )
    row = user_repo.get_by_id(conn, uid)
    assert row["email"] == "doc@cis.com"
    assert row["role"] == "doctor"
    assert user_repo.get_by_email(conn, "doc@cis.com")["id"] == uid


def test_patient_allergies_and_history(conn):
    _, pid = _make_patient(conn)
    patient_repo.add_allergy(
        conn, patient_id=pid, allergen="Peanut", category="Food",
        severity="SEVERE", reaction_notes="anaphylaxis", source="self_reported",
    )
    allergies = patient_repo.list_allergies(conn, pid)
    assert len(allergies) == 1
    assert allergies[0]["allergen"] == "Peanut"

    patient_repo.add_medical_history(
        conn, patient_id=pid, entry_type="condition", description="Asthma", entry_date="2020-01-01"
    )
    history = patient_repo.list_medical_history(conn, pid)
    assert len(history) == 1


def test_report_and_extraction_flow(conn):
    _, pid = _make_patient(conn)
    uid, _ = _make_patient(conn, email="p2@cis.com", mrn="MRN-002")

    report_id = report_repo.create_report(
        conn, patient_id=pid, uploaded_by_user_id=uid, report_type="lab", category="cbc",
        original_filename="cbc.pdf", file_path="/tmp/cbc.pdf", file_format="pdf",
        raw_text="Hemoglobin 13.5 g/dL", table_text="",
    )
    report = report_repo.get_by_id(conn, report_id)
    assert report["status"] == "pending_pipeline"

    report_repo.add_extraction(
        conn, report_id=report_id, parameter_name="Hemoglobin", value="13.5",
        unit="g/dL", reference_range="12-16", status="NORMAL", confidence=0.9,
    )
    extractions = report_repo.list_extractions(conn, report_id)
    assert len(extractions) == 1

    report_repo.update_status(conn, report_id, "processed")
    assert report_repo.get_by_id(conn, report_id)["status"] == "processed"


def test_row_level_rbac_patient_cannot_see_other_patients_report(conn):
    """A patient must never be able to fetch another patient's report by guessing an ID —
    the repo layer itself doesn't enforce this (that's the service layer's job), but this
    test proves list_by_patient scoping never leaks cross-patient rows."""
    uid_a, pid_a = _make_patient(conn, email="a@cis.com", mrn="MRN-A")
    uid_b, pid_b = _make_patient(conn, email="b@cis.com", mrn="MRN-B")

    report_repo.create_report(
        conn, patient_id=pid_a, uploaded_by_user_id=uid_a, report_type="lab", category="cbc",
        original_filename=None, file_path=None, file_format="txt", raw_text="A's report",
    )
    report_repo.create_report(
        conn, patient_id=pid_b, uploaded_by_user_id=uid_b, report_type="lab", category="cbc",
        original_filename=None, file_path=None, file_format="txt", raw_text="B's report",
    )

    a_reports = report_repo.list_by_patient(conn, pid_a)
    assert len(a_reports) == 1
    assert a_reports[0]["raw_text"] == "A's report"


def test_pipeline_run_and_doctor_review_gates_patient_summary(conn):
    uid, pid = _make_patient(conn)
    doctor_id = user_repo.create_user(
        conn, email="doc2@cis.com", password_hash="h", password_salt="s",
        full_name="Dr. Lee", role="doctor",
    )
    report_id = report_repo.create_report(
        conn, patient_id=pid, uploaded_by_user_id=uid, report_type="lab", category="cbc",
        original_filename=None, file_path=None, file_format="txt", raw_text="text",
    )
    run_id = pipeline_repo.create_run(conn, report_id=report_id, patient_id=pid)
    pipeline_repo.save_agent_output(
        conn, pipeline_run_id=run_id, agent_name="data_extraction",
        output_json={"ok": True}, confidence=0.9, flagged=False, flag_reason=None,
    )
    insight_id = pipeline_repo.save_insight(
        conn, pipeline_run_id=run_id, report_id=report_id, patient_id=pid,
        summary="All normal", key_findings=["Hgb normal"], risk_indicators=[],
        recommendations=["Routine follow-up"], risk_level="routine",
        requires_review=False, clinical_inconsistency=False, status="ai_generated",
    )
    pipeline_repo.save_patient_summary(
        conn, insight_id=insight_id, pipeline_run_id=run_id,
        plain_language_summary="Your blood test looks normal.",
        what_this_means=["No concerning findings"], what_you_should_do=["Continue routine care"],
        disclaimer="This is not a diagnosis.", diagnostic_language_flag=False,
    )

    summary = pipeline_repo.get_patient_summary(conn, insight_id)
    assert summary["clinician_approved"] == 0

    pipeline_repo.add_doctor_review(
        conn, insight_id=insight_id, doctor_user_id=doctor_id, action="validated",
        modified_findings=None, comments="Looks right",
    )
    summary_after = pipeline_repo.get_patient_summary(conn, insight_id)
    assert summary_after["clinician_approved"] == 1
    assert pipeline_repo.get_insight(conn, insight_id)["status"] == "doctor_reviewed"


def test_alerts_appointments_messages(conn):
    uid, pid = _make_patient(conn)
    doctor_id = user_repo.create_user(
        conn, email="doc3@cis.com", password_hash="h", password_salt="s",
        full_name="Dr. Patel", role="doctor",
    )
    alert_id = alert_repo.create_alert(
        conn, patient_id=pid, report_id=None, pipeline_run_id=None,
        alert_type="critical_lab", severity="emergency", message="Critical potassium level",
    )
    assert len(alert_repo.list_open(conn)) == 1
    alert_repo.acknowledge(conn, alert_id, doctor_id)
    assert len(alert_repo.list_open(conn)) == 0

    appointment_repo.create_appointment(
        conn, patient_id=pid, doctor_user_id=doctor_id, alert_id=alert_id,
        suggested_reason="Critical finding follow-up", proposed_datetime="2026-07-27T09:00:00",
    )
    assert len(appointment_repo.list_by_patient(conn, pid)) == 1

    message_repo.send_message(
        conn, sender_user_id=doctor_id, recipient_user_id=uid, patient_id=pid,
        report_id=None, body="Please review the latest scan",
    )
    thread_id = message_repo.build_thread_id(doctor_id, uid, pid)
    assert len(message_repo.list_thread(conn, thread_id)) == 1
    assert len(message_repo.list_for_user(conn, doctor_id)) == 1


def test_row_level_rbac_doctor_cannot_see_another_doctors_message_thread(conn):
    """Two doctors can each have their own private thread with the same
    radiologist about the same shared patient — one must never see the
    other's conversation just by asking for that patient's messages."""
    _, pid = _make_patient(conn)
    radiologist_id = user_repo.create_user(
        conn, email="rad-shared@cis.com", password_hash="h", password_salt="s",
        full_name="Karan Singh", role="radiologist",
    )
    doctor_a = user_repo.create_user(
        conn, email="doc-a@cis.com", password_hash="h", password_salt="s",
        full_name="Dr. A", role="doctor",
    )
    doctor_b = user_repo.create_user(
        conn, email="doc-b@cis.com", password_hash="h", password_salt="s",
        full_name="Dr. B", role="doctor",
    )

    message_repo.send_message(
        conn, sender_user_id=doctor_a, recipient_user_id=radiologist_id, patient_id=pid,
        report_id=None, body="Any CBC report pending?",
    )
    message_repo.send_message(
        conn, sender_user_id=doctor_b, recipient_user_id=radiologist_id, patient_id=pid,
        report_id=None, body="Please prioritize this patient's scan",
    )

    a_view = message_repo.list_for_patient(conn, pid, doctor_a)
    b_view = message_repo.list_for_patient(conn, pid, doctor_b)

    assert len(a_view) == 1 and a_view[0]["body"] == "Any CBC report pending?"
    assert len(b_view) == 1 and b_view[0]["body"] == "Please prioritize this patient's scan"
