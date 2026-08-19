"""Agent 2: Clinical Analysis — evaluates relationships between diagnostic
values, compares against clinical reference ranges, and checks alignment with
patient-reported symptoms. Adapts Week 4's TracedLabInterpreterAgent /
TracedRadiologyAgent reference-range prompts, but is fed Agent 1's structured
output + patient symptoms instead of raw text.
"""
from typing import Any

from backend.agents.base import TracedAgent
from backend.agents.schemas import (
    ClinicalAnalysisOutput,
    DataExtractionOutput,
    PatientContext,
)
from backend.llm.openai_client import OpenAIClient
from backend.observability.port import ObservabilityPort

REFERENCE_RANGES = """Reference ranges (use these for interpretation):
- Hemoglobin: Male 13.5-17.5 g/dL, Female 12.0-16.0 g/dL
- WBC: 4,500-11,000 /uL
- Platelet: 150,000-400,000 /uL
- Glucose (fasting): 70-100 mg/dL
- Creatinine: 0.7-1.3 mg/dL
- BUN: 7-20 mg/dL
- AST: 10-40 U/L, ALT: 7-56 U/L
- TSH: 0.4-4.0 mIU/L
- Free T4: 0.8-1.8 ng/dL

Critical (panic) values: Hemoglobin <7 or >20 g/dL, Glucose <40 or >500 mg/dL,
WBC <2,000 or >30,000 /uL, Platelets <50,000 or >1,000,000 /uL."""

LAB_SYSTEM_PROMPT = f"""You are an expert clinical laboratory medicine specialist. Given \
extracted lab parameters and the patient's reported symptoms, evaluate each parameter \
against reference ranges, determine whether findings align with the reported symptoms, \
and flag any conflicting indicators (e.g. a critical value with no corroborating symptom, \
or symptoms that don't match any abnormal parameter).

{REFERENCE_RANGES}

Set clinical_inconsistency=true if findings conflict with each other or with the reported \
symptoms in a way that needs a clinician's judgment before proceeding. Leave radiology_detail null."""

RADIOLOGY_SYSTEM_PROMPT = """You are an expert radiologist specializing in diagnostic \
imaging. Given extracted radiology observations and the patient's reported symptoms, \
produce a radiology_detail assessment (study_type, body_region, findings, impression, \
differential_diagnoses, recommendations, urgency, confidence) and also summarize your \
overall_impression at the top level.

For each study type, consider: X-ray (lung fields, heart size, bones, soft tissues), \
CT (detailed anatomy, contrast patterns, masses), MRI (soft tissue detail, brain/spine), \
Ultrasound (real-time imaging, Doppler flow).

Set clinical_inconsistency=true if the findings don't align with the reported symptoms in \
a way that needs a clinician's judgment. The top-level `findings` list may be left empty; \
put structured findings inside radiology_detail instead."""


def _format_input(data_extraction: DataExtractionOutput, patient: PatientContext) -> str:
    params = "\n".join(
        f"- {p.name}: {p.value} {p.unit or ''} (status: {p.status})".strip()
        for p in data_extraction.parameters
    ) or "(no structured parameters extracted)"
    narrative = "\n".join(f"- {o}" for o in data_extraction.narrative_observations) or "(none)"
    return (
        f"Extracted parameters:\n{params}\n\n"
        f"Narrative observations:\n{narrative}\n\n"
        f"Patient age: {patient.age}, sex: {patient.sex}\n"
        f"Patient-reported symptoms: {patient.reported_symptoms}\n"
        f"Patient known conditions: {patient.known_conditions}"
    )


class ClinicalAnalysisAgent:
    """Dispatches to a lab-focused or radiology-focused LCEL sub-agent based on
    report_type, both sharing the ClinicalAnalysisOutput schema."""

    agent_name = "clinical_analysis"

    def __init__(self, *, llm_client: OpenAIClient, observability: ObservabilityPort) -> None:
        self._lab_agent = TracedAgent(
            llm_client=llm_client, observability=observability,
            system_prompt=LAB_SYSTEM_PROMPT, output_model=ClinicalAnalysisOutput,
        )
        self._lab_agent.agent_name = self.agent_name
        self._radiology_agent = TracedAgent(
            llm_client=llm_client, observability=observability,
            system_prompt=RADIOLOGY_SYSTEM_PROMPT, output_model=ClinicalAnalysisOutput,
        )
        self._radiology_agent.agent_name = self.agent_name

    def run(self, *, report_type: str, data_extraction: DataExtractionOutput,
            patient: PatientContext, trace_parent: Any) -> ClinicalAnalysisOutput:
        input_text = _format_input(data_extraction, patient)
        sub_agent = self._radiology_agent if report_type == "radiology" else self._lab_agent
        output = sub_agent.invoke_llm(input_text=input_text, trace_parent=trace_parent)

        # Deterministic backstop for Negative Scenario 2 ("Clinical Inconsistency"):
        # force the flag even if the LLM under-calls it, whenever there are explicit
        # conflicting indicators or an urgent/emergency finding that doesn't align with
        # the patient's reported symptoms.
        urgent_misaligned = any(
            f.urgency in ("urgent", "stat", "emergency") and not f.aligns_with_symptoms
            for f in output.findings
        )
        if output.conflicting_indicators or urgent_misaligned:
            output.clinical_inconsistency = True
            if not output.inconsistency_reason:
                output.inconsistency_reason = (
                    "Conflicting indicators or an urgent finding not aligned with reported symptoms."
                )
        return output
