-- Multiple documents per analysis session (text + vision summaries).
-- Run: psql -U <user> -d <db> -f backend/migrations/add_analysis_documents.sql
-- Ensures parent table exists (matches application schema).

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
);

CREATE TABLE IF NOT EXISTS analysis_documents (
    id BIGSERIAL PRIMARY KEY,
    analysis_session_id UUID NOT NULL REFERENCES analysis_sessions(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('erd_text', 'supporting_text', 'diagram_vision')),
    filename TEXT NOT NULL DEFAULT '',
    content_text TEXT NOT NULL DEFAULT '',
    sort_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analysis_documents_session
    ON analysis_documents (analysis_session_id, sort_order);

COMMENT ON TABLE analysis_documents IS 'Append-only chunks per session; legacy analysis_sessions columns are aggregates for compatibility.';
