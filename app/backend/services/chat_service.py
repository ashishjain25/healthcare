"""RAG-grounded chatbot backing both the patient-facing 'AI Health Assistant'
and the doctor-facing 'AI Clinical Assistant'. Patient-report retrieval is
filtered by patient_id in ChromaDB metadata — that filter, not a prompt
instruction, is what keeps one patient's data out of another's chat context.
"""
import sqlite3

from backend.db.repositories import chat_repo
from backend.llm.openai_client import OpenAIClient
from backend.vectorstore.chroma_store import ChromaStore

PATIENT_SYSTEM_PROMPT = """You are a patient-facing AI Health Assistant. Answer the \
patient's question using ONLY the provided context from their own reports and general \
reference material. Use plain, non-technical language. Never state or imply a new \
diagnosis; if the context suggests something concerning, recommend the patient discuss \
it with their doctor. If the context doesn't contain enough information to answer, say so."""

DOCTOR_SYSTEM_PROMPT = """You are a clinician-facing AI Clinical Assistant. Answer the \
doctor's question using ONLY the provided context from the patient's reports and \
reference material. Clinical terminology is appropriate. If the context doesn't contain \
enough information to answer, say so rather than speculating."""


def _build_context(patient_results: dict, reference_results: dict) -> tuple[str, list[str]]:
    chunks: list[str] = []
    chunk_ids: list[str] = []

    docs = patient_results.get("documents", [[]])[0]
    ids = patient_results.get("ids", [[]])[0]
    for doc, doc_id in zip(docs, ids):
        chunks.append(f"[Patient report excerpt] {doc}")
        chunk_ids.append(doc_id)

    ref_docs = reference_results.get("documents", [[]])[0]
    ref_ids = reference_results.get("ids", [[]])[0]
    for doc, doc_id in zip(ref_docs, ref_ids):
        chunks.append(f"[Reference material] {doc}")
        chunk_ids.append(doc_id)

    return "\n\n".join(chunks) if chunks else "(no relevant context found)", chunk_ids


def ask(conn: sqlite3.Connection, *, vector_store: ChromaStore, llm_client: OpenAIClient,
        user_id: int, patient_id: int, role: str, question: str) -> str:
    session_id = chat_repo.get_or_create_session(conn, user_id=user_id, patient_id=patient_id, role=role)
    chat_repo.add_message(conn, chat_session_id=session_id, role="user", content=question)

    patient_results = vector_store.query(
        "patient_reports", query_text=question, embed_fn=llm_client.embed,
        n_results=5, where={"patient_id": patient_id},
    )
    reference_results = vector_store.query(
        "reference_knowledge", query_text=question, embed_fn=llm_client.embed, n_results=3,
    )
    context_text, chunk_ids = _build_context(patient_results, reference_results)

    system_prompt = PATIENT_SYSTEM_PROMPT if role == "patient" else DOCTOR_SYSTEM_PROMPT
    prompt = f"Context:\n{context_text}\n\nQuestion: {question}"
    answer = llm_client.complete(prompt=prompt, system=system_prompt, temperature=0.2)

    chat_repo.add_message(
        conn, chat_session_id=session_id, role="assistant", content=answer, retrieved_chunk_ids=chunk_ids,
    )
    return answer


def get_history(conn: sqlite3.Connection, *, user_id: int, patient_id: int, role: str) -> list[dict]:
    session_id = chat_repo.get_or_create_session(conn, user_id=user_id, patient_id=patient_id, role=role)
    return [dict(m) for m in chat_repo.list_messages(conn, session_id)]
