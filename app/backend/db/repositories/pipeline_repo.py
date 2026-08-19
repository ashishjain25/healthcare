"""Pipeline run / agent audit trail / insight / patient-summary / doctor-review CRUD.

This is the audit-trail backbone: every agent stage writes one agent_outputs row,
and the two Agent-5 gates (insights.status and patient_summaries.clinician_approved)
are enforced here, not just trusted from agent self-reports.
"""
import json
import sqlite3


def create_run(conn: sqlite3.Connection, *, report_id: int, patient_id: int) -> int:
    cur = conn.execute(
        "INSERT INTO pipeline_runs (report_id, patient_id, status) VALUES (?, ?, 'running')",
        (report_id, patient_id),
    )
    conn.commit()
    return cur.lastrowid


def save_agent_output(conn: sqlite3.Connection, *, pipeline_run_id: int, agent_name: str,
                       output_json: dict, confidence: float | None, flagged: bool,
                       flag_reason: str | None) -> int:
    cur = conn.execute(
        "INSERT INTO agent_outputs (pipeline_run_id, agent_name, output_json, confidence, flagged, flag_reason) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (pipeline_run_id, agent_name, json.dumps(output_json), confidence, int(flagged), flag_reason),
    )
    conn.commit()
    return cur.lastrowid


def list_agent_outputs(conn: sqlite3.Connection, pipeline_run_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM agent_outputs WHERE pipeline_run_id = ? ORDER BY id", (pipeline_run_id,)
    ).fetchall()


def mark_run_status(conn: sqlite3.Connection, pipeline_run_id: int, *, status: str,
                     overall_confidence: float | None = None, escalation_flag: bool = False,
                     escalation_reason: str | None = None) -> None:
    conn.execute(
        "UPDATE pipeline_runs SET status = ?, completed_at = datetime('now'), "
        "overall_confidence = ?, escalation_flag = ?, escalation_reason = ? WHERE id = ?",
        (status, overall_confidence, int(escalation_flag), escalation_reason, pipeline_run_id),
    )
    conn.commit()


def get_run(conn: sqlite3.Connection, pipeline_run_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM pipeline_runs WHERE id = ?", (pipeline_run_id,)).fetchone()


def get_run_by_report(conn: sqlite3.Connection, report_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM pipeline_runs WHERE report_id = ? ORDER BY id DESC LIMIT 1", (report_id,)
    ).fetchone()


def save_insight(conn: sqlite3.Connection, *, pipeline_run_id: int, report_id: int, patient_id: int,
                  summary: str, key_findings: list[str], risk_indicators: list[str],
                  recommendations: list[str], risk_level: str, requires_review: bool,
                  clinical_inconsistency: bool, status: str) -> int:
    cur = conn.execute(
        "INSERT INTO insights (pipeline_run_id, report_id, patient_id, summary, key_findings_json, "
        "risk_indicators_json, recommendations_json, risk_level, requires_review, clinical_inconsistency, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (pipeline_run_id, report_id, patient_id, summary, json.dumps(key_findings),
         json.dumps(risk_indicators), json.dumps(recommendations), risk_level,
         int(requires_review), int(clinical_inconsistency), status),
    )
    conn.commit()
    return cur.lastrowid


def get_insight(conn: sqlite3.Connection, insight_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM insights WHERE id = ?", (insight_id,)).fetchone()


def get_insight_by_report(conn: sqlite3.Connection, report_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM insights WHERE report_id = ? ORDER BY id DESC LIMIT 1", (report_id,)
    ).fetchone()


def list_insights_by_patient(conn: sqlite3.Connection, patient_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM insights WHERE patient_id = ? ORDER BY created_at DESC", (patient_id,)
    ).fetchall()


def update_insight_status(conn: sqlite3.Connection, insight_id: int, status: str,
                           requires_review: bool | None = None) -> None:
    if requires_review is None:
        conn.execute("UPDATE insights SET status = ? WHERE id = ?", (status, insight_id))
    else:
        conn.execute("UPDATE insights SET status = ?, requires_review = ? WHERE id = ?",
                      (status, int(requires_review), insight_id))
    conn.commit()


def save_patient_summary(conn: sqlite3.Connection, *, insight_id: int, pipeline_run_id: int,
                          plain_language_summary: str, what_this_means: list[str],
                          what_you_should_do: list[str], disclaimer: str,
                          diagnostic_language_flag: bool) -> int:
    cur = conn.execute(
        "INSERT INTO patient_summaries (insight_id, pipeline_run_id, plain_language_summary, "
        "what_this_means_json, what_you_should_do_json, disclaimer, diagnostic_language_flag, "
        "clinician_approved) VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
        (insight_id, pipeline_run_id, plain_language_summary, json.dumps(what_this_means),
         json.dumps(what_you_should_do), disclaimer, int(diagnostic_language_flag)),
    )
    conn.commit()
    return cur.lastrowid


def get_patient_summary(conn: sqlite3.Connection, insight_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM patient_summaries WHERE insight_id = ?", (insight_id,)
    ).fetchone()


def approve_patient_summary(conn: sqlite3.Connection, insight_id: int, approved_by_user_id: int) -> None:
    conn.execute(
        "UPDATE patient_summaries SET clinician_approved = 1, approved_by_user_id = ?, "
        "approved_at = datetime('now') WHERE insight_id = ?",
        (approved_by_user_id, insight_id),
    )
    conn.commit()


def add_doctor_review(conn: sqlite3.Connection, *, insight_id: int, doctor_user_id: int,
                       action: str, modified_findings: dict | None, comments: str | None) -> int:
    """Records a doctor's review action and enforces the clinician-oversight gate:
    only validated/modified/finalized reviews unlock the patient-facing summary."""
    cur = conn.execute(
        "INSERT INTO doctor_reviews (insight_id, doctor_user_id, action, modified_findings_json, comments) "
        "VALUES (?, ?, ?, ?, ?)",
        (insight_id, doctor_user_id, action,
         json.dumps(modified_findings) if modified_findings is not None else None, comments),
    )
    conn.commit()

    if action in ("validated", "modified", "finalized"):
        approve_patient_summary(conn, insight_id, doctor_user_id)
        update_insight_status(conn, insight_id, "finalized" if action == "finalized" else "doctor_reviewed",
                               requires_review=False)
    elif action == "rejected":
        update_insight_status(conn, insight_id, "review_required", requires_review=True)

    return cur.lastrowid


def list_doctor_reviews(conn: sqlite3.Connection, insight_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT doctor_reviews.*, users.full_name AS doctor_name "
        "FROM doctor_reviews JOIN users ON users.id = doctor_reviews.doctor_user_id "
        "WHERE doctor_reviews.insight_id = ? ORDER BY doctor_reviews.created_at DESC",
        (insight_id,),
    ).fetchall()
