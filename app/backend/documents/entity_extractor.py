"""Deterministic regex-based clinical entity extraction — adapted from
Healthcare.ipynb Week 2 (ClinicalEntityExtractor, cell 37). Used as the
first, cheap pass inside Agent 1 (Data Extraction) before any LLM call.
"""
import re

LAB_PATTERNS: dict[str, str] = {
    "hemoglobin": r"(?:Hemoglobin|Hgb|HGB)[:\s]+(\d+\.?\d*)\s*(g/dL|g/dl)?",
    "wbc": r"(?:WBC|White Blood Cell)[:\s]+(\d+[,\d]*)\s*(/uL|/μL)?",
    "rbc": r"(?:RBC|Red Blood Cell)[:\s]+(\d+\.?\d*)\s*(M/uL)?",
    "platelet": r"(?:Platelet|PLT)[:\s]+(\d+[,\d]*)",
    "glucose": r"(?:Glucose|Blood Sugar)[:\s]+(\d+\.?\d*)\s*(mg/dL)?",
    "creatinine": r"(?:Creatinine)[:\s]+(\d+\.?\d*)\s*(mg/dL)?",
    "bun": r"(?:BUN|Blood Urea Nitrogen)[:\s]+(\d+\.?\d*)\s*(mg/dL)?",
    "bilirubin": r"(?:Bilirubin)[:\s]+(\d+\.?\d*)\s*(mg/dL)?",
    "ast": r"(?:AST|SGOT)[:\s]+(\d+\.?\d*)\s*(U/L)?",
    "alt": r"(?:ALT|SGPT)[:\s]+(\d+\.?\d*)\s*(U/L)?",
    "tsh": r"(?:TSH)[:\s]+(\d+\.?\d*)\s*(mIU/L)?",
    "t4": r"(?:Free T4|T4)[:\s]+(\d+\.?\d*)\s*(ng/dL)?",
}

STATUS_PATTERNS: dict[str, str] = {
    "normal": r"\b(NORMAL|Normal|WNL|Within Normal Limits)\b",
    "high": r"\b(HIGH|High|Elevated|Increased|Above|H)\b",
    "low": r"\b(LOW|Low|Decreased|Below|L)\b",
    "critical": r"\b(CRITICAL|Critical|STAT|Urgent|PANIC)\b",
}

ALLERGEN_LIST: list[str] = [
    # Food
    "peanut", "wheat", "milk", "egg", "soy", "fish", "shellfish",
    "gluten", "tree nut", "sesame",
    # Medication
    "penicillin", "sulfa", "aspirin", "ibuprofen", "nsaid",
    "codeine", "morphine", "latex",
    # Environmental
    "dust", "pollen", "mold", "pet dander", "bee", "wasp",
]


class EntityExtractor:
    """Regex-based extraction of lab values, status keywords, and allergens."""

    def __init__(self) -> None:
        self.lab_patterns = LAB_PATTERNS
        self.status_patterns = STATUS_PATTERNS
        self.allergen_list = ALLERGEN_LIST

    def extract_lab_values(self, text: str) -> list[dict[str, str]]:
        results = []
        for test_name, pattern in self.lab_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                value = match[0] if isinstance(match, tuple) else match
                unit = match[1] if isinstance(match, tuple) and len(match) > 1 else ""
                results.append({
                    "test": test_name,
                    "value": value.replace(",", ""),
                    "unit": unit or "N/A",
                })
        return results

    def extract_status(self, text: str) -> list[str]:
        return [status for status, pattern in self.status_patterns.items() if re.search(pattern, text)]

    def extract_allergies(self, text: str) -> list[str]:
        text_lower = text.lower()
        return [a for a in self.allergen_list if a in text_lower]
