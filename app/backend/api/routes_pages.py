"""SPA shell serving. The React app (frontend/dist, built via `npm run
build`) owns all client-side routing — this router just hands back
index.html for any non-API path so React Router can take over, plus the
handful of top-level static assets Vite emits outside of /assets (favicon)
and the /healthz liveness check. Registered last in main.py so the catch-all
never shadows the /api/* routers or the /assets static mount — within this
file, /healthz and /favicon.svg are also declared before the catch-all,
since Starlette matches routes in registration order, not by specificity.
"""
import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from backend.config import get_settings
from backend.db.database import get_connection

router = APIRouter(tags=["pages"])

_DIST_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
_INDEX_HTML = _DIST_DIR / "index.html"


def _spa_shell() -> FileResponse:
    if not _INDEX_HTML.exists():
        raise HTTPException(
            status_code=503,
            detail="Frontend build not found — run `npm run build` in frontend/ first.",
        )
    return FileResponse(str(_INDEX_HTML))


@router.get("/healthz", include_in_schema=False)
def healthz() -> JSONResponse:
    """Liveness/readiness probe for load balancers and container orchestrators.
    Actually touches SQLite rather than just returning 200 unconditionally —
    an unmounted data volume (the most likely real deployment failure mode)
    should fail health checks, not serve a green light over a broken DB."""
    settings = get_settings()
    try:
        conn = get_connection(settings.DATABASE_PATH)
        try:
            conn.execute("SELECT 1")
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return JSONResponse(status_code=503, content={"status": "error", "detail": str(exc)})
    return JSONResponse(status_code=200, content={"status": "ok"})


@router.get("/favicon.svg", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(str(_DIST_DIR / "favicon.svg"))


@router.get("/{full_path:path}", include_in_schema=False)
def spa_catch_all(full_path: str) -> FileResponse:
    return _spa_shell()
