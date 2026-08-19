"""Agent 4: Insight Generation (net new — no notebook counterpart). Consolidates
outputs from Agents 1-3 plus historical report comparison into a structured,
clinician-facing insight with recommended next steps.
"""
from typing import Any

from backend.agents.base import TracedAgent
from backend.agents.schemas import (
    ClinicalAnalysisOutput,
    DataExtractionOutput,
    HistoricalReportSummary,
    InsightGenerationOutput,
    RiskDetectionOutput,
)
from backend.llm.openai_client import OpenAIClient
from backend.observability.port import ObservabilityPort

SYSTEM_PROMPT = """You are a clinical insight synthesis specialist. You are given the \
outputs of three upstream agents (data extraction, clinical analysis, risk detection) \
plus a summary of the patient's historical reports of the same category. Consolidate \
these into:
- key_findings: the most clinically important points, in plain clinical language
- risk_indicators: the risk signals a clinician should see first
- recommendations: concrete next-step recommendations
- historical_comparison_notes: how this report compares to the patient's prior reports \
  of the same type (trend improving/worsening/stable, notable deltas) — if no prior \
  reports are provided, say so explicitly rather than inventing a comparison
- overall_confidence (0-1): your confidence that this synthesis is complete and correct
- contradictory_outputs_detected: true if the upstream agents' outputs conflict with \
  each other in a way a clinician needs to resolve
Set status="review_required" whenever you are not confident, and explain why in \
review_required_reason."""


def _format_input(data_extraction: DataExtractionOutput, clinical_analysis: ClinicalAnalysisOutput,
                   risk_detection: RiskDetectionOutput, history: list[HistoricalReportSummary]) -> str:
    history_text = "\n".join(
        f"- {h.report_date} (report #{h.report_id}): {h.parameters}" for h in history
    ) or "(no prior reports of this category on file)"
    return (
        f"Data extraction: needs_review={data_extraction.needs_review}, "
        f"confidence={data_extraction.extraction_confidence}, "
        f"parameters={[p.model_dump() for p in data_extraction.parameters]}\n\n"
        f"Clinical analysis: clinical_inconsistency={clinical_analysis.clinical_inconsistency}, "
        f"overall_impression={clinical_analysis.overall_impression!r}, "
        f"confidence={clinical_analysis.analysis_confidence}\n\n"
        f"Risk detection: overall_risk_level={risk_detection.overall_risk_level}, "
        f"requires_immediate_escalation={risk_detection.requires_immediate_escalation}, "
        f"escalate_for_clinician_validation={risk_detection.escalate_for_clinician_validation}, "
        f"risk_flags={[f.model_dump() for f in risk_detection.risk_flags]}\n\n"
        f"Historical reports of this category:\n{history_text}"
    )


class InsightGenerationAgent(TracedAgent):
    agent_name = "insight_generation"

    def __init__(self, *, llm_client: OpenAIClient, observability: ObservabilityPort) -> None:
        super().__init__(
            llm_client=llm_client, observability=observability,
            system_prompt=SYSTEM_PROMPT, output_model=InsightGenerationOutput,
        )

    def run(self, *, data_extraction: DataExtractionOutput, clinical_analysis: ClinicalAnalysisOutput,
            risk_detection: RiskDetectionOutput, history: list[HistoricalReportSummary],
            confidence_threshold: float, trace_parent: Any) -> InsightGenerationOutput:
        input_text = _format_input(data_extraction, clinical_analysis, risk_detection, history)
        output = self.invoke_llm(input_text=input_text, trace_parent=trace_parent)

        # Negative Scenario 4 ("Review Required") — enforced deterministically, not just
        # trusted from the LLM's own status field.
        needs_review = (
            output.overall_confidence < confidence_threshold
            or data_extraction.needs_review
            or clinical_analysis.clinical_inconsistency
            or risk_detection.escalate_for_clinician_validation
            or output.contradictory_outputs_detected
        )
        if needs_review:
            output.status = "review_required"
            if not output.review_required_reason:
                output.review_required_reason = (
                    "Low confidence, upstream inconsistency/escalation, or contradictory "
                    "agent outputs require clinician review before this insight is finalized."
                )
        return output
