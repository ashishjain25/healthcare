"""Seeds a fresh database + vector store from the real Datasets/ folder so the
demo has realistic data to click through. Run from the app/ directory:

    python scripts/reset_db.py
    python scripts/seed_data.py

If OPENAI_API_KEY is not configured, reports are still created and structural
data (users, patients, allergies, history) is fully seeded, but the AI
pipeline and reference-knowledge embedding are skipped (each report stays
'pending_pipeline') — the script prints a clear note explaining this so it's
never mistaken for a bug.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import openpyxl  # noqa: E402

from backend.agents.clinical_analysis import ClinicalAnalysisAgent  # noqa: E402
from backend.agents.data_extraction import DataExtractionAgent  # noqa: E402
from backend.agents.insight_generation import InsightGenerationAgent  # noqa: E402
from backend.agents.patient_communication import PatientCommunicationAgent  # noqa: E402
from backend.agents.pipeline import ClinicalPipeline  # noqa: E402
from backend.agents.risk_detection import RiskDetectionAgent  # noqa: E402
from backend.auth.security import hash_password  # noqa: E402
from backend.config import get_settings  # noqa: E402
from backend.db.database import get_connection, init_db  # noqa: E402
from backend.db.repositories import patient_repo, report_repo, user_repo  # noqa: E402
from backend.documents.processor import DocumentProcessor  # noqa: E402
from backend.knowledge_graph import MedicalKnowledgeGraph  # noqa: E402
from backend.llm.openai_client import OpenAIClient  # noqa: E402
from backend.observability.noop_observability import NoOpObservability  # noqa: E402
from backend.vectorstore.chroma_store import ChromaStore  # noqa: E402

DATASETS_DIR = Path(__file__).resolve().parent.parent.parent / "Datasets"
DEFAULT_PASSWORD = "password123"


def _docx_paths(*parts: str) -> Path:
    return DATASETS_DIR.joinpath(*parts)


SEED_DOCTORS = [
    {"email": "sharma@cis.com", "full_name": "Dr. Anita Sharma"},
    {"email": "verma@cis.com", "full_name": "Dr. Rohan Verma"},
]

SEED_RADIOLOGISTS = [
    {"email": "singh@cis.com", "full_name": "Karan Singh (Radiologist)"},
    {"email": "iyer@cis.com", "full_name": "Meera Iyer (Lab Technician)"},
]

# Each patient's report list references real files under Datasets/. The
# "CBC Report - Patient Anal.pdf" is a genuinely scanned image with no OCR
# text layer (verified in tests/test_document_processor.py) — used
# deliberately for Priya Nair to demonstrate the Data Extraction agent's
# "low-confidence extraction flagged for review" negative scenario.
SEED_PATIENTS = [
    {
        "full_name": "Aisha Khan", "email": "aisha.khan@cis.com", "mrn": "MRN-0001",
        "dob": "1990-03-12", "sex": "F", "blood_group": "O+",
        "symptoms": ["fatigue", "shortness_of_breath"],
        "conditions": [],
        "allergies": [("peanut", "Food", "SEVERE", "Anaphylaxis on prior exposure")],
        "reports": [
            {"file": _docx_paths("Clinician , Doctor", "CBC report.zz.docx"), "report_type": "lab", "category": "cbc", "uploader": "radiologist"},
            {"file": _docx_paths("Radiologist", "CHEST X-RAY (CXR) zz.docx"), "report_type": "radiology", "category": "chest_xray", "uploader": "radiologist"},
            {"file": _docx_paths("Patient", "Patient discharge summary sample zz.docx"), "report_type": "discharge_summary", "category": "discharge_summary", "uploader": "doctor"},
        ],
    },
    {
        "full_name": "Ravi Verma", "email": "ravi.verma@cis.com", "mrn": "MRN-0002",
        "dob": "1978-07-22", "sex": "M", "blood_group": "B+",
        "symptoms": ["fatigue"],
        "conditions": ["Hypothyroidism (prior diagnosis)"],
        "allergies": [],
        "reports": [
            {"file": _docx_paths("Clinician , Doctor", "Thyroid function test sample zz.docx"), "report_type": "lab", "category": "thyroid", "uploader": "radiologist"},
            {"file": _docx_paths("Radiologist", "MRI SPINE zz.docx"), "report_type": "radiology", "category": "mri_spine", "uploader": "radiologist"},
        ],
    },
    {
        "full_name": "Meena Patel", "email": "meena.patel@cis.com", "mrn": "MRN-0003",
        "dob": "1985-11-02", "sex": "F", "blood_group": "A+",
        "symptoms": ["fever", "cough"],
        "conditions": [],
        "allergies": [("sulfa", "Medication", "MODERATE", "Skin rash within hours of exposure")],
        "reports": [
            {"file": _docx_paths("Clinician , Doctor", "Liver function test sample zz.docx"), "report_type": "lab", "category": "lft", "uploader": "radiologist"},
            {"file": _docx_paths("Radiologist", "CT BRAIN SCAN zz.docx"), "report_type": "radiology", "category": "ct_brain", "uploader": "radiologist"},
            {"file": _docx_paths("Patient", "Asthama sample and details.docx"), "report_type": "physician_note", "category": "asthma", "uploader": "doctor"},
        ],
    },
    {
        "full_name": "John Fernandes", "email": "john.fernandes@cis.com", "mrn": "MRN-0004",
        "dob": "1965-01-30", "sex": "M", "blood_group": "AB+",
        "symptoms": ["shortness_of_breath"],
        "conditions": [],
        "allergies": [("shellfish", "Food", "SEVERE", "Throat swelling on prior exposure")],
        "reports": [
            {"file": _docx_paths("Clinician , Doctor", "Kidney function test sample zz.docx"), "report_type": "lab", "category": "kft", "uploader": "radiologist"},
            {"file": _docx_paths("Radiologist", "ULTRASOUND ABDOMEN zz.docx"), "report_type": "radiology", "category": "ultrasound_abdomen", "uploader": "radiologist"},
        ],
    },
    {
        "full_name": "Priya Nair", "email": "priya.nair@cis.com", "mrn": "MRN-0005",
        "dob": "1998-09-15", "sex": "F", "blood_group": "O-",
        "symptoms": [],
        "conditions": [],
        "allergies": [],
        "reports": [
            {"file": _docx_paths("Clinician , Doctor", "CBC Report - Patient Anal.pdf"), "report_type": "lab", "category": "cbc", "uploader": "radiologist"},
            {"file": _docx_paths("Clinician , Doctor", "Blood sugar test report zz.docx"), "report_type": "lab", "category": "blood_sugar", "uploader": "radiologist"},
        ],
    },
]

# Reference material seeded into the "reference_knowledge" ChromaDB collection
# — everything under Clinician/Radiologist/allergy-subfolder docs, used for
# reference-range/cross-reactivity grounding and general medical Q&A.
REFERENCE_FOLDERS = [
    _docx_paths("Clinician , Doctor"),
    _docx_paths("Radiologist"),
    _docx_paths("Patient", "Food allergy zz"),
    _docx_paths("Patient", "Medication allergy zz"),
    _docx_paths("Patient", "Environment allergy zz"),
    _docx_paths("Patient", "Skin allergy zz"),
]


def _is_real_file(path: Path) -> bool:
    """Excludes Word lock files (~$...) and non-existent paths."""
    return path.exists() and not path.name.startswith("~$")


def seed_users(conn) -> dict:
    ids = {"doctors": [], "radiologists": [], "patients": {}}

    for doc in SEED_DOCTORS:
        h, s = hash_password(DEFAULT_PASSWORD)
        uid = user_repo.create_user(conn, email=doc["email"], password_hash=h, password_salt=s,
                                     full_name=doc["full_name"], role="doctor")
        ids["doctors"].append(uid)

    for rad in SEED_RADIOLOGISTS:
        h, s = hash_password(DEFAULT_PASSWORD)
        uid = user_repo.create_user(conn, email=rad["email"], password_hash=h, password_salt=s,
                                     full_name=rad["full_name"], role="radiologist")
        ids["radiologists"].append(uid)

    for i, patient in enumerate(SEED_PATIENTS):
        h, s = hash_password(DEFAULT_PASSWORD)
        user_id = user_repo.create_user(conn, email=patient["email"], password_hash=h, password_salt=s,
                                         full_name=patient["full_name"], role="patient")
        patient_id = patient_repo.create_patient(
            conn, user_id=user_id, mrn=patient["mrn"], dob=patient["dob"], sex=patient["sex"],
            blood_group=patient["blood_group"], known_conditions=None,
            primary_doctor_id=ids["doctors"][i % len(ids["doctors"])],
        )
        for symptom in patient["symptoms"]:
            patient_repo.add_medical_history(conn, patient_id=patient_id, entry_type="symptom",
                                              description=symptom, entry_date=None)
        for condition in patient["conditions"]:
            patient_repo.add_medical_history(conn, patient_id=patient_id, entry_type="condition",
                                              description=condition, entry_date=None)
        for allergen, category, severity, notes in patient["allergies"]:
            patient_repo.add_allergy(conn, patient_id=patient_id, allergen=allergen, category=category,
                                      severity=severity, reaction_notes=notes, source="self_reported")

        ids["patients"][patient["mrn"]] = {"user_id": user_id, "patient_id": patient_id}

    return ids


def seed_reports(conn, vector_store, llm_client, settings, ids, run_pipeline: bool) -> tuple[int, int]:
    processor = DocumentProcessor()
    pipeline = None
    if run_pipeline:
        kg = MedicalKnowledgeGraph()
        obs = NoOpObservability()
        pipeline = ClinicalPipeline(
            data_extraction_agent=DataExtractionAgent(llm_client=llm_client, observability=obs),
            clinical_analysis_agent=ClinicalAnalysisAgent(llm_client=llm_client, observability=obs),
            risk_detection_agent=RiskDetectionAgent(llm_client=llm_client, observability=obs, knowledge_graph=kg),
            insight_generation_agent=InsightGenerationAgent(llm_client=llm_client, observability=obs),
            patient_communication_agent=PatientCommunicationAgent(llm_client=llm_client, observability=obs),
            observability=obs,
            extraction_confidence_threshold=settings.EXTRACTION_CONFIDENCE_THRESHOLD,
            insight_confidence_threshold=settings.INSIGHT_CONFIDENCE_THRESHOLD,
        )

    reports_created = 0
    pipelines_run = 0

    for patient in SEED_PATIENTS:
        ref = ids["patients"][patient["mrn"]]
        for report_spec in patient["reports"]:
            file_path = report_spec["file"]
            if not _is_real_file(file_path):
                print(f"  [skip] missing sample file: {file_path}")
                continue

            uploader_role = report_spec["uploader"]
            uploader_id = (ids["radiologists"][0] if uploader_role == "radiologist" else ids["doctors"][0])

            parsed = processor.process_file(file_path)
            raw_text = parsed["full_text"] if parsed else ""
            table_text = parsed["table_text"] if parsed else ""

            report_id = report_repo.create_report(
                conn, patient_id=ref["patient_id"], uploaded_by_user_id=uploader_id,
                report_type=report_spec["report_type"], category=report_spec["category"],
                original_filename=file_path.name, file_path=str(file_path),
                file_format=file_path.suffix.lstrip(".").lower(),
                raw_text=raw_text, table_text=table_text,
            )
            reports_created += 1

            full_text = f"{raw_text}\n{table_text}".strip()
            if full_text and settings.openai_configured:
                try:
                    vector_store.add_document(
                        "patient_reports", doc_id=f"report-{report_id}", text=full_text,
                        metadata={"patient_id": ref["patient_id"], "report_id": report_id,
                                  "report_type": report_spec["report_type"], "category": report_spec["category"],
                                  "report_date": ""},
                        embed_fn=llm_client.embed,
                    )
                except Exception as exc:
                    # A transient network/API failure here (seen in practice: SSL/proxy
                    # errors reaching OpenAI) must not lose every other report's already-
                    # seeded data — log and move on rather than crashing the whole script.
                    print(f"  [warn] embedding failed for report {report_id} "
                          f"({patient['full_name']} / {report_spec['category']}): {exc}")

            if pipeline is not None:
                try:
                    result = pipeline.run(conn, report_id)
                    pipelines_run += 1
                    status_note = "OK" if result.status == "completed" else f"FAILED: {result.error}"
                except Exception as exc:
                    status_note = f"FAILED (unhandled): {exc}"
                print(f"  ran pipeline for report {report_id} ({patient['full_name']} / "
                      f"{report_spec['category']}): {status_note}")

    return reports_created, pipelines_run


def seed_reference_knowledge(vector_store, llm_client, settings) -> int:
    if not settings.openai_configured:
        print("  OPENAI_API_KEY not configured — skipping reference_knowledge embedding.")
        return 0

    processor = DocumentProcessor()
    count = 0
    for folder in REFERENCE_FOLDERS:
        if not folder.exists():
            continue
        for file_path in sorted(folder.glob("*.docx")):
            if not _is_real_file(file_path):
                continue
            parsed = processor.process_file(file_path)
            if not parsed or not parsed["full_text"].strip():
                continue
            try:
                vector_store.add_document(
                    "reference_knowledge", doc_id=f"ref-{file_path.stem}",
                    text=parsed["full_text"] + "\n" + parsed["table_text"],
                    metadata={"category": folder.name, "source_file": file_path.name},
                    embed_fn=llm_client.embed,
                )
                count += 1
            except Exception as exc:
                print(f"  [warn] embedding failed for reference file {file_path.name}: {exc}")

    glossary_path = _docx_paths("Training", "Medical_Glossary_Expanded.xlsx")
    if glossary_path.exists():
        wb = openpyxl.load_workbook(str(glossary_path), read_only=True)
        ws = wb.worksheets[0]
        rows = list(ws.iter_rows(values_only=True))
        header, data_rows = rows[0], rows[1:]
        for i, row in enumerate(data_rows):
            record = dict(zip(header, row))
            term = record.get("Term")
            if not term:
                continue
            text = (f"Term: {term}. Category: {record.get('Category')}. "
                    f"System: {record.get('Panel_or_System')}. "
                    f"Meaning: {record.get('Simplified_Meaning')}.")
            try:
                vector_store.add_document(
                    "reference_knowledge", doc_id=f"glossary-{i}", text=text,
                    metadata={"category": "glossary", "source_file": glossary_path.name},
                    embed_fn=llm_client.embed,
                )
                count += 1
            except Exception as exc:
                print(f"  [warn] embedding failed for glossary term {term!r}: {exc}")

    return count


def main() -> None:
    settings = get_settings()

    db_path = Path(settings.DATABASE_PATH)
    if db_path.exists():
        db_path.unlink()
    init_db(settings.DATABASE_PATH)

    chroma_dir = Path(settings.CHROMA_PERSIST_DIR)
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)

    conn = get_connection(settings.DATABASE_PATH)
    vector_store = ChromaStore(settings.CHROMA_PERSIST_DIR)
    llm_client = OpenAIClient(api_key=settings.OPENAI_API_KEY, chat_model=settings.OPENAI_CHAT_MODEL,
                               embedding_model=settings.OPENAI_EMBEDDING_MODEL)

    print("=" * 60)
    print("SEEDING CLINICAL INTELLIGENCE SYSTEM DEMO DATA")
    print("=" * 60)

    print("\n[1/3] Seeding users, patients, allergies, and history…")
    ids = seed_users(conn)
    print(f"  {len(ids['doctors'])} doctors, {len(ids['radiologists'])} radiologists, "
          f"{len(ids['patients'])} patients")

    if not settings.openai_configured:
        print("\nNOTE: OPENAI_API_KEY is not configured. Reports will be created but left "
              "'pending_pipeline' (no AI analysis, no embeddings) — set OPENAI_API_KEY in .env "
              "and re-run this script for a fully-populated demo.")

    print("\n[2/3] Seeding reports from Datasets/ and running the AI pipeline…")
    reports_created, pipelines_run = seed_reports(
        conn, vector_store, llm_client, settings, ids, run_pipeline=settings.openai_configured,
    )
    print(f"  {reports_created} reports created, {pipelines_run} pipeline runs completed")

    print("\n[3/3] Seeding reference_knowledge collection…")
    ref_count = seed_reference_knowledge(vector_store, llm_client, settings)
    print(f"  {ref_count} reference documents embedded")

    conn.close()

    print("\n" + "=" * 60)
    print("DONE. Demo login credentials (password for all: 'password123'):")
    for doc in SEED_DOCTORS:
        print(f"  doctor      | {doc['email']}")
    for rad in SEED_RADIOLOGISTS:
        print(f"  radiologist | {rad['email']}")
    for patient in SEED_PATIENTS:
        print(f"  patient     | {patient['email']}  ({patient['full_name']}, {patient['mrn']})")
    print("=" * 60)


if __name__ == "__main__":
    main()
