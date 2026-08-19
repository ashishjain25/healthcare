"""Agent 3: Risk Detection — evaluates abnormal findings from the Clinical
Analysis agent and assigns a severity/risk classification. Adapts Week 4's
TracedAllergyAgent cross-reactivity knowledge plus Week 6's
MedicalKnowledgeGraph for deterministic corroboration of LLM risk judgments.
"""
from typing import Any

from backend.agents.base import TracedAgent
from backend.agents.schemas import ClinicalAnalysisOutput, PatientContext, RiskDetectionOutput
from backend.documents.entity_extractor import EntityExtractor
from backend.knowledge_graph import MedicalKnowledgeGraph
from backend.llm.openai_client import OpenAIClient
from backend.observability.port import ObservabilityPort

# Maps extracted parameter names (as produced by EntityExtractor/Agent 1) to the
# knowledge graph's broader lab-test category nodes (CBC/LFT/KFT/Thyroid_Panel).
PARAMETER_TO_TEST_CATEGORY: dict[str, str] = {
    "hemoglobin": "CBC", "wbc": "CBC", "rbc": "CBC", "platelet": "CBC",
    "ast": "LFT", "alt": "LFT", "bilirubin": "LFT",
    "creatinine": "KFT", "bun": "KFT",
    "tsh": "Thyroid_Panel", "t4": "Thyroid_Panel",
}

SYSTEM_PROMPT = """You are a clinical risk assessment specialist. Given the Clinical \
Analysis agent's findings, the patient's known/reported allergies, and knowledge-graph \
corroboration data, assign an overall risk classification.

Known allergen cross-reactivities to consider:
- Peanut: tree nuts, legumes, lupin
- Penicillin: amoxicillin, cephalosporins (~10% cross-react)
- Latex: banana, avocado, kiwi, chestnut
- Shellfish: shrimp, crab, lobster (crustaceans cross-react)
- Aspirin/NSAIDs: ibuprofen, naproxen

For each notable finding, produce a RiskFlag with a risk_level, whether it crosses a \
critical threshold, and your rationale. Set requires_immediate_escalation=true for any \
critical/emergency-level risk. Set ambiguous_multiple_conditions=true if the evidence \
plausibly supports two or more unrelated diagnoses. Set possible_false_positive=true if \
a flagged risk could plausibly be a data or measurement artifact rather than real risk."""


def _format_input(clinical_analysis: ClinicalAnalysisOutput, patient: PatientContext,
                   mentioned_allergens: list[str], kg_notes: list[str]) -> str:
    findings = "\n".join(
        f"- {f.parameter_name}: {f.status}, urgency={f.urgency}, within_range={f.within_reference_range}, "
        f"aligns_with_symptoms={f.aligns_with_symptoms}, causes={f.potential_causes}"
        for f in clinical_analysis.findings
    ) or "(no structured findings)"
    return (
        f"Clinical analysis findings:\n{findings}\n\n"
        f"Overall impression: {clinical_analysis.overall_impression}\n"
        f"Clinical inconsistency already flagged upstream: {clinical_analysis.clinical_inconsistency}\n\n"
        f"Patient known allergies: {patient.known_allergies}\n"
        f"Allergens mentioned in this report: {mentioned_allergens}\n\n"
        f"Knowledge graph corroboration:\n" + "\n".join(f"- {n}" for n in kg_notes)
    )


class RiskDetectionAgent(TracedAgent):
    agent_name = "risk_detection"

    def __init__(self, *, llm_client: OpenAIClient, observability: ObservabilityPort,
                 knowledge_graph: MedicalKnowledgeGraph) -> None:
        super().__init__(
            llm_client=llm_client, observability=observability,
            system_prompt=SYSTEM_PROMPT, output_model=RiskDetectionOutput,
        )
        self.knowledge_graph = knowledge_graph
        self.entity_extractor = EntityExtractor()

    def run(self, *, report_text: str, clinical_analysis: ClinicalAnalysisOutput,
            patient: PatientContext, trace_parent: Any) -> RiskDetectionOutput:
        mentioned_allergens = self.entity_extractor.extract_allergies(report_text)

        kg_notes: list[str] = []
        cross_reactive_map: dict[str, list[str]] = {}
        for allergen in set(mentioned_allergens) | set(a.lower() for a in patient.known_allergies):
            cross = self.knowledge_graph.get_cross_reactive_allergens(allergen)
            if cross:
                cross_reactive_map[allergen] = cross
                kg_notes.append(f"{allergen} is cross-reactive with: {cross}")

        symptom_result = self.knowledge_graph.find_diagnoses_for_symptoms(patient.reported_symptoms)
        if symptom_result["diagnoses"]:
            kg_notes.append(f"Symptom-based candidate diagnoses: {symptom_result['diagnoses']}")

        for f in clinical_analysis.findings:
            category = PARAMETER_TO_TEST_CATEGORY.get(f.parameter_name.lower())
            if category:
                supporting = self.knowledge_graph.find_diagnoses_for_test(category)
                if supporting:
                    kg_notes.append(f"{f.parameter_name} ({category}) may confirm: {supporting}")

        input_text = _format_input(clinical_analysis, patient, mentioned_allergens, kg_notes)
        output = self.invoke_llm(input_text=input_text, trace_parent=trace_parent)

        for flag in output.risk_flags:
            if flag.source_parameter.lower() in cross_reactive_map and not flag.cross_reactive_allergens:
                flag.cross_reactive_allergens = cross_reactive_map[flag.source_parameter.lower()]

        # Deterministic safety net for Negative Scenario 3: any CRITICAL_LOW/CRITICAL_HIGH
        # finding must always escalate, regardless of what the LLM concluded.
        has_critical_finding = any(
            f.status in ("CRITICAL_LOW", "CRITICAL_HIGH") for f in clinical_analysis.findings
        )
        if has_critical_finding:
            output.requires_immediate_escalation = True
            output.overall_risk_level = "emergency"

        # Ambiguous multiple diagnoses via KG symptom lookup (2+ candidate diagnoses with
        # no clearly dominant one) — surfaces as an escalation trigger, not silently resolved.
        diagnoses = symptom_result["diagnoses"]
        if len(diagnoses) >= 2 and diagnoses[0][1] == diagnoses[1][1]:
            output.ambiguous_multiple_conditions = True

        if (output.requires_immediate_escalation or output.ambiguous_multiple_conditions
                or output.possible_false_positive or clinical_analysis.clinical_inconsistency):
            output.escalate_for_clinician_validation = True
            if not output.escalation_reason:
                output.escalation_reason = (
                    "Critical finding, ambiguous diagnosis, possible false positive, or upstream "
                    "clinical inconsistency requires clinician validation before proceeding."
                )
        return output
