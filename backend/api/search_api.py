# api/search_api.py — FastAPI app: ERD/diagram upload + /ask (no vector RAG).
#
# Code attribution (for provenance / authorship proof):
# Raja Nagori <raja.nagori@owasp.org>
#
__code_written_by = "Raja Nagori <raja.nagori@owasp.org>"

import os
import time

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field
from typing import List, Union

from api.erd_processor import router as erd_router
from qa.qa_chain import QAService, ThreatModelReport
from utils.audit import audit_event
from utils.auth import AuthContext, is_production_mode, require_auth
from utils.config_loader import load_config
from utils.rate_limit import enforce_rate_limit


class AskRequest(BaseModel):
    q: str = Field(..., min_length=1, description="User question")
    analysis_id: str | None = Field(default=None, description="Analysis session UUID")
    structured: bool = False
    k: int = Field(default=3, ge=1, le=12)

class ChatResponse(BaseModel):
    """Plain chat response returned when `structured=false`."""

    answer: str
    sources: List[str] = Field(default_factory=list)

cfg = load_config("config.yaml")
_langsmith = cfg.get("langsmith") or {}
_api_key = (_langsmith.get("api_key") or "").strip()
if _langsmith and _api_key:
    os.environ["LANGSMITH_API_KEY"] = _api_key
    os.environ["LANGSMITH_PROJECT"] = _langsmith.get("project") or "default"
    os.environ["LANGSMITH_ENDPOINT"] = _langsmith.get(
        "endpoint", "https://api.smith.langchain.com"
    )
    os.environ["LANGSMITH_TRACING"] = "true"
    print(f"✅ LangSmith tracing enabled for project: {os.environ['LANGSMITH_PROJECT']}")

app = FastAPI(
    title="Chakravyuh API",
    redirect_slashes=False,
)
MAX_REQUEST_BYTES = int(os.getenv("MAX_REQUEST_BYTES", str(55 * 1024 * 1024)))
ENABLE_DEPRECATED_ENDPOINTS = (
    (os.getenv("ENABLE_DEPRECATED_ENDPOINTS") or "").strip().lower() in {"1", "true", "yes"}
    or not is_production_mode()
)

_cors_env = os.getenv("CORS_ALLOW_ORIGINS", "")
_cors_allow_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]
if not _cors_allow_origins and not is_production_mode():
    _cors_allow_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
_allow_origin_regex = None
if not is_production_mode():
    _allow_origin_regex = r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+):3000$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins,
    allow_origin_regex=_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(erd_router, prefix="/api", tags=["ERD Processing"])


@app.middleware("http")
async def request_size_guard(request: Request, call_next):
    length_header = request.headers.get("content-length")
    if length_header:
        try:
            if int(length_header) > MAX_REQUEST_BYTES:
                raise HTTPException(status_code=413, detail="Request body too large.")
        except ValueError:
            pass
    return await call_next(request)


@app.get("/search", include_in_schema=False)
async def search_removed():
    """Vector search removed; use /ask with uploaded ERD + diagram context."""
    if not ENABLE_DEPRECATED_ENDPOINTS:
        raise HTTPException(status_code=404, detail="Not found")
    raise HTTPException(
        status_code=410,
        detail="Semantic search has been removed. Use chat (/ask) with uploaded documents.",
    )


def _run_ask(
    q: str,
    k: int,
    structured: bool,
    service: str | None,
    start_date: str | None,
    end_date: str | None,
    analysis_id: str | None,
    owner_subject: str,
):
    start_time = time.time()
    qa_service = QAService(k=min(k, 6))
    result = qa_service.answer(
        q,
        k=min(k, 6),
        structured=structured,
        service=service,
        start_date=start_date,
        end_date=end_date,
        analysis_id=analysis_id,
        owner_subject=owner_subject,
    )
    elapsed = time.time() - start_time
    print(f"Query completed in {elapsed:.2f} seconds")
    return result


@app.post("/ask", response_model=Union[ChatResponse, ThreatModelReport])
async def ask_post(body: AskRequest, request: Request, auth: AuthContext = Depends(require_auth)):
    try:
        enforce_rate_limit(f"{auth.subject}:ask", max_requests=60, window_seconds=60)
        if is_production_mode() and not (body.analysis_id or "").strip():
            raise HTTPException(status_code=400, detail="analysis_id is required in production mode.")
        result = _run_ask(
            body.q,
            body.k,
            body.structured,
            None,
            None,
            None,
            body.analysis_id,
            auth.subject,
        )
        audit_event(
            request, "ask_completed", auth.subject, analysis_id=body.analysis_id or "", structured=body.structured
        )
        return result
    except Exception as e:
        print(f"Error in ask POST: {str(e)}")
        if isinstance(e, PermissionError):
            raise HTTPException(status_code=403, detail=str(e)) from e
        if isinstance(e, HTTPException):
            raise
        audit_event(request, "ask_failed", auth.subject, error=str(e))
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}") from e


@app.get("/ask", include_in_schema=False)
async def ask(
    request: Request,
    q: str = Query(..., description="Question"),
    k: int = 3,
    structured: bool = False,
    service: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    analysis_id: str | None = Query(default=None, description="Analysis session UUID"),
    auth: AuthContext = Depends(require_auth),
):
    try:
        enforce_rate_limit(f"{auth.subject}:ask-get", max_requests=30, window_seconds=60)
        if is_production_mode() and not (analysis_id or "").strip():
            raise HTTPException(status_code=400, detail="analysis_id is required in production mode.")
        result = _run_ask(q, k, structured, service, start_date, end_date, analysis_id, auth.subject)
        audit_event(
            request, "ask_completed", auth.subject, analysis_id=analysis_id or "", structured=structured
        )
        return result
    except Exception as e:
        print(f"Error in ask endpoint: {str(e)}")
        if isinstance(e, PermissionError):
            raise HTTPException(status_code=403, detail=str(e)) from e
        if isinstance(e, HTTPException):
            raise
        audit_event(request, "ask_failed", auth.subject, error=str(e))
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}") from e


@app.get("/threat-modeling", include_in_schema=False)
async def threat_modeling(
    request: Request,
    q: str = Query(..., description="Threat modeling query"),
    k: int = 2,
    analysis_id: str | None = Query(default=None, description="Analysis session UUID"),
    auth: AuthContext = Depends(require_auth),
):
    try:
        start_time = time.time()
        qa = QAService(k=min(k, 4))
        result = qa.answer(
            q, k=min(k, 4), structured=True, analysis_id=analysis_id, owner_subject=auth.subject
        )
        elapsed = time.time() - start_time
        print(f"Threat modeling completed in {elapsed:.2f} seconds")
        audit_event(request, "threat_modeling_completed", auth.subject, analysis_id=analysis_id or "")
        return result
    except Exception as e:
        print(f"Error in threat modeling: {str(e)}")
        if isinstance(e, PermissionError):
            raise HTTPException(status_code=403, detail=str(e)) from e
        return {
            "scope_summary": f"Error processing request: {str(e)}",
            "threat_analysis": [],
            "assets": [],
            "actors": [],
            "key_controls": [],
            "residual_risk_rating": "Unknown",
            "assumptions": [],
            "sources": [],
        }


@app.get("/openapi.json", include_in_schema=False)
async def openapi_endpoint():
    return get_openapi(
        title="Chakravyuh API",
        version="1.0.0",
        routes=app.routes,
    )


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return {}


@app.get("/api/embedding-status", include_in_schema=False)
async def embedding_status(auth: AuthContext = Depends(require_auth)):
    """Embeddings removed; always ready for UI compatibility."""
    return {"ready": True, "message": "Embeddings disabled; use ERD PDF + diagram upload."}


@app.get("/health")
async def health_check():
    from utils.db_utils import get_conn
    from utils.llm_provider import get_llm

    health_status = {
        "status": "ok",
        "timestamp": time.time(),
        "message": "API is running",
        "components": {},
    }

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        health_status["components"]["database"] = {
            "status": "healthy",
            "message": "PostgreSQL reachable",
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e),
            "message": "Database connection failed",
        }

    try:
        cfg = load_config("config.yaml")
        get_llm(cfg)
        health_status["components"]["llm"] = {
            "status": "healthy",
            "provider": cfg.get("provider", "unknown"),
            "message": "LLM instance available",
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["components"]["llm"] = {
            "status": "unhealthy",
            "error": str(e),
            "message": "LLM initialization failed",
        }

    health_status["components"]["cache"] = {
        "status": "healthy",
        "message": "In-process caches operational",
    }

    return health_status


@app.get("/metrics", include_in_schema=False)
async def get_metrics(auth: AuthContext = Depends(require_auth)):
    from utils.metrics import get_metrics

    metrics = get_metrics()
    return {"status": "ok", "metrics": metrics.get_summary()}


@app.options("/health", include_in_schema=False)
async def health_check_options():
    return {"status": "ok", "message": "CORS preflight for health check"}


@app.get("/debug", include_in_schema=False)
async def debug_endpoint(request: Request, auth: AuthContext = Depends(require_auth)):
    return {
        "status": "ok",
        "headers": dict(request.headers),
        "method": request.method,
        "url": str(request.url),
        "client": request.client.host if request.client else "unknown",
    }


@app.get("/dataset-status", include_in_schema=False)
async def get_dataset_status(auth: AuthContext = Depends(require_auth)):
    if not ENABLE_DEPRECATED_ENDPOINTS:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "status": "deprecated",
        "message": "Vector dataset status removed. Use GET /api/analysis-status.",
    }

