"""Agent 1: Data Extraction — parses diagnostic reports, extracts key clinical
entities, and flags insufficient/ambiguous data for review. Wraps Week 2's
regex EntityExtractor as a deterministic first pass, then one LLM call fills
in narrative observations (needed for radiology text regex can't parse) and
judges extraction confidence.
"""
from typing import Any

from backend.agents.base import TracedAgent
from backend.agents.schemas import DataExtractionOutput, ExtractedParameter
from backend.documents.entity_extractor import EntityExtractor
from backend.llm.openai_client import OpenAIClient
from backend.observability.port import ObservabilityPort

SYSTEM_PROMPT = """You are a clinical data extraction specialist. You are given the raw \
text of a diagnostic report (lab, radiology, or physician note) plus a preliminary \
regex-based extraction pass of any lab values it found.

Your job:
1. List every clinically relevant parameter you can find (name, value, unit, reference \
   range if stated, and status if determinable: NORMAL/LOW/HIGH/CRITICAL_LOW/CRITICAL_HIGH/UNKNOWN).
   Include parameters the regex pass may have missed, and narrative findings for reports \
   that are not lab-value based (e.g. radiology impressions).
2. List narrative_observations: any non-tabular clinical observations worth carrying forward.
3. List missing_or_ambiguous: any parameter or observation you cannot confidently determine \
   from the text (e.g. a value with no units, an illegible fragment, a truncated sentence).
4. Set extraction_confidence (0-1): use a LOW score (below 0.5) if the report is short, \
   garbled, mostly empty, or otherwise insufficient for reliable clinical extraction.
Do not invent values that are not present in the text."""


class DataExtractionAgent(TracedAgent):
    agent_name = "data_extraction"

    def __init__(self, *, llm_client: OpenAIClient, observability: ObservabilityPort) -> None:
        super().__init__(
            llm_client=llm_client, observability=observability,
            system_prompt=SYSTEM_PROMPT, output_model=DataExtractionOutput,
        )
        self.entity_extractor = EntityExtractor()

    def run(self, *, report_text: str, table_text: str, confidence_threshold: float,
            trace_parent: Any) -> DataExtractionOutput:
        full_text = f"{report_text}\n{table_text}".strip()

        # Negative scenario: no extractable text at all (e.g. a scanned-image PDF with
        # no OCR text layer — a real case in this project's own sample data). Short-circuit
        # without an LLM call: there is nothing for the model to reason about.
        if not full_text:
            return DataExtractionOutput(
                parameters=[],
                narrative_observations=[],
                missing_or_ambiguous=[
                    "Report contains no extractable text (e.g. a scanned image with no OCR text layer)."
                ],
                extraction_confidence=0.0,
                needs_review=True,
                review_reason="No extractable text found in the uploaded document.",
            )

        regex_labs = self.entity_extractor.extract_lab_values(full_text)
        regex_statuses = self.entity_extractor.extract_status(full_text)

        input_text = (
            f"Report text:\n{full_text}\n\n"
            f"Regex pre-extraction found these lab values: {regex_labs}\n"
            f"Detected status keywords in the text: {regex_statuses}\n"
        )
        output = self.invoke_llm(input_text=input_text, trace_parent=trace_parent)

        # Keep any regex-detected parameter the LLM didn't surface, rather than silently
        # dropping a deterministically-found value.
        llm_param_names = {p.name.lower() for p in output.parameters}
        for lab in regex_labs:
            if lab["test"] not in llm_param_names:
                output.parameters.append(ExtractedParameter(
                    name=lab["test"], value=lab["value"], unit=lab["unit"] or None,
                    reference_range=None, status="UNKNOWN",
                ))

        if output.extraction_confidence < confidence_threshold or output.missing_or_ambiguous:
            output.needs_review = True
            if not output.review_reason:
                output.review_reason = (
                    f"Extraction confidence {output.extraction_confidence:.2f} is below the "
                    f"{confidence_threshold} threshold, or ambiguous/missing fields were detected."
                )
        return output
