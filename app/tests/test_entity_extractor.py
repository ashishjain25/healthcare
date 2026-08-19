from backend.documents.entity_extractor import EntityExtractor


def test_extract_lab_values_from_cbc_text():
    extractor = EntityExtractor()
    text = """CBC Report:
    Hemoglobin: 10.2 g/dL (LOW)
    WBC: 12,500 /uL (HIGH)
    Platelet: 180,000 /uL (NORMAL)"""

    labs = extractor.extract_lab_values(text)
    lab_names = {lab["test"] for lab in labs}
    assert "hemoglobin" in lab_names
    assert "wbc" in lab_names
    assert "platelet" in lab_names

    hgb = next(lab for lab in labs if lab["test"] == "hemoglobin")
    assert hgb["value"] == "10.2"
    assert hgb["unit"] == "g/dL"


def test_extract_status_indicators():
    extractor = EntityExtractor()
    statuses = extractor.extract_status("Creatinine: 2.1 mg/dL (HIGH), STAT review needed")
    assert "high" in statuses
    assert "critical" in statuses


def test_extract_allergies():
    extractor = EntityExtractor()
    allergies = extractor.extract_allergies(
        "Patient has severe peanut allergy with history of anaphylaxis. Also allergic to penicillin."
    )
    assert "peanut" in allergies
    assert "penicillin" in allergies
    assert "milk" not in allergies


def test_lab_pattern_and_allergen_counts_match_spec():
    extractor = EntityExtractor()
    assert len(extractor.lab_patterns) >= 10
    assert len(extractor.allergen_list) >= 15
