"""Covers the exact free-text status/urgency values gpt-4o-mini emitted on
real report data during manual seeding (see the traceback that motivated
this module) plus a few synthetic edge cases."""
import pytest

from backend.agents.normalize import normalize_lab_status, normalize_risk_level, normalize_urgency
from backend.agents.schemas import ClinicalAnalysisFinding, ExtractedParameter, InsightGenerationOutput


@pytest.mark.parametrize("raw,expected", [
    ("NORMAL", "NORMAL"),
    ("normal", "NORMAL"),
    ("LOW", "LOW"),
    ("HIGH", "HIGH"),
    ("CRITICAL_LOW", "CRITICAL_LOW"),
    ("CRITICAL_HIGH", "CRITICAL_HIGH"),
    ("Slightly High", "HIGH"),
    ("ABNORMAL", "UNKNOWN"),
    ("Abnormal", "UNKNOWN"),
    ("Low-normal", "LOW"),
    ("LOW (Stage 3 CKD)", "LOW"),
    ("Prolonged", "HIGH"),
    ("Positive", "HIGH"),
    ("Elevated", "HIGH"),
    ("Decreased", "LOW"),
    ("something totally unrecognized", "UNKNOWN"),
])
def test_normalize_lab_status(raw, expected):
    assert normalize_lab_status(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("routine", "routine"),
    ("URGENT", "urgent"),
    ("Stat", "stat"),
    ("emergency", "emergency"),
    ("Immediate", "emergency"),
    ("Critical", "emergency"),
    ("unclear", "routine"),
])
def test_normalize_urgency(raw, expected):
    assert normalize_urgency(raw) == expected


def test_normalize_urgency_without_emergency_clamps_to_stat():
    assert normalize_urgency("Critical", allow_emergency=False) == "stat"
    assert normalize_urgency("Emergency", allow_emergency=False) == "stat"


@pytest.mark.parametrize("raw,expected", [
    ("low", "low"), ("Medium", "moderate"), ("HIGH", "high"), ("critical", "critical"),
    ("severe", "critical"), ("???", "moderate"),
])
def test_normalize_risk_level(raw, expected):
    assert normalize_risk_level(raw) == expected


def test_extracted_parameter_coerces_out_of_vocabulary_status():
    param = ExtractedParameter(name="ALP", value="158", unit="U/L", status="Slightly High")
    assert param.status == "HIGH"


def test_clinical_analysis_finding_accepts_null_within_reference_range():
    finding = ClinicalAnalysisFinding(
        parameter_name="LVEF", interpretation="Reduced", status="UNKNOWN",
        within_reference_range=None, aligns_with_symptoms=True, confidence=0.7,
    )
    assert finding.within_reference_range is None


def test_insight_generation_status_coerces_free_text():
    output = InsightGenerationOutput(overall_confidence=0.9, status="Needs Review")
    assert output.status == "review_required"
