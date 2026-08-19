"""FastAPI application entrypoint. Builds the process-lifetime singletons
(ChromaStore, ObservabilityPort, OpenAIClient, MedicalKnowledgeGraph,
ClinicalPipeline) once at startup and stores them on app.state — this is the
one place the object graph is wired, replacing the notebook's module globals.

Run from the app/ directory: `uvicorn backend.main:app --reload`
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from backend.agents.clinical_analysis import ClinicalAnalysisAgent
from backend.agents.data_extraction import DataExtractionAgent
from backend.agents.insight_generation import InsightGenerationAgent
from backend.agents.patient_communication import PatientCommunicationAgent
from backend.agents.pipeline import ClinicalPipeline
from backend.agents.risk_detection import RiskDetectionAgent
from backend.api import routes_auth, routes_doctor, routes_pages, routes_patient, routes_radiologist
from backend.config import get_settings
from backend.db.database import init_db
from backend.knowledge_graph import MedicalKnowledgeGraph
from backend.llm.openai_client import OpenAIClient
from backend.observability.langfuse_observability import LangfuseObservability
from backend.observability.noop_observability import NoOpObservability
from backend.vectorstore.chroma_store import ChromaStore

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist" / "assets"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_db(settings.DATABASE_PATH)

    app.state.vector_store = ChromaStore(settings.CHROMA_PERSIST_DIR)
    app.state.knowledge_graph = MedicalKnowledgeGraph()
    app.state.llm_client = OpenAIClient(
        api_key=settings.OPENAI_API_KEY, chat_model=settings.OPENAI_CHAT_MODEL,
        embedding_model=settings.OPENAI_EMBEDDING_MODEL,
    )

    if settings.langfuse_configured:
        app.state.observability = LangfuseObservability(
            public_key=settings.LANGFUSE_PUBLIC_KEY, secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
    else:
        app.state.observability = NoOpObservability()

    llm_client = app.state.llm_client
    observability = app.state.observability
    app.state.pipeline = ClinicalPipeline(
        data_extraction_agent=DataExtractionAgent(llm_client=llm_client, observability=observability),
        clinical_analysis_agent=ClinicalAnalysisAgent(llm_client=llm_client, observability=observability),
        risk_detection_agent=RiskDetectionAgent(
            llm_client=llm_client, observability=observability, knowledge_graph=app.state.knowledge_graph,
        ),
        insight_generation_agent=InsightGenerationAgent(llm_client=llm_client, observability=observability),
        patient_communication_agent=PatientCommunicationAgent(llm_client=llm_client, observability=observability),
        observability=observability,
        extraction_confidence_threshold=settings.EXTRACTION_CONFIDENCE_THRESHOLD,
        insight_confidence_threshold=settings.INSIGHT_CONFIDENCE_THRESHOLD,
    )

    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Clinical Intelligence System", lifespan=lifespan)
    app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET)

    if _ASSETS_DIR.exists():
        app.mount("/assets", StaticFiles(directory=str(_ASSETS_DIR)), name="assets")

    app.include_router(routes_auth.router)
    app.include_router(routes_patient.router)
    app.include_router(routes_doctor.router)
    app.include_router(routes_radiologist.router)
    # Catch-all SPA shell — must be included last so it never shadows the API
    # routers or the /assets static mount above.
    app.include_router(routes_pages.router)

    return app


app = create_app()
