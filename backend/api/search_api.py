# api/search_api.py — FastAPI app: ERD/diagram upload + /ask (no vector RAG).
import os
import time

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field

from api.erd_processor import router as erd_router
from qa.qa_chain import QAService
from utils.config_loader import load_config


class AskRequest(BaseModel):
    q: str = Field(..., min_length=1, description="User question")
    analysis_id: str | None = Field(default=None, description="Analysis session UUID")
    structured: bool = False
    k: int = Field(default=3, ge=1, le=12)

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

_cors_env = os.getenv("CORS_ALLOW_ORIGINS", "")
_cors_allow_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]
if not _cors_allow_origins:
    _cors_allow_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins,
    # LAN/dev convenience for browser access from private network hosts.
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+):3000$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(erd_router, prefix="/api", tags=["ERD Processing"])


@app.get("/search")
async def search_removed():
    """Vector search removed; use /ask with uploaded ERD + diagram context."""
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
    )
    elapsed = time.time() - start_time
    print(f"Query completed in {elapsed:.2f} seconds")
    return result


@app.post("/ask")
async def ask_post(body: AskRequest):
    try:
        return _run_ask(
            body.q,
            body.k,
            body.structured,
            None,
            None,
            None,
            body.analysis_id,
        )
    except Exception as e:
        print(f"Error in ask POST: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}") from e


@app.get("/ask")
async def ask(
    q: str = Query(..., description="Question"),
    k: int = 3,
    structured: bool = False,
    service: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    analysis_id: str | None = Query(default=None, description="Analysis session UUID"),
):
    try:
        return _run_ask(q, k, structured, service, start_date, end_date, analysis_id)
    except Exception as e:
        print(f"Error in ask endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}") from e


@app.get("/threat-modeling")
async def threat_modeling(
    q: str = Query(..., description="Threat modeling query"),
    k: int = 2,
    analysis_id: str | None = Query(default=None, description="Analysis session UUID"),
):
    try:
        start_time = time.time()
        qa = QAService(k=min(k, 4))
        result = qa.answer(
            q, k=min(k, 4), structured=True, analysis_id=analysis_id
        )
        elapsed = time.time() - start_time
        print(f"Threat modeling completed in {elapsed:.2f} seconds")
        return result
    except Exception as e:
        print(f"Error in threat modeling: {str(e)}")
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


@app.get("/openapi.json")
async def openapi_endpoint():
    return get_openapi(
        title="Chakravyuh API",
        version="1.0.0",
        routes=app.routes,
    )


@app.get("/favicon.ico")
async def favicon():
    return {}


@app.get("/api/embedding-status")
async def embedding_status():
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


@app.get("/metrics")
async def get_metrics():
    from utils.metrics import get_metrics

    metrics = get_metrics()
    return {"status": "ok", "metrics": metrics.get_summary()}


@app.options("/health")
async def health_check_options():
    return {"status": "ok", "message": "CORS preflight for health check"}


@app.get("/debug")
async def debug_endpoint(request: Request):
    return {
        "status": "ok",
        "headers": dict(request.headers),
        "method": request.method,
        "url": str(request.url),
        "client": request.client.host if request.client else "unknown",
    }


@app.get("/dataset-status")
async def get_dataset_status():
    return {
        "status": "deprecated",
        "message": "Vector dataset status removed. Use GET /api/analysis-status.",
    }

