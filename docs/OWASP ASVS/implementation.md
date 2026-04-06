# OWASP ASVS 5.0.0 -- Chakravyuh Implementation Mapping

**Document Version:** 1.0
**Last Updated:** 2026-04-06
**Framework:** OWASP Application Security Verification Standard 5.0.0 (May 2025)

This document maps OWASP ASVS 5.0.0 requirements to concrete implementations within the Chakravyuh project (AI-assisted threat modeling platform), with exact file paths, line numbers, and descriptions.

> **Note:** Chakravyuh is a threat modeling tool with **no user authentication system** (no login, passwords, sessions, or RBAC). The application uses `analysis_id` (UUID) as an opaque session handle. This means entire ASVS chapters on authentication (V6), session management (V7), and OAuth (V10) are largely **not applicable** in the current architecture. The mapping focuses on controls that **are** implemented.

---

## V1: Encoding and Sanitization

| ASVS # | Requirement | Lvl | File | Lines | What Was Done |
|--------|------------|-----|------|-------|---------------|
| 1.2.4 | Parameterized queries prevent SQL injection | L1 | `backend/utils/db_utils.py` | 28-32 | All PostgreSQL queries use psycopg2 parameterized placeholders (`%s`). Example: `cur.execute("SELECT sha256 FROM doc_hashes WHERE service=%s AND doc_name=%s", (service, doc_name))` (lines 28-32). No string concatenation or f-strings used in SQL across the entire `db_utils.py` file. |
| 1.2.4 | Parameterized queries prevent SQL injection | L1 | `backend/utils/db_utils.py` | 46-52, 63-70, 91-100 | Insert operations also parameterized: `INSERT INTO doc_hashes ... VALUES (%s, %s, %s, %s)` (lines 46-52). Analysis session creation (lines 63-70) and document registration (lines 91-100) all use `%s` placeholders with tuple parameters. |
| 1.3.3 | Sanitization before dangerous context | L2 | `backend/utils/db_utils.py` | 10-14 | `_clean_text(value)` strips NUL bytes (`\x00`) that PostgreSQL text columns cannot store: `return value.replace("\x00", "")` (lines 10-14). Applied before all text insertions to prevent data corruption and potential injection via null bytes. |
| 1.5.1 | XML parser configured to prevent XXE | L1 | `backend/utils/config_loader.py` | 13-14 | YAML parsing uses `yaml.safe_load(f)` (line 14) instead of `yaml.load()`, preventing arbitrary object deserialization and code execution via malicious YAML payloads. |

---

## V2: Validation and Business Logic

| ASVS # | Requirement | Lvl | File | Lines | What Was Done |
|--------|------------|-----|------|-------|---------------|
| 2.2.1 | Input validated against expected structure | L1 | `backend/api/search_api.py` | 22-26 | Pydantic `AskRequest` model validates `/ask` POST body: `q: str = Field(..., min_length=1)` enforces non-empty questions, `k: int = Field(default=3, ge=1, le=12)` restricts result count to 1-12 range (lines 22-26). FastAPI automatically rejects malformed requests with 422. |
| 2.2.1 | Input validated against expected structure | L1 | `backend/api/erd_processor.py` | 267-270 | `analysis_id` validated as proper UUID format using `uuid.UUID(analysis_id.strip())` (lines 267-270). Invalid UUIDs raise `HTTPException(status_code=400, detail="Invalid analysis_id")`. Applied across multiple endpoints. |
| 2.2.2 | Server-side validation, not client-side only | L1 | `backend/api/erd_processor.py` | 319-326 | File upload validation is performed server-side in FastAPI, not just in the React frontend. Extension allowlist (`[".pdf", ".json", ".txt"]`, line 319) and 50MB size limit (line 325) enforced at the API layer regardless of client behavior. |

---

## V3: Web Frontend Security

| ASVS # | Requirement | Lvl | File | Lines | What Was Done |
|--------|------------|-----|------|-------|---------------|
| 3.4.2 | CORS Access-Control-Allow-Origin validated against allowlist | L1 | `backend/api/search_api.py` | 51-69 | CORS configured with environment-driven allowlist: `CORS_ALLOW_ORIGINS` env var parsed into list (lines 51-53). Defaults to localhost origins (lines 54-59). `allow_origin_regex` restricts LAN access to private IP ranges on port 3000 (line 66). Applied via FastAPI `CORSMiddleware` (lines 61-69). |

---

## V4: API and Web Service

| ASVS # | Requirement | Lvl | File | Lines | What Was Done |
|--------|------------|-----|------|-------|---------------|
| 4.1.1 | Content-Type header matches response content | L1 | `backend/api/search_api.py` | Full file | FastAPI automatically sets `Content-Type: application/json` for all JSON responses. `StreamingResponse` endpoints set explicit `media_type="text/event-stream"` for SSE streams. Framework-level enforcement ensures correct content types. |

---

## V5: File Handling

| ASVS # | Requirement | Lvl | File | Lines | What Was Done |
|--------|------------|-----|------|-------|---------------|
| 5.2.1 | File size limits enforced | L1 | `backend/api/erd_processor.py` | 325-326 | Server-side file size validation: `if file.size and file.size > 50 * 1024 * 1024: raise HTTPException(status_code=400, detail="File too large (max 50MB).")` (lines 325-326). Applied to ERD upload endpoint. |
| 5.2.1 | File size limits enforced | L1 | `backend/api/erd_processor.py` | 355-357 | Diagram uploads also size-limited to 50MB with same pattern at lines 355-357. |
| 5.2.2 | File extension validation | L1 | `backend/api/erd_processor.py` | 319-324 | ERD uploads restricted to allowlist: `allowed = [".pdf", ".json", ".txt"]` (line 319). Extension checked via `if not any(filename.lower().endswith(ext) for ext in allowed)` (line 320). Rejects with 400 and lists allowed types (lines 321-324). |
| 5.2.2 | File extension validation | L1 | `backend/api/erd_processor.py` | 350-354 | Diagram uploads have separate allowlist: `[".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg"]`. Same pattern of lowercase comparison and 400 rejection for disallowed types. |
| 5.2.6 | Image pixel size limits to prevent pixel flood | L3 | `backend/services/diagram_vision.py` | 33-37 | Pillow `MAX_IMAGE_PIXELS` cap set to 250 million pixels (line 36): `Image.MAX_IMAGE_PIXELS = max(Image.MAX_IMAGE_PIXELS, cap)`. Prevents decompression bomb attacks while allowing legitimate large architecture diagrams. Images are immediately downscaled after loading. |
| 5.3.2 | Path traversal protection | L1 | `backend/api/erd_processor.py` | 182-184 | `os.path.basename(filename)` used to strip directory components: `safe_name = os.path.basename(filename)` then `path = ERD_DIR / safe_name` (lines 182-184). Prevents `../../etc/passwd` style path traversal on file append operations. |

---

## V11: Cryptography

| ASVS # | Requirement | Lvl | File | Lines | What Was Done |
|--------|------------|-----|------|-------|---------------|
| 11.4.1 | Approved hash functions (no MD5 for crypto) | L1 | `backend/utils/db_utils.py` | SHA256 usage | Document hashing uses SHA256 (via `doc_hashes` table column named `sha256`) for content deduplication -- not MD5 or SHA1. |

---

## V12: Secure Communication

| ASVS # | Requirement | Lvl | File | Lines | What Was Done |
|--------|------------|-----|------|-------|---------------|
| 12.2.1 | TLS for external service connectivity | L1 | `backend/utils/llm_provider.py` | 30-36, 76-85 | OAuth token endpoint called via `requests.post(token_url, ...)` over HTTPS (line 36). Azure OpenAI and OpenAI SDK clients communicate over HTTPS by default. All LLM provider connections use TLS. |

---

## V13: Configuration

| ASVS # | Requirement | Lvl | File | Lines | What Was Done |
|--------|------------|-----|------|-------|---------------|
| 13.3.1 | Secrets not in source code | L2 | `backend/utils/llm_provider.py` | 12-41 | API credentials loaded from environment variables first, config file second: `os.environ.get("TM_API_CLIENT_ID")` (line 15), `os.environ.get("TM_API_CLIENT_SECRET")` (line 17), `os.environ.get("OPENAI_API_KEY")` (line 78). Env vars always override file-based config. |
| 13.3.1 | Secrets not in source code | L2 | `.gitignore` | 137-223 | `.env`, `backend/.env`, `backend/config.yaml`, `docker-prod/config.yaml` all excluded from version control (lines 137-223). Config example files (`config.example.yaml`, `.env.example`) contain placeholder values only. |
| 13.4.1 | No source control metadata exposed | L1 | `.gitignore` | Full file | `.env` files, config files with secrets, knowledge directories, and build artifacts all excluded from the repository. |

---

## V15: Secure Coding and Architecture

| ASVS # | Requirement | Lvl | File | Lines | What Was Done |
|--------|------------|-----|------|-------|---------------|
| 15.2.5 | Containerization for isolation | L3 | `docker-prod/docker-compose.yml` | 46-52 | Docker containers hardened: `cap_drop: [ALL]` drops all Linux capabilities (lines 49-50), `security_opt: [no-new-privileges:true]` prevents privilege escalation (lines 51-52), `tmpfs` mounts for temp directories (lines 46-48). |
| 15.2.5 | Containerization for isolation | L3 | `docker-prod/backend.Dockerfile` | 17-23 | Backend container runs as non-root user: `addgroup --system app && adduser --system --ingroup app app` (line 17), `USER app` (line 23). Prevents container breakout from running with root privileges. |
| 15.2.5 | Containerization for isolation | L3 | `docker-prod/frontend.Dockerfile` | 12-25 | Frontend container also runs as non-root with same pattern. `read_only: true` in docker-compose prevents filesystem writes from the frontend container. |
| 15.3.1 | Return only required data fields | L1 | `backend/services/erd_extraction.py` | 77-80 | `truncate_text(text, max_chars=500_000)` limits stored text to 500K characters (lines 77-80), preventing unbounded data storage and potential memory/processing abuse from extremely large documents. |

---

## V16: Security Logging and Error Handling

| ASVS # | Requirement | Lvl | File | Lines | What Was Done |
|--------|------------|-----|------|-------|---------------|
| 16.5.2 | Application continues operating when external resources fail | L2 | `backend/utils/llm_provider.py` | 30-36 | OAuth token acquisition uses `timeout=60` (line 36) preventing indefinite hangs when the token endpoint is unreachable. LLM provider initialization raises clear `ValueError` with actionable messages when configuration is missing. |

---

## Areas Not Currently Covered (Gaps)

| ASVS Chapter | Status | Notes |
|---|---|---|
| V6 - Authentication | **Not applicable** | No user authentication system. Access is by `analysis_id` knowledge. |
| V7 - Session Management | **Not applicable** | No user sessions. `analysis_id` is an opaque UUID handle. |
| V8 - Authorization | **Gap** | No RBAC/ABAC. Anyone with a valid `analysis_id` can access that session's data. |
| V9 - Self-contained Tokens | **Not applicable** | No JWT or self-contained tokens for user auth. |
| V10 - OAuth and OIDC | **Not applicable** | OAuth used only outbound for LLM API access, not for user authentication. |
| V3.4 - Security Headers | **Gap** | No CSP, HSTS, X-Content-Type-Options, or X-Frame-Options configured. |
| V3.5 - CSRF Protection | **Gap** | No CSRF tokens (mitigated partially by no cookie-based auth). |
| V2.4 - Rate Limiting | **Gap** | No rate limiting on any endpoint. |
| V16.2 - Structured Logging | **Gap** | Logging is `print()` based, not structured audit logging. |
| V13.4 - Information Leakage | **Gap** | `/debug` endpoint exposes request headers and client IP. `/metrics` is unauthenticated. Error responses include `str(e)` internal details. |
| V5.3.2 - Path Traversal | **Partial gap** | `os.path.basename` used in append flows but `process_erd_document` and `/save-original-erd` write filenames without basename sanitization. |

---

## Summary

| ASVS Chapter | Implemented Count | Key Implementation Highlights |
|---|---|---|
| V1 - Encoding & Sanitization | 4 | Parameterized SQL (psycopg2 `%s`), NUL byte stripping, YAML safe_load |
| V2 - Validation & Business Logic | 3 | Pydantic models, UUID validation, server-side file validation |
| V3 - Web Frontend Security | 1 | CORS env-driven allowlist with LAN regex |
| V4 - API and Web Service | 1 | Framework-enforced Content-Type headers |
| V5 - File Handling | 6 | Size limits (50MB), extension allowlists, pixel flood protection, partial path traversal prevention |
| V11 - Cryptography | 1 | SHA256 for document hashing |
| V12 - Secure Communication | 1 | TLS for all LLM provider connections |
| V13 - Configuration | 3 | Env-based secrets, .gitignore exclusions, config example files |
| V15 - Secure Coding | 4 | Docker hardening (cap_drop ALL, no-new-privileges, non-root), text truncation |
| V16 - Error Handling | 1 | Timeout on external service calls |
| **Total** | **~25 requirements covered** | Strongest in file handling validation and container hardening |
