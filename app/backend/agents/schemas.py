"""Pydantic I/O schemas for the 5-agent clinical pipeline
(Data Extraction -> Clinical Analysis -> Risk Detection -> Insight Generation
-> Patient Communication), matching the PDF's agent/decision-point/negative-
scenario table. Field names here are what get persisted verbatim into
agent_outputs.output_json for the doctor-facing audit trail.
"""
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from backend.agents.normalize import normalize_lab_status, normalize_risk_level, normalize_urgency

LabStatus = Literal["NORMAL", "LOW", "HIGH", "CRITICAL_LOW", "CRITICAL_HIGH", "UNKNOWN"]
Urgency = Literal["routine", "urgent", "stat", "emergency"]


class PatientContext(BaseModel):
    """Snapshot of patient info fed into every agent — from patients/allergies/medical_history tables."""
    age: int | None = None
    sex: str | None = None
    reported_symptoms: list[str] = Field(default_factory=list)
    known_allergies: list[str] = Field(default_factory=list)
    known_conditions: list[str] = Field(default_factory=list)


class HistoricalReportSummary(BaseModel):
    """One prior report of the same category, used for the Insight Generation
    Agent's historical-comparison step (the PDF's 'Historical Data Comparison')."""
    report_id: int
    report_date: str
    parameters: dict[str, str]


# --- Agent 1: Data Extraction ---

class ExtractedParameter(BaseModel):
    name: str
    value: str
    unit: str | None = None
    reference_range: str | None = None
    status: LabStatus = "UNKNOWN"

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status(cls, value):
        return normalize_lab_status(value)


class DataExtractionOutput(BaseModel):
    parameters: list[ExtractedParameter] = Field(default_factory=list)
    narrative_observations: list[str] = Field(default_factory=list)
    missing_or_ambiguous: list[str] = Field(default_factory=list)
    extraction_confidence: float = Field(ge=0, le=1)
    needs_review: bool = False
    review_reason: str | None = None


# --- Agent 2: Clinical Analysis ---

class ClinicalAnalysisFinding(BaseModel):
    parameter_name: str
    interpretation: str
    status: LabStatus
    # LLMs legitimately can't always determine this (e.g. LVEF from a
    # narrative-only report has no simple numeric reference range) — None
    # means "undetermined", not "within range".
    within_reference_range: bool | None = None
    aligns_with_symptoms: bool
    potential_causes: list[str] = Field(default_factory=list)
    urgency: Urgency = "routine"
    confidence: float = Field(ge=0, le=1)

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status(cls, value):
        return normalize_lab_status(value)

    @field_validator("urgency", mode="before")
    @classmethod
    def _normalize_urgency(cls, value):
        return normalize_urgency(value)


class RadiologyDetail(BaseModel):
    study_type: str
    body_region: str
    findings: list[str] = Field(default_factory=list)
    impression: str
    differential_diagnoses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    urgency: Literal["routine", "urgent", "stat"] = "routine"
    confidence: float = Field(ge=0, le=1)

    @field_validator("urgency", mode="before")
    @classmethod
    def _normalize_urgency(cls, value):
        return normalize_urgency(value, allow_emergency=False)


class ClinicalAnalysisOutput(BaseModel):
    findings: list[ClinicalAnalysisFinding] = Field(default_factory=list)
    radiology_detail: RadiologyDetail | None = None
    overall_impression: str
    conflicting_indicators: list[str] = Field(default_factory=list)
    clinical_inconsistency: bool = False
    inconsistency_reason: str | None = None
    analysis_confidence: float = Field(ge=0, le=1)


# --- Agent 3: Risk Detection ---

class RiskFlag(BaseModel):
    source_parameter: str
    risk_level: Literal["low", "moderate", "high", "critical"]
    crosses_critical_threshold: bool
    rationale: str
    kg_supporting_diagnoses: list[str] = Field(default_factory=list)
    cross_reactive_allergens: list[str] = Field(default_factory=list)

    @field_validator("risk_level", mode="before")
    @classmethod
    def _normalize_risk_level(cls, value):
        return normalize_risk_level(value)


class RiskDetectionOutput(BaseModel):
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    overall_risk_level: Urgency = "routine"
    requires_immediate_escalation: bool = False
    ambiguous_multiple_conditions: bool = False
    possible_false_positive: bool = False
    escalate_for_clinician_validation: bool = False
    escalation_reason: str | None = None
    risk_confidence: float = Field(ge=0, le=1)

    @field_validator("overall_risk_level", mode="before")
    @classmethod
    def _normalize_overall_risk_level(cls, value):
        return normalize_urgency(value)


# --- Agent 4: Insight Generation (net new — no notebook counterpart) ---

class InsightGenerationOutput(BaseModel):
    key_findings: list[str] = Field(default_factory=list)
    risk_indicators: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    historical_comparison_notes: list[str] = Field(default_factory=list)
    overall_confidence: float = Field(ge=0, le=1)
    contradictory_outputs_detected: bool = False
    status: Literal["ai_generated", "review_required"] = "ai_generated"
    review_required_reason: str | None = None

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status(cls, value):
        text = str(value).strip().lower().replace(" ", "_")
        return "review_required" if "review" in text else "ai_generated"


# --- Agent 5: Patient Communication (net new — no notebook counterpart) ---

class PatientCommunicationOutput(BaseModel):
    plain_language_summary: str
    what_this_means: list[str] = Field(default_factory=list)
    what_you_should_do: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "This explanation is for informational purposes only and is not a diagnosis. "
        "Please discuss your results with your doctor."
    )
    diagnostic_language_flag: bool = False


class PipelineResult(BaseModel):
    """Everything a caller (report_service) needs after ClinicalPipeline.run()."""
    pipeline_run_id: int
    report_id: int
    patient_id: int
    status: Literal["completed", "failed"]
    data_extraction: DataExtractionOutput | None = None
    clinical_analysis: ClinicalAnalysisOutput | None = None
    risk_detection: RiskDetectionOutput | None = None
    insight_generation: InsightGenerationOutput | None = None
    patient_communication: PatientCommunicationOutput | None = None
    insight_id: int | None = None
    alert_id: int | None = None
    error: str | None = None
