# Upload ERD PDF and architecture diagram → extract text (PyMuPDF + OCR fallback) and vision summary. No embeddings.
#
# Code attribution (for provenance / authorship proof):
# Raja Nagori <raja.nagori@owasp.org>

import json
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from services.diagram_vision import rasterize_pdf_first_page, summarize_diagram_image
from services.erd_extraction import extract_text_pdf_hybrid, truncate_text
from utils.audit import audit_event
from utils.auth import AuthContext, require_auth
from utils.config_loader import load_config
from qa.qa_chain import clear_analysis_cache
from utils.db_utils import (
    append_analysis_document,
    create_analysis_session,
    get_analysis_context_by_id_or_latest,
    get_analysis_context_bundle,
    get_erd_documents,
    get_latest_analysis_context,
    list_analysis_sessions,
    list_documents_for_analysis,
    update_analysis_diagram,
    upsert_analysis_erd,
)
from utils.rate_limit import enforce_rate_limit
from utils.upload_validation import (
    ensure_extension,
    sanitize_filename,
    sniff_binary_type,
    sniff_text_type,
)

router = APIRouter(dependencies=[Depends(require_auth)])
ENABLE_DEPRECATED_ENDPOINTS = (
    (os.getenv("ENABLE_DEPRECATED_ENDPOINTS") or "").strip().lower() in {"1", "true", "yes"}
)

ERD_DIR = Path("knowledge/erd")
DIAGRAM_DIR = Path("knowledge/diagrams")


def _cfg():
    return load_config("config.yaml")


def extract_text_from_pdf(file_path: str) -> tuple[str, str]:
    cfg = _cfg()
    return extract_text_pdf_hybrid(file_path, cfg)


def process_erd_document(file: UploadFile, filename: str, analysis_id: str | None) -> dict:
    # Backward-compatible wrapper; authenticated routes should use owner-aware path.
    return process_erd_document_with_owner(file, filename, analysis_id, "anonymous-dev")


def _validate_text_upload(content: bytes, filename: str) -> None:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        sniff_binary_type(content, "pdf")
    elif lower.endswith(".json"):
        sniff_text_type(content, "json")
    elif lower.endswith(".txt"):
        sniff_text_type(content, "txt")


def _validate_diagram_upload(content: bytes, filename: str) -> None:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        sniff_binary_type(content, "pdf")
    elif lower.endswith(".png"):
        sniff_binary_type(content, "png")
    elif lower.endswith(".jpg") or lower.endswith(".jpeg"):
        sniff_binary_type(content, "jpg")
    elif lower.endswith(".webp"):
        sniff_binary_type(content, "webp")


def process_erd_document_with_owner(
    file: UploadFile, filename: str, analysis_id: str | None, owner_subject: str
) -> dict:
    ERD_DIR.mkdir(parents=True, exist_ok=True)
    safe_filename = sanitize_filename(filename)
    file_path = ERD_DIR / safe_filename

    content = file.file.read()
    _validate_text_upload(content, safe_filename)
    file_path.write_bytes(content)

    lower = safe_filename.lower()
    if lower.endswith(".pdf"):
        try:
            text, method = extract_text_from_pdf(str(file_path))
            if not text.strip():
                text = f"PDF {safe_filename}: no text extracted."
        except Exception as e:
            text = f"PDF {safe_filename}: extraction error: {str(e)}"
            method = "error"
    elif lower.endswith(".json"):
        try:
            data = json.loads(content.decode("utf-8"))
            text = json.dumps(data, indent=2)
            method = "json"
        except Exception as e:
            text = f"JSON {safe_filename}: {str(e)}"
            method = "error"
    elif lower.endswith(".txt"):
        text = content.decode("utf-8", errors="replace")
        method = "txt"
    else:
        raise HTTPException(
            status_code=400,
            detail="ERD upload must be PDF, JSON, or TXT for text extraction.",
        )

    text = truncate_text(text)
    aid = upsert_analysis_erd(analysis_id, owner_subject, safe_filename, str(file_path), text)
    clear_analysis_cache()

    return {
        "status": "success",
        "message": f"ERD stored and text extracted ({method}). Upload architecture diagram next.",
        "filename": safe_filename,
        "saved_path": str(file_path),
        "analysis_id": aid,
        "extraction_method": method if lower.endswith(".pdf") else method,
    }


def _extract_text_from_saved_file(file_path: Path, filename: str) -> tuple[str, str]:
    lower = filename.lower()
    content = file_path.read_bytes()
    if lower.endswith(".pdf"):
        try:
            text, method = extract_text_from_pdf(str(file_path))
            if not text.strip():
                text = f"PDF {filename}: no text extracted."
        except Exception as e:
            text = f"PDF {filename}: extraction error: {str(e)}"
            method = "error"
        return truncate_text(text), method
    if lower.endswith(".json"):
        try:
            data = json.loads(content.decode("utf-8"))
            return truncate_text(json.dumps(data, indent=2)), "json"
        except Exception as e:
            return f"JSON {filename}: {str(e)}", "error"
    if lower.endswith(".txt"):
        return truncate_text(content.decode("utf-8", errors="replace")), "txt"
    raise HTTPException(
        status_code=400,
        detail="File must be PDF, JSON, or TXT for text extraction.",
    )


def _vision_summary_from_bytes(
    content: bytes, safe_name: str, cfg
) -> str:
    lower = safe_name.lower()
    if lower.endswith(".pdf"):
        path = DIAGRAM_DIR / f"_tmp_{uuid.uuid4().hex}_{safe_name}"
        try:
            path.write_bytes(content)
            img_bytes, mime = rasterize_pdf_first_page(str(path), cfg)
        finally:
            path.unlink(missing_ok=True)
    else:
        img_bytes = content
        mime = "image/jpeg"
        if lower.endswith(".png"):
            mime = "image/png"
        elif lower.endswith(".webp"):
            mime = "image/webp"
    summary = summarize_diagram_image(img_bytes, mime, cfg)
    if not summary.strip():
        summary = "[Vision model returned empty summary]"
    return summary


@router.post("/create-analysis-session")
async def api_create_analysis_session(request: Request, auth: AuthContext = Depends(require_auth)):
    try:
        enforce_rate_limit(f"{auth.subject}:create-session", max_requests=30, window_seconds=60)
        aid = create_analysis_session(auth.subject)
        clear_analysis_cache()
        audit_event(request, "analysis_session_created", auth.subject, analysis_id=aid)
        return JSONResponse(
            content={
                "status": "success",
                "analysis_id": aid,
                "message": "Empty analysis session created. Append PDFs and diagrams.",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.options("/append-text-document", include_in_schema=False)
async def append_text_document_options():
    return {"status": "ok"}


@router.post("/append-text-document")
async def append_text_document(
    request: Request,
    file: UploadFile = File(...),
    filename: str = Form(...),
    analysis_id: str = Form(...),
    doc_role: str = Form(default="supporting"),
    auth: AuthContext = Depends(require_auth),
):
    enforce_rate_limit(f"{auth.subject}:append-text", max_requests=30, window_seconds=60)
    if not analysis_id.strip():
        raise HTTPException(status_code=400, detail="analysis_id is required.")
    kind = "supporting_text" if doc_role.strip().lower() != "erd_text" else "erd_text"
    allowed = [".pdf", ".json", ".txt"]
    safe_name = sanitize_filename(filename)
    ensure_extension(safe_name, allowed)
    if file.size and file.size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 50MB).")
    ERD_DIR.mkdir(parents=True, exist_ok=True)
    path = ERD_DIR / safe_name
    content = file.file.read()
    _validate_text_upload(content, safe_name)
    path.write_bytes(content)
    try:
        text, method = _extract_text_from_saved_file(path, safe_name)
        append_analysis_document(analysis_id.strip(), auth.subject, kind, safe_name, text)
        audit_event(
            request,
            "text_document_appended",
            auth.subject,
            analysis_id=analysis_id.strip(),
            filename=safe_name,
            kind=kind,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except PermissionError as e:
        audit_event(
            request,
            "analysis_access_denied",
            auth.subject,
            analysis_id=analysis_id.strip(),
            reason=str(e),
        )
        raise HTTPException(status_code=403, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        clear_analysis_cache()
    return JSONResponse(
        content={
            "status": "success",
            "message": f"Text document appended ({method}).",
            "filename": safe_name,
            "analysis_id": analysis_id.strip(),
            "kind": kind,
        }
    )


@router.options("/append-architecture-diagram", include_in_schema=False)
async def append_arch_diagram_options():
    return {"status": "ok"}


@router.post("/append-architecture-diagram")
async def append_architecture_diagram(
    request: Request,
    file: UploadFile = File(...),
    filename: str = Form(...),
    analysis_id: str = Form(...),
    auth: AuthContext = Depends(require_auth),
):
    enforce_rate_limit(f"{auth.subject}:append-diagram", max_requests=20, window_seconds=60)
    if not analysis_id.strip():
        raise HTTPException(status_code=400, detail="analysis_id is required.")
    allowed = [".png", ".jpg", ".jpeg", ".pdf", ".webp"]
    safe_name = sanitize_filename(filename)
    ensure_extension(safe_name, allowed)
    if file.size and file.size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 50MB).")
    DIAGRAM_DIR.mkdir(parents=True, exist_ok=True)
    path = DIAGRAM_DIR / safe_name
    content = file.file.read()
    _validate_diagram_upload(content, safe_name)
    path.write_bytes(content)
    cfg = _cfg()
    try:
        summary = _vision_summary_from_bytes(content, safe_name, cfg)
        append_analysis_document(
            analysis_id.strip(),
            auth.subject,
            "diagram_vision",
            safe_name,
            summary,
            diagram_file_path=str(path),
        )
        audit_event(
            request,
            "diagram_appended",
            auth.subject,
            analysis_id=analysis_id.strip(),
            filename=safe_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except PermissionError as e:
        audit_event(
            request,
            "analysis_access_denied",
            auth.subject,
            analysis_id=analysis_id.strip(),
            reason=str(e),
        )
        raise HTTPException(status_code=403, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Architecture diagram analysis failed: {str(e)}",
        ) from e
    finally:
        clear_analysis_cache()
    return JSONResponse(
        content={
            "status": "success",
            "message": "Architecture diagram appended.",
            "filename": safe_name,
            "saved_path": str(path),
            "analysis_id": analysis_id.strip(),
        }
    )


@router.get("/session-documents", include_in_schema=False)
async def session_documents(
    analysis_id: str = Query(..., description="Analysis session UUID"),
    auth: AuthContext = Depends(require_auth),
):
    try:
        uuid.UUID(analysis_id.strip())
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid analysis_id")
    rows = list_documents_for_analysis(analysis_id.strip())
    # Ownership check via context bundle to avoid exposing rows from another tenant.
    try:
        _ = get_analysis_context_bundle(analysis_id.strip(), owner_subject=auth.subject)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    return JSONResponse(
        content=jsonable_encoder(
            {
                "status": "success",
                "analysis_id": analysis_id.strip(),
                "documents": rows,
            }
        )
    )


@router.options("/save-original-erd", include_in_schema=False)
async def save_original_erd_options():
    return {"status": "ok"}


@router.post("/save-original-erd")
async def save_original_erd(request: Request, auth: AuthContext = Depends(require_auth)):
    enforce_rate_limit(f"{auth.subject}:save-erd", max_requests=20, window_seconds=60)
    filename = request.headers.get("X-Filename")
    if not filename:
        raise HTTPException(status_code=400, detail="Filename header is required")
    safe_name = sanitize_filename(filename)
    ensure_extension(safe_name, [".pdf", ".json", ".txt"])
    ERD_DIR.mkdir(parents=True, exist_ok=True)
    content = await request.body()
    _validate_text_upload(content, safe_name)
    file_path = ERD_DIR / safe_name
    file_path.write_bytes(content)
    audit_event(request, "original_erd_saved", auth.subject, filename=safe_name)
    return JSONResponse(
        content={
            "status": "success",
            "message": f"Saved to {ERD_DIR}/{safe_name}",
            "filename": safe_name,
            "saved_path": str(file_path),
        }
    )


@router.options("/process-erd", include_in_schema=False)
async def process_erd_options():
    return {"status": "ok"}


@router.post("/process-erd")
async def process_erd(
    request: Request,
    file: UploadFile = File(...),
    filename: str = Form(...),
    analysis_id: str = Form(default=""),
    doc_type: str = Form(default="erd"),
    auth: AuthContext = Depends(require_auth),
):
    enforce_rate_limit(f"{auth.subject}:process-erd", max_requests=20, window_seconds=60)
    allowed = [".pdf", ".json", ".txt"]
    safe_name = sanitize_filename(filename)
    ensure_extension(safe_name, allowed)
    if file.size and file.size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 50MB).")
    try:
        aid = analysis_id.strip() or None
        result = process_erd_document_with_owner(file, safe_name, aid, auth.subject)
        audit_event(
            request,
            "erd_processed",
            auth.subject,
            analysis_id=result.get("analysis_id"),
            filename=safe_name,
            doc_type=doc_type,
        )
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}") from e


@router.options("/process-architecture-diagram", include_in_schema=False)
async def process_diagram_options():
    return {"status": "ok"}


@router.post("/process-architecture-diagram")
async def process_architecture_diagram(
    request: Request,
    file: UploadFile = File(...),
    filename: str = Form(...),
    analysis_id: str = Form(...),
    auth: AuthContext = Depends(require_auth),
):
    enforce_rate_limit(f"{auth.subject}:process-diagram", max_requests=20, window_seconds=60)
    if not analysis_id.strip():
        raise HTTPException(status_code=400, detail="analysis_id is required (process ERD PDF first).")
    allowed = [".png", ".jpg", ".jpeg", ".pdf", ".webp"]
    safe_name = sanitize_filename(filename)
    ensure_extension(safe_name, allowed)
    if file.size and file.size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 50MB).")

    DIAGRAM_DIR.mkdir(parents=True, exist_ok=True)
    path = DIAGRAM_DIR / safe_name
    content = file.file.read()
    _validate_diagram_upload(content, safe_name)
    path.write_bytes(content)

    cfg = _cfg()
    try:
        summary = _vision_summary_from_bytes(content, safe_name, cfg)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Architecture diagram analysis failed: {str(e)}",
        ) from e

    try:
        update_analysis_diagram(analysis_id.strip(), auth.subject, safe_name, str(path), summary)
        audit_event(
            request,
            "diagram_processed",
            auth.subject,
            analysis_id=analysis_id.strip(),
            filename=safe_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e

    clear_analysis_cache()

    return JSONResponse(
        content={
            "status": "success",
            "message": "Architecture diagram analyzed and stored.",
            "filename": safe_name,
            "saved_path": str(path),
            "analysis_id": analysis_id.strip(),
        }
    )


@router.get("/erd-status", include_in_schema=False)
async def get_erd_status():
    try:
        docs = get_erd_documents()
        erd_documents = [
            {"filename": d["filename"], "uploaded_at": d["uploaded_at"]} for d in docs
        ]
        ctx = get_latest_analysis_context()
        return JSONResponse(
            content=jsonable_encoder(
                {
                    "status": "success",
                    "erd_documents": erd_documents,
                    "total": len(erd_documents),
                    "latest_analysis_id": ctx.get("analysis_id"),
                    "has_diagram_summary": bool(
                        (ctx.get("architecture_diagram_summary") or "").strip()
                    ),
                }
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/analysis-status")
async def analysis_status(
    analysis_id: str | None = Query(
        default=None,
        description="If set, readiness for this session; else latest session.",
    ),
    auth: AuthContext = Depends(require_auth),
):
    """Analysis session readiness for chat (text + at least one diagram summary)."""
    try:
        if analysis_id and analysis_id.strip():
            ctx = get_analysis_context_bundle(analysis_id.strip(), owner_subject=auth.subject)
        else:
            ctx = get_analysis_context_by_id_or_latest(
                None, owner_subject=auth.subject, allow_latest_fallback=True
            )
        sessions = list_analysis_sessions(5, owner_subject=auth.subject)
        docs = ctx.get("documents") or []
        if docs:
            has_text = any(
                d.get("kind") in ("erd_text", "supporting_text")
                and (d.get("content_text") or "").strip()
                for d in docs
            )
            has_diagram = any(
                d.get("kind") == "diagram_vision"
                and (d.get("content_text") or "").strip()
                for d in docs
            )
        else:
            has_text = bool((ctx.get("erd_text") or "").strip())
            has_diagram = bool((ctx.get("architecture_diagram_summary") or "").strip())
        ready = bool(has_text and has_diagram)
        return JSONResponse(
            content=jsonable_encoder(
                {
                    "status": "success",
                    "ready_for_chat": ready,
                    "latest": ctx,
                    "recent_sessions": sessions,
                }
            )
        )
    except Exception as e:
        return JSONResponse(
            content=jsonable_encoder({"status": "error", "message": str(e)}),
            status_code=500,
        )


@router.options("/bulk-insert-erd", include_in_schema=False)
async def bulk_insert_erd_options():
    return {"status": "ok"}


@router.post("/bulk-insert-erd", include_in_schema=False)
async def bulk_insert_erd():
    if not ENABLE_DEPRECATED_ENDPOINTS:
        raise HTTPException(status_code=404, detail="Not found")
    return JSONResponse(
        content={
            "status": "success",
            "message": "Bulk embedding removed. Use ERD PDF + architecture diagram uploads.",
        }
    )


@router.options("/bulk-insert-erd-status", include_in_schema=False)
async def bulk_insert_status_options():
    return {"status": "ok"}


@router.get("/bulk-insert-erd-status", include_in_schema=False)
async def get_bulk_insert_status():
    if not ENABLE_DEPRECATED_ENDPOINTS:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        ctx = get_latest_analysis_context()
        n = len(list_analysis_sessions(100))
        return JSONResponse(
            content={
                "status": "success",
                "erd_files_count": n,
                "erd_chunks_in_db": n,
                "message": f"Analysis sessions: {n}. Latest has ERD + diagram: "
                f"{bool((ctx.get('erd_text') or '').strip() and (ctx.get('architecture_diagram_summary') or '').strip())}.",
            }
        )
    except Exception as e:
        return JSONResponse(
            content={
                "status": "error",
                "message": str(e),
                "erd_files_count": 0,
                "erd_chunks_in_db": 0,
            }
        )
