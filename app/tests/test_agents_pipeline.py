"""Mocked-LLM tests for each agent's negative-scenario/escalation branch, plus
one full-pipeline integration test proving the branches compose correctly:
an alert + appointment get created, and the patient-facing summary stays
un-approved regardless of what the agents themselves report.
"""
from backend.agents.clinical_analysis import ClinicalAnalysisAgent
from backend.agents.data_extraction import DataExtractionAgent
from backend.agents.insight_generation import InsightGenerationAgent
from backend.agents.patient_communication import PatientCommunicationAgent
from backend.agents.pipeline import ClinicalPipeline
from backend.agents.risk_detection import RiskDetectionAgent
from backend.agents.schemas import (
    ClinicalAnalysisFinding,
    ClinicalAnalysisOutput,
    DataExtractionOutput,
    InsightGenerationOutput,
    PatientCommunicationOutput,
    PatientContext,
    RiskDetectionOutput,
)
from backend.db.repositories import alert_repo, appointment_repo, patient_repo, pipeline_repo, report_repo, user_repo
from backend.knowledge_graph import MedicalKnowledgeGraph
from backend.llm.openai_client import OpenAIClient
from backend.observability.noop_observability import NoOpObservability

FAKE_LLM = OpenAIClient(api_key="sk-fake-for-tests", chat_model="gpt-4o-mini",
                         embedding_model="text-embedding-3-small")
OBS = NoOpObservability()


def _patient_context(**overrides) -> PatientContext:
    base = dict(age=40, sex="F", reported_symptoms=[], known_allergies=[], known_conditions=[])
    base.update(overrides)
    return PatientContext(**base)


# --- Agent 1: Data Extraction ---

def test_data_extraction_empty_text_short_circuits_without_llm_call():
    agent = DataExtractionAgent(llm_client=FAKE_LLM, observability=OBS)
    agent.invoke_llm = lambda **kwargs: (_ for _ in ()).throw(AssertionError("LLM should not be called"))

    output = agent.run(report_text="", table_text="", confidence_threshold=0.6, trace_parent=None)
    assert output.needs_review is True
    assert output.extraction_confidence == 0.0


def test_data_extraction_low_confidence_flags_needs_review():
    agent = DataExtractionAgent(llm_client=FAKE_LLM, observability=OBS)
    agent.invoke_llm = lambda **kwargs: DataExtractionOutput(
        parameters=[], narrative_observations=[], missing_or_ambiguous=[],
        extraction_confidence=0.3, needs_review=False, review_reason=None,
    )

    output = agent.run(report_text="Some garbled text", table_text="",
                        confidence_threshold=0.6, trace_parent=None)
    assert output.needs_review is True
    assert "0.30" in output.review_reason or "0.3" in output.review_reason


# --- Agent 2: Clinical Analysis ---

def test_clinical_analysis_conflicting_indicators_forces_inconsistency():
    agent = ClinicalAnalysisAgent(llm_client=FAKE_LLM, observability=OBS)
    canned = ClinicalAnalysisOutput(
        findings=[], overall_impression="Unclear", conflicting_indicators=["Hgb vs symptoms mismatch"],
        clinical_inconsistency=False, analysis_confidence=0.8,
    )
    agent._lab_agent.invoke_llm = lambda **kwargs: canned

    data_extraction = DataExtractionOutput(extraction_confidence=0.9)
    output = agent.run(report_type="lab", data_extraction=data_extraction,
                        patient=_patient_context(), trace_parent=None)
    assert output.clinical_inconsistency is True


def test_clinical_analysis_urgent_finding_misaligned_with_symptoms_forces_inconsistency():
    agent = ClinicalAnalysisAgent(llm_client=FAKE_LLM, observability=OBS)
    canned = ClinicalAnalysisOutput(
        findings=[ClinicalAnalysisFinding(
            parameter_name="hemoglobin", interpretation="Very low", status="CRITICAL_LOW",
            within_reference_range=False, aligns_with_symptoms=False,
            urgency="emergency", confidence=0.9,
        )],
        overall_impression="Severe anemia", clinical_inconsistency=False, analysis_confidence=0.9,
    )
    agent._lab_agent.invoke_llm = lambda **kwargs: canned

    output = agent.run(report_type="lab", data_extraction=DataExtractionOutput(extraction_confidence=0.9),
                        patient=_patient_context(), trace_parent=None)
    assert output.clinical_inconsistency is True


# --- Agent 3: Risk Detection ---

def test_risk_detection_critical_finding_forces_escalation():
    kg = MedicalKnowledgeGraph()
    agent = RiskDetectionAgent(llm_client=FAKE_LLM, observability=OBS, knowledge_graph=kg)
    agent.invoke_llm = lambda **kwargs: RiskDetectionOutput(
        risk_flags=[], overall_risk_level="routine", requires_immediate_escalation=False,
        risk_confidence=0.9,
    )

    clinical_analysis = ClinicalAnalysisOutput(
        findings=[ClinicalAnalysisFinding(
            parameter_name="hemoglobin", interpretation="Critically low", status="CRITICAL_LOW",
            within_reference_range=False, aligns_with_symptoms=True, urgency="emergency", confidence=0.9,
        )],
        overall_impression="Severe anemia", analysis_confidence=0.9,
    )
    output = agent.run(report_text="Hemoglobin 5.0 g/dL", clinical_analysis=clinical_analysis,
                        patient=_patient_context(), trace_parent=None)

    assert output.requires_immediate_escalation is True
    assert output.overall_risk_level == "emergency"
    assert output.escalate_for_clinician_validation is True


def test_risk_detection_allergy_cross_reactivity_attached_from_kg():
    kg = MedicalKnowledgeGraph()
    agent = RiskDetectionAgent(llm_client=FAKE_LLM, observability=OBS, knowledge_graph=kg)
    agent.invoke_llm = lambda **kwargs: RiskDetectionOutput(
        risk_flags=[{
            "source_parameter": "peanut", "risk_level": "high", "crosses_critical_threshold": False,
            "rationale": "Known peanut allergy", "kg_supporting_diagnoses": [], "cross_reactive_allergens": [],
        }],
        overall_risk_level="urgent", risk_confidence=0.8,
    )
    clinical_analysis = ClinicalAnalysisOutput(findings=[], overall_impression="N/A", analysis_confidence=0.8)
    output = agent.run(report_text="Patient reports peanut allergy",
                        clinical_analysis=clinical_analysis,
                        patient=_patient_context(known_allergies=["peanut"]), trace_parent=None)

    assert "tree_nuts" in output.risk_flags[0].cross_reactive_allergens


# --- Agent 4: Insight Generation ---

def test_insight_generation_review_required_on_low_confidence():
    agent = InsightGenerationAgent(llm_client=FAKE_LLM, observability=OBS)
    agent.invoke_llm = lambda **kwargs: InsightGenerationOutput(
        key_findings=["ok"], overall_confidence=0.3, status="ai_generated",
    )

    output = agent.run(
        data_extraction=DataExtractionOutput(extraction_confidence=0.9, needs_review=False),
        clinical_analysis=ClinicalAnalysisOutput(overall_impression="ok", analysis_confidence=0.9),
        risk_detection=RiskDetectionOutput(risk_confidence=0.9),
        history=[], confidence_threshold=0.65, trace_parent=None,
    )
    assert output.status == "review_required"


def test_insight_generation_review_required_when_upstream_escalated():
    agent = InsightGenerationAgent(llm_client=FAKE_LLM, observability=OBS)
    agent.invoke_llm = lambda **kwargs: InsightGenerationOutput(
        key_findings=["ok"], overall_confidence=0.95, status="ai_generated",
    )
    output = agent.run(
        data_extraction=DataExtractionOutput(extraction_confidence=0.9, needs_review=False),
        clinical_analysis=ClinicalAnalysisOutput(overall_impression="ok", analysis_confidence=0.9),
        risk_detection=RiskDetectionOutput(risk_confidence=0.9, escalate_for_clinician_validation=True),
        history=[], confidence_threshold=0.65, trace_parent=None,
    )
    assert output.status == "review_required"


# --- Agent 5: Patient Communication ---

def test_patient_communication_flags_diagnostic_language():
    agent = PatientCommunicationAgent(llm_client=FAKE_LLM, observability=OBS)
    agent.invoke_llm = lambda **kwargs: PatientCommunicationOutput(
        plain_language_summary="You have diabetes and need treatment.",
        diagnostic_language_flag=False,
    )
    output = agent.run(
        insight=InsightGenerationOutput(key_findings=["High glucose"], overall_confidence=0.9),
        patient=_patient_context(), trace_parent=None,
    )
    assert output.diagnostic_language_flag is True


def test_patient_communication_clean_language_not_flagged():
    agent = PatientCommunicationAgent(llm_client=FAKE_LLM, observability=OBS)
    agent.invoke_llm = lambda **kwargs: PatientCommunicationOutput(
        plain_language_summary="Your recent blood test showed a value outside the usual range.",
        what_this_means=["This can have several possible causes."],
        diagnostic_language_flag=False,
    )
    output = agent.run(
        insight=InsightGenerationOutput(key_findings=["High glucose"], overall_confidence=0.9),
        patient=_patient_context(), trace_parent=None,
    )
    assert output.diagnostic_language_flag is False


# --- Full pipeline integration (mocked LLM throughout) ---

def _build_pipeline() -> ClinicalPipeline:
    kg = MedicalKnowledgeGraph()
    data_extraction_agent = DataExtractionAgent(llm_client=FAKE_LLM, observability=OBS)
    clinical_analysis_agent = ClinicalAnalysisAgent(llm_client=FAKE_LLM, observability=OBS)
    risk_detection_agent = RiskDetectionAgent(llm_client=FAKE_LLM, observability=OBS, knowledge_graph=kg)
    insight_generation_agent = InsightGenerationAgent(llm_client=FAKE_LLM, observability=OBS)
    patient_communication_agent = PatientCommunicationAgent(llm_client=FAKE_LLM, observability=OBS)

    data_extraction_agent.invoke_llm = lambda **kwargs: DataExtractionOutput(
        parameters=[{"name": "hemoglobin", "value": "5.0", "unit": "g/dL", "status": "CRITICAL_LOW"}],
        extraction_confidence=0.9,
    )
    clinical_analysis_agent._lab_agent.invoke_llm = lambda **kwargs: ClinicalAnalysisOutput(
        findings=[ClinicalAnalysisFinding(
            parameter_name="hemoglobin", interpretation="Critically low", status="CRITICAL_LOW",
            within_reference_range=False, aligns_with_symptoms=True, urgency="emergency", confidence=0.9,
        )],
        overall_impression="Severe anemia requiring urgent attention", analysis_confidence=0.9,
    )
    risk_detection_agent.invoke_llm = lambda **kwargs: RiskDetectionOutput(
        risk_flags=[{
            "source_parameter": "hemoglobin", "risk_level": "critical", "crosses_critical_threshold": True,
            "rationale": "Hemoglobin critically low, risk of severe anemia",
        }],
        overall_risk_level="urgent", requires_immediate_escalation=False, risk_confidence=0.9,
    )
    insight_generation_agent.invoke_llm = lambda **kwargs: InsightGenerationOutput(
        key_findings=["Critically low hemoglobin"], risk_indicators=["Severe anemia risk"],
        recommendations=["Urgent clinician review"], overall_confidence=0.9, status="ai_generated",
    )
    patient_communication_agent.invoke_llm = lambda **kwargs: PatientCommunicationOutput(
        plain_language_summary="Your recent blood test showed a value that needs your doctor's attention.",
        what_this_means=["One of your blood values was outside the typical range."],
        what_you_should_do=["Contact your doctor promptly to discuss these results."],
    )

    return ClinicalPipeline(
        data_extraction_agent=data_extraction_agent, clinical_analysis_agent=clinical_analysis_agent,
        risk_detection_agent=risk_detection_agent, insight_generation_agent=insight_generation_agent,
        patient_communication_agent=patient_communication_agent, observability=OBS,
        extraction_confidence_threshold=0.6, insight_confidence_threshold=0.65,
    )


def test_full_pipeline_critical_finding_creates_alert_and_appointment_and_gates_patient_summary(conn):
    user_id = user_repo.create_user(conn, email="pt@cis.com", password_hash="h", password_salt="s",
                                     full_name="Test Patient", role="patient")
    patient_id = patient_repo.create_patient(conn, user_id=user_id, mrn="MRN-100", dob="1985-05-01",
                                              sex="F", blood_group="A+", known_conditions=None,
                                              primary_doctor_id=None)
    report_id = report_repo.create_report(
        conn, patient_id=patient_id, uploaded_by_user_id=user_id, report_type="lab", category="cbc",
        original_filename="cbc.pdf", file_path=None, file_format="pdf",
        raw_text="Hemoglobin: 5.0 g/dL (CRITICAL LOW)",
    )

    pipeline = _build_pipeline()
    result = pipeline.run(conn, report_id)

    assert result.status == "completed"
    assert report_repo.get_by_id(conn, report_id)["status"] == "processed"

    # Risk Detection's deterministic safety net must have forced escalation even though
    # the mocked LLM output said requires_immediate_escalation=False.
    assert result.risk_detection.requires_immediate_escalation is True
    assert len(alert_repo.list_by_patient(conn, patient_id)) == 1
    assert len(appointment_repo.list_by_patient(conn, patient_id)) == 1

    # Escalation must have propagated into Insight Generation's review-required gate.
    insight = pipeline_repo.get_insight(conn, result.insight_id)
    assert insight["status"] == "review_required"

    # And the patient-facing summary must stay locked regardless of the agents' own output.
    summary = pipeline_repo.get_patient_summary(conn, result.insight_id)
    assert summary["clinician_approved"] == 0

    agent_outputs = pipeline_repo.list_agent_outputs(conn, result.pipeline_run_id)
    assert {row["agent_name"] for row in agent_outputs} == {
        "data_extraction", "clinical_analysis", "risk_detection",
        "insight_generation", "patient_communication",
    }
