"""BackgroundTasks entry point — runs the pipeline after the upload HTTP
response has already been returned. Opens its own connection since the
request-scoped one closes when the response is sent."""
from backend.agents.pipeline import ClinicalPipeline
from backend.db.database import get_connection


def run_pipeline_in_background(*, database_path: str, pipeline: ClinicalPipeline, report_id: int) -> None:
    conn = get_connection(database_path)
    try:
        pipeline.run(conn, report_id)
    finally:
        conn.close()
