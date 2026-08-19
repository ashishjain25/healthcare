"""Creates SQLite alert records from Risk Detection agent output. No real
paging/notification system is contacted — this is the simulated-integration
boundary described in the project plan."""
import sqlite3

from backend.agents.schemas import RiskDetectionOutput
from backend.db.repositories import alert_repo


def create_alert_from_risk(conn: sqlite3.Connection, *, patient_id: int, report_id: int,
                            pipeline_run_id: int, risk_detection: RiskDetectionOutput,
                            report_type: str, clinical_inconsistency: bool = False) -> int | None:
    if not risk_detection.requires_immediate_escalation:
        return None

    severity = risk_detection.overall_risk_level if risk_detection.overall_risk_level in (
        "urgent", "stat", "emergency") else "urgent"

    # Only the flags that actually crossed a critical threshold should drive both the
    # message and the type classification below — a patient's on-file allergy showing up
    # as an unrelated, non-critical risk_flag elsewhere in the same list must not relabel
    # an otherwise purely cardiac/renal/etc. critical-lab alert as "allergy_risk" (a real
    # bug caught during manual verification: Aisha Khan's peanut allergy flag caused her
    # critical Troponin I alert to be mislabeled).
    critical_flags = [f for f in risk_detection.risk_flags if f.crosses_critical_threshold]
    message = "; ".join(f.rationale for f in critical_flags) or (
        risk_detection.escalation_reason or "Critical risk detected during automated review."
    )

    if any(f.cross_reactive_allergens for f in critical_flags):
        alert_type = "allergy_risk"
    elif not critical_flags and clinical_inconsistency:
        alert_type = "clinical_inconsistency"
    elif report_type == "radiology":
        alert_type = "critical_radiology"
    else:
        alert_type = "critical_lab"

    return alert_repo.create_alert(
        conn, patient_id=patient_id, report_id=report_id, pipeline_run_id=pipeline_run_id,
        alert_type=alert_type, severity=severity, message=message,
    )
