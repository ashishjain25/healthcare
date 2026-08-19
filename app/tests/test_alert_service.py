"""Regression coverage for alert_type classification — a real bug caught
during manual verification against live GPT-4o-mini output: a patient's
on-file allergy showing up as an unrelated, non-critical risk_flag caused an
otherwise purely cardiac critical-lab alert to be mislabeled 'allergy_risk'."""
from backend.agents.schemas import RiskDetectionOutput
from backend.db.repositories import alert_repo, patient_repo, report_repo, user_repo
from backend.services import alert_service


def _seed_patient(conn, email="alert-test@cis.com", mrn="ALERT-001"):
    uid = user_repo.create_user(conn, email=email, password_hash="h", password_salt="s",
                                 full_name="Alert Test Patient", role="patient")
    pid = patient_repo.create_patient(conn, user_id=uid, mrn=mrn, dob="1990-01-01", sex="F",
                                       blood_group="O+", known_conditions=None, primary_doctor_id=None)
    rid = report_repo.create_report(conn, patient_id=pid, uploaded_by_user_id=uid, report_type="lab",
                                     category="cardiac", original_filename=None, file_path=None,
                                     file_format="txt", raw_text="Troponin I critically elevated")
    return pid, rid


def test_unrelated_allergy_flag_does_not_relabel_critical_lab_alert(conn):
    patient_id, report_id = _seed_patient(conn)

    risk_detection = RiskDetectionOutput(
        risk_flags=[
            {
                "source_parameter": "Troponin I", "risk_level": "critical",
                "crosses_critical_threshold": True,
                "rationale": "Critical elevation of Troponin I indicates acute myocardial injury.",
                "cross_reactive_allergens": [],
            },
            {
                "source_parameter": "peanut", "risk_level": "low", "crosses_critical_threshold": False,
                "rationale": "Patient has a documented peanut allergy on file.",
                "cross_reactive_allergens": ["tree_nuts", "legumes", "lupin"],
            },
        ],
        overall_risk_level="emergency", requires_immediate_escalation=True, risk_confidence=0.9,
    )

    alert_id = alert_service.create_alert_from_risk(
        conn, patient_id=patient_id, report_id=report_id, pipeline_run_id=None,
        risk_detection=risk_detection, report_type="lab", clinical_inconsistency=False,
    )
    alert = alert_repo.get_by_id(conn, alert_id)
    assert alert["alert_type"] == "critical_lab"
    assert "Troponin" in alert["message"]
    assert "peanut" not in alert["message"]


def test_critical_flag_with_cross_reactive_allergens_is_allergy_risk(conn):
    patient_id, report_id = _seed_patient(conn, email="allergy2@cis.com", mrn="ALERT-002")

    risk_detection = RiskDetectionOutput(
        risk_flags=[{
            "source_parameter": "peanut", "risk_level": "critical", "crosses_critical_threshold": True,
            "rationale": "Severe anaphylactic reaction risk from peanut exposure.",
            "cross_reactive_allergens": ["tree_nuts"],
        }],
        overall_risk_level="emergency", requires_immediate_escalation=True, risk_confidence=0.9,
    )
    alert_id = alert_service.create_alert_from_risk(
        conn, patient_id=patient_id, report_id=report_id, pipeline_run_id=None,
        risk_detection=risk_detection, report_type="lab", clinical_inconsistency=False,
    )
    assert alert_repo.get_by_id(conn, alert_id)["alert_type"] == "allergy_risk"


def test_radiology_report_type_classified_as_critical_radiology(conn):
    patient_id, report_id = _seed_patient(conn, email="rad@cis.com", mrn="ALERT-003")

    risk_detection = RiskDetectionOutput(
        risk_flags=[{
            "source_parameter": "Canal narrowing", "risk_level": "critical",
            "crosses_critical_threshold": True, "rationale": "Critical spinal canal narrowing.",
        }],
        overall_risk_level="emergency", requires_immediate_escalation=True, risk_confidence=0.9,
    )
    alert_id = alert_service.create_alert_from_risk(
        conn, patient_id=patient_id, report_id=report_id, pipeline_run_id=None,
        risk_detection=risk_detection, report_type="radiology", clinical_inconsistency=False,
    )
    assert alert_repo.get_by_id(conn, alert_id)["alert_type"] == "critical_radiology"


def test_escalation_with_no_critical_flags_but_inconsistency_is_clinical_inconsistency(conn):
    patient_id, report_id = _seed_patient(conn, email="inconsist@cis.com", mrn="ALERT-004")

    risk_detection = RiskDetectionOutput(
        risk_flags=[], overall_risk_level="urgent", requires_immediate_escalation=True,
        escalate_for_clinician_validation=True, risk_confidence=0.6,
    )
    alert_id = alert_service.create_alert_from_risk(
        conn, patient_id=patient_id, report_id=report_id, pipeline_run_id=None,
        risk_detection=risk_detection, report_type="lab", clinical_inconsistency=True,
    )
    assert alert_repo.get_by_id(conn, alert_id)["alert_type"] == "clinical_inconsistency"


def test_no_escalation_creates_no_alert(conn):
    patient_id, report_id = _seed_patient(conn, email="noescalation@cis.com", mrn="ALERT-005")
    risk_detection = RiskDetectionOutput(requires_immediate_escalation=False, risk_confidence=0.9)
    alert_id = alert_service.create_alert_from_risk(
        conn, patient_id=patient_id, report_id=report_id, pipeline_run_id=None,
        risk_detection=risk_detection, report_type="lab",
    )
    assert alert_id is None
