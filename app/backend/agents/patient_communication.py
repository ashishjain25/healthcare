"""Agent 5: Patient Communication (net new — no notebook counterpart). Converts
clinical insights into plain-language patient explanations. The real
enforcement of "must not read as a diagnosis" is a DB-level gate applied by
report_service (patient_summaries.clinician_approved), not this agent's
self-report — but this agent still runs a guard as a first line of defense.
"""
import re
from typing import Any

from backend.agents.base import TracedAgent
from backend.agents.schemas import InsightGenerationOutput, PatientCommunicationOutput, PatientContext
from backend.llm.openai_client import OpenAIClient
from backend.observability.port import ObservabilityPort

SYSTEM_PROMPT = """You are a patient communication specialist. Translate the clinical \
insight below into a plain-language explanation for the patient.

Rules (safety-critical):
- Never state or imply a new diagnosis (e.g. do not say "you have diabetes" or "you are \
  diagnosed with X"). Describe findings and their general meaning, then recommend the \
  patient discuss the results with their doctor.
- Use plain, non-technical language a layperson can understand.
- what_this_means: 2-5 short bullet points explaining the findings in plain language.
- what_you_should_do: 2-5 short, actionable next steps (e.g. "Schedule a follow-up with \
  your doctor", "Continue your current medication as prescribed").
- Set diagnostic_language_flag=true yourself if you were unable to avoid diagnostic-sounding \
  language, so a human reviewer can catch it."""

_DIAGNOSTIC_PHRASE_PATTERN = re.compile(
    r"\byou (have|are suffering from|are diagnosed with)\b|"
    r"\byour diagnosis is\b|\bdiagnosed with\b|\byou'?ve been diagnosed\b",
    re.IGNORECASE,
)


def _format_input(insight: InsightGenerationOutput, patient: PatientContext) -> str:
    return (
        f"Key findings: {insight.key_findings}\n"
        f"Risk indicators: {insight.risk_indicators}\n"
        f"Recommendations: {insight.recommendations}\n"
        f"Historical comparison notes: {insight.historical_comparison_notes}\n"
        f"Patient age: {patient.age}, known conditions: {patient.known_conditions}"
    )


class PatientCommunicationAgent(TracedAgent):
    agent_name = "patient_communication"

    def __init__(self, *, llm_client: OpenAIClient, observability: ObservabilityPort) -> None:
        super().__init__(
            llm_client=llm_client, observability=observability,
            system_prompt=SYSTEM_PROMPT, output_model=PatientCommunicationOutput,
        )

    def run(self, *, insight: InsightGenerationOutput, patient: PatientContext,
            trace_parent: Any) -> PatientCommunicationOutput:
        input_text = _format_input(insight, patient)
        output = self.invoke_llm(input_text=input_text, trace_parent=trace_parent)

        combined_text = output.plain_language_summary + " " + " ".join(output.what_this_means)
        if _DIAGNOSTIC_PHRASE_PATTERN.search(combined_text):
            output.diagnostic_language_flag = True

        return output
