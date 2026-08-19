from backend.knowledge_graph import MedicalKnowledgeGraph
from backend.vectorstore.chroma_store import ChromaStore


def _fake_embed(text: str) -> list[float]:
    """Deterministic pseudo-embedding so tests don't need OpenAI."""
    h = abs(hash(text)) % 1000
    return [h / 1000.0] * 8


def test_chunk_text_short_text_returns_single_chunk():
    chunks = ChromaStore.chunk_text("just a few words", chunk_size=500, overlap=50)
    assert chunks == ["just a few words"]


def test_chunk_text_long_text_overlaps():
    text = " ".join(f"word{i}" for i in range(1200))
    chunks = ChromaStore.chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) >= 2


def test_add_and_query_document(tmp_path):
    store = ChromaStore(str(tmp_path / "chroma_test"))
    added = store.add_document(
        "test_collection",
        doc_id="DOC-1",
        text="Patient has elevated hemoglobin levels consistent with dehydration.",
        metadata={"patient_id": 1, "category": "cbc"},
        embed_fn=_fake_embed,
    )
    assert added >= 1

    results = store.query(
        "test_collection", query_text="hemoglobin dehydration", embed_fn=_fake_embed,
        n_results=3, where={"patient_id": 1},
    )
    assert len(results["documents"][0]) >= 1


def test_query_scopes_by_patient_id_metadata(tmp_path):
    store = ChromaStore(str(tmp_path / "chroma_test2"))
    store.add_document(
        "patient_reports", doc_id="P1-R1", text="Patient one report text about anemia.",
        metadata={"patient_id": 1}, embed_fn=_fake_embed,
    )
    store.add_document(
        "patient_reports", doc_id="P2-R1", text="Patient two report text about anemia.",
        metadata={"patient_id": 2}, embed_fn=_fake_embed,
    )

    results = store.query(
        "patient_reports", query_text="anemia", embed_fn=_fake_embed,
        n_results=10, where={"patient_id": 1},
    )
    metadatas = results["metadatas"][0]
    assert len(metadatas) == 1
    assert metadatas[0]["patient_id"] == 1


def test_knowledge_graph_symptom_to_diagnosis():
    kg = MedicalKnowledgeGraph()
    result = kg.find_diagnoses_for_symptoms(["fatigue", "shortness_of_breath"])
    diagnosis_names = [d for d, _ in result["diagnoses"]]
    assert "anemia" in diagnosis_names


def test_knowledge_graph_allergen_cross_reactivity():
    kg = MedicalKnowledgeGraph()
    cross = kg.get_cross_reactive_allergens("peanut")
    assert "tree_nuts" in cross
    assert kg.get_cross_reactive_allergens("unknown_allergen") == []


def test_knowledge_graph_test_to_diagnosis():
    kg = MedicalKnowledgeGraph()
    diagnoses = kg.find_diagnoses_for_test("CBC")
    assert "anemia" in diagnoses
    assert "infection" in diagnoses
