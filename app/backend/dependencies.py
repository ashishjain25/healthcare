"""Single wiring point for dependency injection. Process-lifetime singletons
(ChromaStore, ObservabilityPort, OpenAIClient, MedicalKnowledgeGraph,
ClinicalPipeline) live on app.state (set up once in main.py's lifespan);
per-request state is just a fresh sqlite3.Connection.
"""
from collections.abc import Generator

from fastapi import Depends, Request

from backend.agents.pipeline import ClinicalPipeline
from backend.config import Settings, get_settings
from backend.db.database import get_connection
from backend.knowledge_graph import MedicalKnowledgeGraph
from backend.llm.openai_client import OpenAIClient
from backend.observability.port import ObservabilityPort
from backend.vectorstore.chroma_store import ChromaStore


def get_db(settings: Settings = Depends(get_settings)) -> Generator:
    conn = get_connection(settings.DATABASE_PATH)
    try:
        yield conn
    finally:
        conn.close()


def get_vector_store(request: Request) -> ChromaStore:
    return request.app.state.vector_store


def get_knowledge_graph(request: Request) -> MedicalKnowledgeGraph:
    return request.app.state.knowledge_graph


def get_observability(request: Request) -> ObservabilityPort:
    return request.app.state.observability


def get_llm_client(request: Request) -> OpenAIClient:
    return request.app.state.llm_client


def get_pipeline(request: Request) -> ClinicalPipeline:
    return request.app.state.pipeline
