"""Enhanced API with Tier 3/5/6 features."""
from typing import Optional
from fastapi import FastAPI, Query, HTTPException, Depends, Header, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from chakravyuh.core.config import get_config
from chakravyuh.core.logging import logger
from chakravyuh.generation.chains.enhanced_qa_chain import EnhancedQAService
from chakravyuh.evaluation import BenchmarkDataset, EvaluationPipeline
from chakravyuh.evaluation.validation import ValidationInterface
from chakravyuh.security.access_control import AccessControlManager, Permission
from chakravyuh.security.validation import validate_query_params
from chakravyuh.security.csrf import csrf_protect

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Chakravyuh Enhanced RAG API",
    description="Enterprise-grade RAG API with security, knowledge graph, and evaluation",
    version="2.0.0",
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Global services
_qa_services: dict[str, EnhancedQAService] = {}
_evaluation_pipeline: Optional[EvaluationPipeline] = None
_validation_interface: Optional[ValidationInterface] = None


def get_user_id(x_user_id: Optional[str] = Header(None)) -> str:
    """Extract user ID from header or use default."""
    return x_user_id or "anonymous"


def get_qa_service(user_id: str) -> EnhancedQAService:
    """Get or create QA service for user."""
    if user_id not in _qa_services:
        _qa_services[user_id] = EnhancedQAService(user_id=user_id)
    return _qa_services[user_id]


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "version": "2.0.0", "features": ["security", "knowledge_graph", "evaluation"]}


@app.get("/api/v1/ask")
@limiter.limit("30/minute")  # 30 requests per minute per IP
async def ask(
    request: Request,
    q: str = Query(..., description="Question", min_length=1, max_length=5000),
    k: int = Query(6, description="Number of documents", ge=1, le=20),
    structured: bool = Query(False, description="Return structured CIA/AAA threat model"),
    service: Optional[str] = Query(None, description="Filter by service", max_length=50),
    start_date: Optional[str] = Query(None, description="Start date filter", max_length=20),
    end_date: Optional[str] = Query(None, description="End date filter", max_length=20),
    user_id: str = Depends(get_user_id),
):
    """Enhanced question answering with security and knowledge graph."""
    try:
        # Validate query parameters
        try:
            validated_params = validate_query_params(
                service=service,
                start_date=start_date,
                end_date=end_date,
            )
            service = validated_params.get('service')
            start_date = validated_params.get('start_date')
            end_date = validated_params.get('end_date')
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        
        qa = get_qa_service(user_id)
        result = qa.answer(
            question=q,
            k=k,
            structured=structured,
            service=service,
            start_date=start_date,
            end_date=end_date,
        )

        if "error" in result:
            raise HTTPException(status_code=403, detail=result["message"])

        return result

    except HTTPException:
        raise
    except ValueError as ve:
        # Validation errors - return as-is (already sanitized)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # Log full error details server-side only
        logger.error(f"Error in ask endpoint: {e}", exc_info=True)
        # Don't expose internal error details to client
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while processing your request. Please try again later."
        )


@app.post("/api/v1/evaluate")
@limiter.limit("5/minute")  # Lower limit for expensive operations
async def evaluate_system(
    request: Request,
    user_id: str = Depends(get_user_id),
    _csrf: None = Depends(csrf_protect),  # CSRF protection
):
    """Run system evaluation on benchmark dataset."""
    try:
        cfg = get_config()
        if not cfg.evaluation.enable_continuous_evaluation:
            raise HTTPException(status_code=403, detail="Continuous evaluation not enabled")

        benchmark = BenchmarkDataset(cfg.evaluation.benchmark_dataset_path)
        pipeline = EvaluationPipeline(benchmark)

        # Create a threat model generator function
        def threat_model_generator(architecture: str) -> dict:
            qa = get_qa_service(user_id)
            result = qa.answer(f"Perform a CIA/AAA threat model for: {architecture}", structured=True)
            return result

        result = pipeline.evaluate_system(threat_model_generator)

        return {
            "run_id": result.run_id,
            "overall_score": result.overall_score,
            "metrics": result.metrics.dict(),
            "timestamp": result.timestamp.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in evaluation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred during evaluation. Please try again later."
        )


@app.get("/api/v1/reviews")
@limiter.limit("20/minute")
async def get_reviews(
    request: Request,
    threat_model_id: Optional[str] = Query(None, description="Filter by threat model ID", max_length=100),
    user_id: str = Depends(get_user_id),
):
    """Get expert reviews."""
    try:
        cfg = get_config()
        validation = ValidationInterface(cfg.evaluation.reviews_storage_path)

        if threat_model_id:
            reviews = validation.get_reviews_for_threat_model(threat_model_id)
        else:
            reviews = validation.get_pending_reviews()

        return {
            "reviews": [r.dict() for r in reviews],
            "summary": validation.get_feedback_summary(),
        }

    except Exception as e:
        logger.error(f"Error getting reviews: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while retrieving reviews. Please try again later."
        )


@app.get("/api/v1/audit")
@limiter.limit("10/minute")  # Stricter limit for sensitive audit logs
async def get_audit_logs(
    request: Request,
    user_id_filter: Optional[str] = Query(None, description="Filter by user ID", max_length=100),
    limit: int = Query(100, description="Maximum number of events", ge=1, le=1000),
    user_id: str = Depends(get_user_id),
):
    """Get audit logs (requires admin permission)."""
    try:
        cfg = get_config()
        if not cfg.security.access_control_enabled:
            raise HTTPException(status_code=403, detail="Access control not enabled")

        qa = get_qa_service(user_id)
        if not qa.access_control:
            raise HTTPException(status_code=403, detail="Access control not enabled")
        if not qa.access_control.has_permission(user_id, Permission.ADMIN):
            raise HTTPException(status_code=403, detail="Admin permission required")

        from chakravyuh.security.access_control.audit import AuditLogger
        audit = AuditLogger(log_dir=cfg.security.audit_log_dir)

        events = audit.get_events(user_id=user_id_filter, limit=limit)

        return {
            "events": events,
            "count": len(events),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audit logs: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while retrieving audit logs. Please try again later."
        )


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        cfg = get_config()
        
        # Add HTTPS enforcement middleware (only in production)
        # In development, this can be disabled
        import os
        if os.getenv("ENVIRONMENT", "development").lower() == "production":
            app.add_middleware(HTTPSRedirectMiddleware)
            # Add trusted host middleware for production
            allowed_hosts = os.getenv("ALLOWED_HOSTS", "*").split(",")
            app.add_middleware(
                TrustedHostMiddleware,
                allowed_hosts=allowed_hosts
            )
            logger.info("HTTPS enforcement enabled (production mode)")
        else:
            logger.info("HTTPS enforcement disabled (development mode)")
        
        logger.info("Chakravyuh Enhanced RAG API starting up...")
        logger.info(f"Knowledge Graph: {'enabled' if cfg.knowledge_graph.enabled else 'disabled'}")
        logger.info(f"Security: adversarial={cfg.security.adversarial_detection}, access_control={cfg.security.access_control_enabled}")
        logger.info(f"Evaluation: continuous={cfg.evaluation.enable_continuous_evaluation}")
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)
