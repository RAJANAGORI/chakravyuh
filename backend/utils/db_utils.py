# Hash storage for legacy doc_hashes; analysis_sessions stores ERD text + diagram analysis (no embeddings).
import os
import uuid
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import DictCursor


def _clean_text(value: Optional[str]) -> str:
    """Remove NUL bytes that PostgreSQL text columns cannot store."""
    if value is None:
        return ""
    return value.replace("\x00", "")


def get_conn():
    return psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"),
        port=os.getenv("PG_PORT", "5432"),
        dbname=os.getenv("PG_DB", "chakravyuh"),
        user=os.getenv("PG_USER", "chakravyuh"),
        password=os.getenv("PG_PASSWORD", "chakravyuh"),
    )


def get_hash(service, doc_name):
    with get_conn() as conn, conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(
            "SELECT sha256 FROM doc_hashes WHERE service=%s AND doc_name=%s",
            (service, doc_name),
        )
        row = cur.fetchone()
        return row["sha256"] if row else None


def upsert_hash(service, doc_name, sha256):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO doc_hashes (service, doc_name, sha256)
            VALUES (%s, %s, %s)
            ON CONFLICT (doc_name, service)
            DO UPDATE SET sha256=EXCLUDED.sha256, updated_at=NOW()
        """,
            (service, doc_name, sha256),
        )
        conn.commit()


def _ensure_analysis_sessions_table(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS analysis_sessions (
            id UUID PRIMARY KEY,
            erd_filename TEXT,
            erd_file_path TEXT,
            erd_text TEXT NOT NULL DEFAULT '',
            diagram_filename TEXT,
            diagram_file_path TEXT,
            architecture_diagram_summary TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    conn.commit()
    cur.close()


def _ensure_analysis_documents_table(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS analysis_documents (
            id BIGSERIAL PRIMARY KEY,
            analysis_session_id UUID NOT NULL REFERENCES analysis_sessions(id) ON DELETE CASCADE,
            kind TEXT NOT NULL,
            filename TEXT NOT NULL DEFAULT '',
            content_text TEXT NOT NULL DEFAULT '',
            sort_order INT NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT analysis_documents_kind_chk CHECK (
                kind IN ('erd_text', 'supporting_text', 'diagram_vision')
            )
        )
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_analysis_documents_session
        ON analysis_documents (analysis_session_id, sort_order)
        """
    )
    conn.commit()
    cur.close()


def refresh_session_aggregates_conn(conn, session_id: str) -> None:
    """Recompute analysis_sessions text fields from analysis_documents rows."""
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(
            """
            SELECT kind, filename, content_text
            FROM analysis_documents
            WHERE analysis_session_id = %s
            ORDER BY sort_order ASC, id ASC
            """,
            (session_id,),
        )
        rows = cur.fetchall()
    text_parts: List[str] = []
    diagram_parts: List[str] = []
    first_text_fn: Optional[str] = None
    last_diag_fn: Optional[str] = None
    for r in rows:
        k = r["kind"]
        fn = (r["filename"] or "document").strip() or "document"
        c = r["content_text"] or ""
        if k in ("erd_text", "supporting_text"):
            if first_text_fn is None:
                first_text_fn = fn
            text_parts.append(f"--- File: {fn} ({k}) ---\n{c}")
        elif k == "diagram_vision":
            last_diag_fn = fn
            diagram_parts.append(f"--- Diagram: {fn} ---\n{c}")
    erd_concat = "\n\n".join(text_parts)
    diag_concat = "\n\n".join(diagram_parts)
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE analysis_sessions
            SET erd_text = %s,
                erd_filename = %s,
                architecture_diagram_summary = %s,
                diagram_filename = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (
                erd_concat,
                first_text_fn or "",
                diag_concat,
                last_diag_fn or "",
                session_id,
            ),
        )


def append_analysis_document(
    session_id: str,
    kind: str,
    filename: str,
    content_text: str,
    diagram_file_path: Optional[str] = None,
) -> None:
    if kind not in ("erd_text", "supporting_text", "diagram_vision"):
        raise ValueError(f"Invalid document kind: {kind}")
    try:
        parsed = uuid.UUID(session_id.strip())
    except (ValueError, TypeError) as e:
        raise ValueError("Invalid analysis_id") from e
    sid = str(parsed)
    safe_filename = _clean_text(filename)
    safe_content = _clean_text(content_text)
    safe_diagram_path = _clean_text(diagram_file_path)
    with get_conn() as conn:
        _ensure_analysis_sessions_table(conn)
        _ensure_analysis_documents_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM analysis_sessions WHERE id = %s",
                (sid,),
            )
            if not cur.fetchone():
                raise ValueError("analysis_id not found")
            cur.execute(
                """
                SELECT COALESCE(MAX(sort_order), -1) + 1
                FROM analysis_documents
                WHERE analysis_session_id = %s
                """,
                (sid,),
            )
            next_ord = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO analysis_documents (
                    analysis_session_id, kind, filename, content_text, sort_order
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (sid, kind, safe_filename, safe_content, next_ord),
            )
            if kind == "diagram_vision" and diagram_file_path:
                cur.execute(
                    """
                    UPDATE analysis_sessions
                    SET diagram_file_path = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (safe_diagram_path, sid),
                )
        refresh_session_aggregates_conn(conn, sid)
        conn.commit()


def replace_session_text_documents(session_id: str, filename: str, content_text: str) -> None:
    """Single primary ERD path: remove all text docs, add one erd_text row."""
    try:
        parsed = uuid.UUID(session_id.strip())
    except (ValueError, TypeError) as e:
        raise ValueError("Invalid analysis_id") from e
    sid = str(parsed)
    safe_filename = _clean_text(filename)
    safe_content = _clean_text(content_text)
    with get_conn() as conn:
        _ensure_analysis_sessions_table(conn)
        _ensure_analysis_documents_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM analysis_documents
                WHERE analysis_session_id = %s
                  AND kind IN ('erd_text', 'supporting_text')
                """,
                (sid,),
            )
            cur.execute(
                """
                SELECT COALESCE(MAX(sort_order), -1) + 1
                FROM analysis_documents
                WHERE analysis_session_id = %s
                """,
                (sid,),
            )
            next_ord = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO analysis_documents (
                    analysis_session_id, kind, filename, content_text, sort_order
                )
                VALUES (%s, 'erd_text', %s, %s, %s)
                """,
                (sid, safe_filename, safe_content, next_ord),
            )
        refresh_session_aggregates_conn(conn, sid)
        conn.commit()


def replace_session_diagram_documents(
    session_id: str,
    diagram_filename: str,
    diagram_file_path: str,
    architecture_diagram_summary: str,
) -> None:
    """Single-diagram path: remove vision rows, add one diagram_vision row; set file path on session."""
    try:
        parsed = uuid.UUID(session_id.strip())
    except (ValueError, TypeError) as e:
        raise ValueError("Invalid analysis_id") from e
    sid = str(parsed)
    safe_diagram_filename = _clean_text(diagram_filename)
    safe_diagram_path = _clean_text(diagram_file_path)
    safe_summary = _clean_text(architecture_diagram_summary)
    with get_conn() as conn:
        _ensure_analysis_sessions_table(conn)
        _ensure_analysis_documents_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM analysis_documents
                WHERE analysis_session_id = %s AND kind = 'diagram_vision'
                """,
                (sid,),
            )
            cur.execute(
                """
                SELECT COALESCE(MAX(sort_order), -1) + 1
                FROM analysis_documents
                WHERE analysis_session_id = %s
                """,
                (sid,),
            )
            next_ord = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO analysis_documents (
                    analysis_session_id, kind, filename, content_text, sort_order
                )
                VALUES (%s, 'diagram_vision', %s, %s, %s)
                """,
                (sid, safe_diagram_filename, safe_summary, next_ord),
            )
            cur.execute(
                """
                UPDATE analysis_sessions
                SET diagram_file_path = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (safe_diagram_path, sid),
            )
        refresh_session_aggregates_conn(conn, sid)
        conn.commit()


def list_documents_for_analysis(analysis_id: str) -> List[Dict[str, Any]]:
    try:
        parsed = uuid.UUID(analysis_id.strip())
    except (ValueError, TypeError):
        return []
    sid = str(parsed)
    with get_conn() as conn:
        _ensure_analysis_documents_table(conn)
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT id, kind, filename, sort_order, created_at,
                       LENGTH(content_text) AS content_len
                FROM analysis_documents
                WHERE analysis_session_id = %s
                ORDER BY sort_order ASC, id ASC
                """,
                (sid,),
            )
            return [dict(r) for r in cur.fetchall()]


def get_analysis_context_bundle(analysis_id: str) -> Dict[str, Any]:
    """All chunks for Q&A: prefer analysis_documents; else legacy session columns."""
    try:
        parsed = uuid.UUID(analysis_id.strip())
    except (ValueError, TypeError):
        return {
            "analysis_id": None,
            "documents": [],
            "erd_text": "",
            "architecture_diagram_summary": "",
            "erd_filename": None,
            "diagram_filename": None,
            "updated_at": None,
        }
    sid = str(parsed)
    with get_conn() as conn:
        _ensure_analysis_sessions_table(conn)
        _ensure_analysis_documents_table(conn)
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT id, erd_filename, erd_file_path, erd_text,
                       diagram_filename, diagram_file_path, architecture_diagram_summary,
                       updated_at
                FROM analysis_sessions
                WHERE id = %s
                """,
                (sid,),
            )
            row = cur.fetchone()
            if not row:
                return {
                    "analysis_id": None,
                    "documents": [],
                    "erd_text": "",
                    "architecture_diagram_summary": "",
                    "erd_filename": None,
                    "diagram_filename": None,
                    "updated_at": None,
                }
            session = dict(row)
            cur.execute(
                """
                SELECT kind, filename, content_text, sort_order
                FROM analysis_documents
                WHERE analysis_session_id = %s
                ORDER BY sort_order ASC, id ASC
                """,
                (sid,),
            )
            table_docs = [dict(r) for r in cur.fetchall()]

    documents: List[Dict[str, Any]] = []
    if table_docs:
        documents = table_docs
    else:
        et = (session.get("erd_text") or "").strip()
        ds = (session.get("architecture_diagram_summary") or "").strip()
        if et:
            documents.append(
                {
                    "kind": "erd_text",
                    "filename": session.get("erd_filename") or "erd",
                    "content_text": session["erd_text"],
                    "sort_order": 0,
                }
            )
        if ds:
            documents.append(
                {
                    "kind": "diagram_vision",
                    "filename": session.get("diagram_filename") or "diagram",
                    "content_text": session["architecture_diagram_summary"],
                    "sort_order": 1,
                }
            )

    return {
        "analysis_id": sid,
        "documents": documents,
        "erd_text": session.get("erd_text") or "",
        "architecture_diagram_summary": session.get("architecture_diagram_summary")
        or "",
        "erd_filename": session.get("erd_filename"),
        "diagram_filename": session.get("diagram_filename"),
        "updated_at": session.get("updated_at"),
    }


def create_analysis_session() -> str:
    """Empty session for multi-file append flow (no legacy process-erd required first)."""
    new_id = uuid.uuid4()
    nid = str(new_id)
    with get_conn() as conn:
        _ensure_analysis_sessions_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO analysis_sessions (
                    id, erd_text, architecture_diagram_summary, updated_at
                )
                VALUES (%s, '', '', NOW())
                """,
                (nid,),
            )
        conn.commit()
    return nid


def get_analysis_context_by_id_or_latest(analysis_id: Optional[str]) -> Dict[str, Any]:
    if analysis_id and analysis_id.strip():
        bundle = get_analysis_context_bundle(analysis_id.strip())
        if bundle.get("analysis_id"):
            return bundle
    with get_conn() as conn:
        _ensure_analysis_sessions_table(conn)
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT id::text FROM analysis_sessions
                ORDER BY updated_at DESC NULLS LAST
                LIMIT 1
                """
            )
            r = cur.fetchone()
            if not r:
                return {
                    "analysis_id": None,
                    "documents": [],
                    "erd_text": "",
                    "architecture_diagram_summary": "",
                    "erd_filename": None,
                    "diagram_filename": None,
                    "updated_at": None,
                }
            return get_analysis_context_bundle(r["id"])


def upsert_analysis_erd(
    analysis_id: Optional[str],
    filename: str,
    file_path: str,
    erd_text: str,
) -> str:
    """Insert or update ERD fields. Returns analysis session id (UUID string)."""
    aid = analysis_id.strip() if analysis_id else None
    try:
        parsed = uuid.UUID(aid) if aid else None
    except (ValueError, TypeError):
        parsed = None

    safe_filename = _clean_text(filename)
    safe_file_path = _clean_text(file_path)
    safe_erd_text = _clean_text(erd_text)

    with get_conn() as conn:
        _ensure_analysis_sessions_table(conn)
        if parsed is None:
            new_id = uuid.uuid4()
            nid = str(new_id)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO analysis_sessions (
                        id, erd_filename, erd_file_path, erd_text, updated_at
                    )
                    VALUES (%s, %s, %s, %s, NOW())
                    """,
                    (nid, safe_filename, safe_file_path, safe_erd_text),
                )
            conn.commit()
            replace_session_text_documents(nid, safe_filename, safe_erd_text)
            return nid

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE analysis_sessions
                SET erd_filename=%s, erd_file_path=%s, erd_text=%s, updated_at=NOW()
                WHERE id=%s
                """,
                (safe_filename, safe_file_path, safe_erd_text, str(parsed)),
            )
            if cur.rowcount == 0:
                cur.execute(
                    """
                    INSERT INTO analysis_sessions (
                        id, erd_filename, erd_file_path, erd_text, updated_at
                    )
                    VALUES (%s, %s, %s, %s, NOW())
                    """,
                    (str(parsed), safe_filename, safe_file_path, safe_erd_text),
                )
        conn.commit()
        replace_session_text_documents(str(parsed), safe_filename, safe_erd_text)
        return str(parsed)


def update_analysis_diagram(
    analysis_id: str,
    diagram_filename: str,
    diagram_file_path: str,
    architecture_diagram_summary: str,
) -> None:
    try:
        parsed = uuid.UUID(analysis_id.strip())
    except (ValueError, TypeError) as e:
        raise ValueError("Invalid analysis_id") from e

    sid = str(parsed)
    with get_conn() as conn:
        _ensure_analysis_sessions_table(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM analysis_sessions WHERE id = %s", (sid,))
            if not cur.fetchone():
                raise ValueError("analysis_id not found; upload and process ERD PDF first")
    replace_session_diagram_documents(
        sid, diagram_filename, diagram_file_path, architecture_diagram_summary
    )


def get_latest_analysis_context() -> Dict[str, Any]:
    """Single latest analysis by updated_at. Used by Q&A."""
    with get_conn() as conn:
        _ensure_analysis_sessions_table(conn)
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT id, erd_filename, erd_file_path, erd_text,
                       diagram_filename, diagram_file_path, architecture_diagram_summary,
                       updated_at
                FROM analysis_sessions
                ORDER BY updated_at DESC NULLS LAST
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if not row:
                return {
                    "analysis_id": None,
                    "erd_text": "",
                    "architecture_diagram_summary": "",
                    "erd_filename": None,
                    "diagram_filename": None,
                    "updated_at": None,
                }
            d = dict(row)
            return {
                "analysis_id": str(d["id"]),
                "erd_text": d["erd_text"] or "",
                "architecture_diagram_summary": d["architecture_diagram_summary"] or "",
                "erd_filename": d["erd_filename"],
                "diagram_filename": d["diagram_filename"],
                "updated_at": d["updated_at"],
            }


def list_analysis_sessions(limit: int = 20) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        _ensure_analysis_sessions_table(conn)
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT id, erd_filename, diagram_filename, updated_at,
                       LENGTH(erd_text) AS erd_text_len,
                       LENGTH(architecture_diagram_summary) AS diagram_summary_len
                FROM analysis_sessions
                ORDER BY updated_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["id"] = str(d["id"])
                out.append(d)
            return out


# --- Legacy compatibility: old erd_documents table (optional migration) ---


def _ensure_erd_documents_table(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS erd_documents (
            id SERIAL PRIMARY KEY,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            content_text TEXT NOT NULL,
            uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (filename)
        )
        """
    )
    conn.commit()
    cur.close()


def upsert_erd_document(filename: str, file_path: str, content_text: str):
    """Deprecated: prefer upsert_analysis_erd. Kept for scripts/tests."""
    with get_conn() as conn:
        _ensure_erd_documents_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO erd_documents (filename, file_path, content_text, uploaded_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (filename)
                DO UPDATE SET file_path=EXCLUDED.file_path,
                              content_text=EXCLUDED.content_text,
                              uploaded_at=NOW()
                """,
                (filename, file_path, content_text),
            )
        conn.commit()


def get_erd_documents():
    """Prefer analysis_sessions; fall back to legacy erd_documents table."""
    with get_conn() as conn:
        _ensure_analysis_sessions_table(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM analysis_sessions")
            n = cur.fetchone()[0]
    if n > 0:
        ctx = get_latest_analysis_context()
        return [
            {
                "filename": ctx.get("erd_filename") or "analysis",
                "content_text": _combined_content(ctx),
                "uploaded_at": ctx.get("updated_at"),
            }
        ]
    with get_conn() as conn:
        _ensure_erd_documents_table(conn)
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT filename, content_text, uploaded_at
                FROM erd_documents
                ORDER BY uploaded_at DESC
                """
            )
            return [dict(row) for row in cur.fetchall()]


def _combined_content(ctx: Dict[str, Any]) -> str:
    parts = []
    et = ctx.get("erd_text") or ""
    if et.strip():
        parts.append("[ERD TEXT]\n" + et)
    ds = ctx.get("architecture_diagram_summary") or ""
    if ds.strip():
        parts.append("[ARCHITECTURE DIAGRAM ANALYSIS]\n" + ds)
    return "\n\n".join(parts) if parts else ""
