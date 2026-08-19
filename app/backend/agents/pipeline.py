"""ClinicalPipeline — plain Python orchestrator chaining the 5 agents
(Data Extraction -> Clinical Analysis -> Risk Detection -> Insight Generation
-> Patient Communication). Plain Python (not one big LCEL RunnableSequence)
because: report-type branching is clearer as an if; every stage's output must
persist to agent_outputs immediately even if a later stage throws; and the
negative-scenario/escalation logic is business logic, not an LCEL fit.
"""
import sqlite3
from datetime import date, datetime

from backend.agents.clinical_analysis import ClinicalAnalysisAgent
from backend.agents.data_extraction import DataExtractionAgent
from backend.agents.insight_generation import InsightGenerationAgent
from backend.agents.patient_communication import PatientCommunicationAgent
from backend.agents.risk_detection import RiskDetectionAgent
from backend.agents.schemas import HistoricalReportSummary, PatientContext, PipelineResult
from backend.db.repositories import patient_repo, pipeline_repo, report_repo
from backend.observability.port import ObservabilityPort
from backend.services import alert_service, appointment_service


def _calculate_age(dob: str | None) -> int | None:
    if not dob:
        return None
    try:
        birth = date.fromisoformat(dob)
    except ValueError:
        return None
    today = date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def _build_patient_context(conn: sqlite3.Connection, patient_id: int) -> PatientContext:
    patient_row = patient_repo.get_by_id(conn, patient_id)
    allergies = patient_repo.list_allergies(conn, patient_id)
    history = patient_repo.list_medical_history(conn, patient_id)
    return PatientContext(
        age=_calculate_age(patient_row["dob"]) if patient_row else None,
        sex=patient_row["sex"] if patient_row else None,
        reported_symptoms=[h["description"] for h in history if h["entry_type"] == "symptom"],
        known_allergies=[a["allergen"] for a in allergies],
        known_conditions=[h["description"] for h in history if h["entry_type"] == "condition"],
    )


def _build_history(conn: sqlite3.Connection, patient_id: int, category: str,
                    current_report_id: int, limit: int = 3) -> list[HistoricalReportSummary]:
    prior_reports = report_repo.list_previous_reports(conn, patient_id, category, current_report_id, limit)
    summaries = []
    for report in prior_reports:
        extractions = report_repo.list_extractions(conn, report["id"])
        parameters = {e["parameter_name"]: f"{e['value']} {e['unit'] or ''}".strip() for e in extractions}
        summaries.append(HistoricalReportSummary(
            report_id=report["id"], report_date=report["uploaded_at"], parameters=parameters,
        ))
    return summaries


class ClinicalPipeline:
    def __init__(self, *, data_extraction_agent: DataExtractionAgent,
                 clinical_analysis_agent: ClinicalAnalysisAgent,
                 risk_detection_agent: RiskDetectionAgent,
                 insight_generation_agent: InsightGenerationAgent,
                 patient_communication_agent: PatientCommunicationAgent,
                 observability: ObservabilityPort,
                 extraction_confidence_threshold: float,
                 insight_confidence_threshold: float) -> None:
        self.data_extraction_agent = data_extraction_agent
        self.clinical_analysis_agent = clinical_analysis_agent
        self.risk_detection_agent = risk_detection_agent
        self.insight_generation_agent = insight_generation_agent
        self.patient_communication_agent = patient_communication_agent
        self.observability = observability
        self.extraction_confidence_threshold = extraction_confidence_threshold
        self.insight_confidence_threshold = insight_confidence_threshold

    def run(self, conn: sqlite3.Connection, report_id: int) -> PipelineResult:
        report = report_repo.get_by_id(conn, report_id)
        if report is None:
            raise ValueError(f"Report {report_id} not found")

        patient_id = report["patient_id"]
        report_repo.update_status(conn, report_id, "processing")
        run_id = pipeline_repo.create_run(conn, report_id=report_id, patient_id=patient_id)
        trace = self.observability.start_trace(
            "clinical-pipeline-run", session_id=f"report-{report_id}",
            metadata={"report_id": report_id, "patient_id": patient_id, "run_id": run_id},
        )

        try:
            patient_context = _build_patient_context(conn, patient_id)

            # --- Agent 1: Data Extraction ---
            span1 = self.observability.start_span(trace, "stage-data-extraction")
            data_extraction = self.data_extraction_agent.run(
                report_text=report["raw_text"], table_text=report["table_text"] or "",
                confidence_threshold=self.extraction_confidence_threshold, trace_parent=span1,
            )
            pipeline_repo.save_agent_output(
                conn, pipeline_run_id=run_id, agent_name="data_extraction",
                output_json=data_extraction.model_dump(), confidence=data_extraction.extraction_confidence,
                flagged=data_extraction.needs_review, flag_reason=data_extraction.review_reason,
            )
            self.observability.end_span(span1, output=data_extraction.model_dump())

            for param in data_extraction.parameters:
                if param.value:
                    report_repo.add_extraction(
                        conn, report_id=report_id, parameter_name=param.name, value=param.value,
                        unit=param.unit, reference_range=param.reference_range,
                        status=param.status, confidence=data_extraction.extraction_confidence,
                    )

            # --- Agent 2: Clinical Analysis ---
            span2 = self.observability.start_span(trace, "stage-clinical-analysis")
            clinical_analysis = self.clinical_analysis_agent.run(
                report_type=report["report_type"], data_extraction=data_extraction,
                patient=patient_context, trace_parent=span2,
            )
            pipeline_repo.save_agent_output(
                conn, pipeline_run_id=run_id, agent_name="clinical_analysis",
                output_json=clinical_analysis.model_dump(), confidence=clinical_analysis.analysis_confidence,
                flagged=clinical_analysis.clinical_inconsistency, flag_reason=clinical_analysis.inconsistency_reason,
            )
            self.observability.end_span(span2, output=clinical_analysis.model_dump())

            # --- Agent 3: Risk Detection ---
            span3 = self.observability.start_span(trace, "stage-risk-detection")
            risk_detection = self.risk_detection_agent.run(
                report_text=report["raw_text"], clinical_analysis=clinical_analysis,
                patient=patient_context, trace_parent=span3,
            )
            pipeline_repo.save_agent_output(
                conn, pipeline_run_id=run_id, agent_name="risk_detection",
                output_json=risk_detection.model_dump(), confidence=risk_detection.risk_confidence,
                flagged=risk_detection.escalate_for_clinician_validation, flag_reason=risk_detection.escalation_reason,
            )
            self.observability.end_span(span3, output=risk_detection.model_dump())

            alert_id = alert_service.create_alert_from_risk(
                conn, patient_id=patient_id, report_id=report_id, pipeline_run_id=run_id,
                risk_detection=risk_detection, report_type=report["report_type"],
                clinical_inconsistency=clinical_analysis.clinical_inconsistency,
            )
            if alert_id is not None:
                appointment_service.suggest_appointment(
                    conn, patient_id=patient_id, alert_id=alert_id,
                    reason=risk_detection.escalation_reason or "Critical finding follow-up",
                )

            # --- Agent 4: Insight Generation ---
            history = _build_history(conn, patient_id, report["category"], report_id)
            span4 = self.observability.start_span(trace, "stage-insight-generation")
            insight = self.insight_generation_agent.run(
                data_extraction=data_extraction, clinical_analysis=clinical_analysis,
                risk_detection=risk_detection, history=history,
                confidence_threshold=self.insight_confidence_threshold, trace_parent=span4,
            )
            pipeline_repo.save_agent_output(
                conn, pipeline_run_id=run_id, agent_name="insight_generation",
                output_json=insight.model_dump(), confidence=insight.overall_confidence,
                flagged=(insight.status == "review_required"), flag_reason=insight.review_required_reason,
            )
            self.observability.end_span(span4, output=insight.model_dump())

            insight_id = pipeline_repo.save_insight(
                conn, pipeline_run_id=run_id, report_id=report_id, patient_id=patient_id,
                summary=insight.key_findings[0] if insight.key_findings else "See detailed findings.",
                key_findings=insight.key_findings, risk_indicators=insight.risk_indicators,
                recommendations=insight.recommendations, risk_level=risk_detection.overall_risk_level,
                requires_review=(insight.status == "review_required"),
                clinical_inconsistency=clinical_analysis.clinical_inconsistency,
                status=insight.status,
            )

            # --- Agent 5: Patient Communication ---
            span5 = self.observability.start_span(trace, "stage-patient-communication")
            patient_comm = self.patient_communication_agent.run(
                insight=insight, patient=patient_context, trace_parent=span5,
            )
            pipeline_repo.save_agent_output(
                conn, pipeline_run_id=run_id, agent_name="patient_communication",
                output_json=patient_comm.model_dump(), confidence=None,
                flagged=patient_comm.diagnostic_language_flag,
                flag_reason="Diagnostic-sounding language detected" if patient_comm.diagnostic_language_flag else None,
            )
            self.observability.end_span(span5, output=patient_comm.model_dump())

            # Negative Scenario 5's real enforcement: clinician_approved always starts
            # false, regardless of what the agent claims about itself.
            pipeline_repo.save_patient_summary(
                conn, insight_id=insight_id, pipeline_run_id=run_id,
                plain_language_summary=patient_comm.plain_language_summary,
                what_this_means=patient_comm.what_this_means,
                what_you_should_do=patient_comm.what_you_should_do,
                disclaimer=patient_comm.disclaimer,
                diagnostic_language_flag=patient_comm.diagnostic_language_flag,
            )

            overall_confidence = min(
                data_extraction.extraction_confidence, clinical_analysis.analysis_confidence,
                risk_detection.risk_confidence, insight.overall_confidence,
            )
            escalation_flag = risk_detection.requires_immediate_escalation
            pipeline_repo.mark_run_status(
                conn, run_id, status="completed", overall_confidence=overall_confidence,
                escalation_flag=escalation_flag, escalation_reason=risk_detection.escalation_reason,
            )
            report_repo.update_status(conn, report_id, "processed")
            self.observability.end_span(trace, output={"status": "completed"})

            return PipelineResult(
                pipeline_run_id=run_id, report_id=report_id, patient_id=patient_id, status="completed",
                data_extraction=data_extraction, clinical_analysis=clinical_analysis,
                risk_detection=risk_detection, insight_generation=insight,
                patient_communication=patient_comm, insight_id=insight_id, alert_id=alert_id,
            )
        except Exception as exc:
            pipeline_repo.mark_run_status(conn, run_id, status="failed")
            report_repo.update_status(conn, report_id, "error")
            self.observability.end_span(trace, output={"status": "failed", "error": str(exc)})
            return PipelineResult(
                pipeline_run_id=run_id, report_id=report_id, patient_id=patient_id,
                status="failed", error=str(exc),
            )
