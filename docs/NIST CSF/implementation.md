# NIST Cybersecurity Framework (CSF) 2.0 -- Chakravyuh Implementation Mapping

**Document Version:** 1.0
**Last Updated:** 2026-04-06
**Framework:** NIST CSF 2.0 (February 26, 2024)

This document maps NIST CSF 2.0 subcategories to concrete implementations within the Chakravyuh project (AI-assisted threat modeling platform), with exact file paths, line numbers, and descriptions.

> **Note:** Chakravyuh is an internal/team-facing threat modeling tool without user authentication. Many NIST CSF subcategories around identity management and access control have limited applicability. The mapping focuses on controls that **are** implemented.

---

## GOVERN (GV)

### GV.PO -- Policy

| CSF ID | Subcategory | File | Lines | What Was Done |
|--------|------------|------|-------|---------------|
| GV.PO-01 | Policy for managing cybersecurity risks is established based on organizational context | `backend/SECURITY.md` | Full file | Security policy documented with responsible disclosure process and contact information for reporting vulnerabilities. Establishes the project's security communication expectations. |

### GV.SC -- Cybersecurity Supply Chain Risk Management

| CSF ID | Subcategory | File | Lines | What Was Done |
|--------|------------|------|-------|---------------|
| GV.SC-04 | Suppliers are known and prioritized by criticality | `.security_scan_tools/SECURITY_SCAN_REPORT.md` | Full file | npm and pip dependency audits performed and documented. Third-party libraries scanned for known vulnerabilities. Heuristic secret-pattern detection run across the codebase to prevent credential leakage. |

---

## IDENTIFY (ID)

### ID.AM -- Asset Management

| CSF ID | Subcategory | File | Lines | What Was Done |
|--------|------------|------|-------|---------------|
| ID.AM-02 | Inventories of software, services, and systems managed by the organization are maintained | `docs/HLD.md` | Full file | High-Level Design document inventories all system components: Next.js 15 frontend, FastAPI backend, PostgreSQL database, Azure OpenAI / OpenAI LLM providers, Docker deployment stack. Architecture documented with component relationships. |
| ID.AM-02 | Software inventory maintained | `backend/requirements.txt`, `frontend/package.json` | Full files | All Python and Node.js dependencies tracked with pinned versions. `requirements.txt` lists all backend libraries (FastAPI, psycopg2, langchain, Pillow, etc.). `package.json` lists all frontend libraries. |
| ID.AM-03 | Network communication and data flows documented | `docs/DFD.md` | Full file | Data Flow Diagram documents all communication paths: Browser → Next.js → FastAPI → PostgreSQL, FastAPI → LLM providers (Azure/OpenAI), file storage flows for ERDs and diagrams. Trust boundaries identified between components. |
| ID.AM-03 | Network communication documented | `docs/LLD.md` | Full file | Low-Level Design document details internal component communication, API endpoint specifications, database schema, and service interactions. |

### ID.RA -- Risk Assessment

| CSF ID | Subcategory | File | Lines | What Was Done |
|--------|------------|------|-------|---------------|
| ID.RA-01 | Vulnerabilities in assets are identified, validated, and recorded | `.security_scan_tools/SECURITY_SCAN_REPORT.md` | Full file | Automated vulnerability scanning results documented: npm audit findings, pip dependency vulnerability checks, and heuristic secret-detection scan results. Provides a recorded baseline of known vulnerabilities. |

---

## PROTECT (PR)

### PR.AA -- Identity Management, Authentication, and Access Control

| CSF ID | Subcategory | File | Lines | What Was Done |
|--------|------------|------|-------|---------------|
| PR.AA-01 | Identities and credentials for authorized services are managed | `backend/utils/llm_provider.py` | 12-41 | LLM service credentials managed via environment variables with config fallback: `TM_API_CLIENT_ID`, `TM_API_CLIENT_SECRET`, `TM_TOKEN_URL` (lines 15-19). OAuth client credentials flow authenticates the backend to LLM providers using Base64-encoded Basic auth (line 26). Env vars always override file-based config to prevent accidental credential exposure. |
| PR.AA-03 | Services are authenticated | `backend/utils/llm_provider.py` | 24-36 | Backend authenticates to Azure LLM gateway via OAuth client credentials: `grant_type=client_credentials` (line 24), Base64 `Authorization: Basic` header (lines 25-28), token retrieved over HTTPS with 60-second timeout (line 36). Token is then used as Bearer auth for subsequent LLM API calls. |

### PR.DS -- Data Security

| CSF ID | Subcategory | File | Lines | What Was Done |
|--------|------------|------|-------|---------------|
| PR.DS-01 | Confidentiality, integrity, and availability of data-at-rest are protected | `backend/utils/db_utils.py` | 10-14 | `_clean_text(value)` sanitizes data before storage by removing NUL bytes (`\x00`, lines 10-14) that could corrupt PostgreSQL text columns or cause unexpected behavior in downstream processing. Applied before all text insertions. |
| PR.DS-01 | Data-at-rest integrity | `backend/utils/db_utils.py` | 28-32, 46-52 | Document content integrity tracked via SHA256 hashes stored in `doc_hashes` table. Before processing, documents are checked against stored hashes to detect changes: `SELECT sha256 FROM doc_hashes WHERE service=%s AND doc_name=%s` (lines 28-32). New hashes stored on insert (lines 46-52). |
| PR.DS-02 | Confidentiality, integrity, and availability of data-in-transit are protected | `backend/utils/llm_provider.py` | 30-36, 76-85 | All external API communication uses HTTPS: OAuth token endpoint called via `requests.post` to HTTPS URLs (line 36). Azure OpenAI SDK and OpenAI SDK both default to TLS-encrypted connections. No plaintext HTTP used for sensitive API calls. |
| PR.DS-02 | Data-in-transit protection | `backend/api/search_api.py` | 51-69 | CORS middleware configured with explicit origin allowlist (lines 51-69) preventing unauthorized cross-origin access to API data. `allow_credentials=True` (line 65) combined with origin restrictions ensures cookies/auth headers are only accepted from trusted origins. |

### PR.PS -- Platform Security

| CSF ID | Subcategory | File | Lines | What Was Done |
|--------|------------|------|-------|---------------|
| PR.PS-01 | Configuration management practices are established | `backend/config.example.yaml`, `backend/.env.example` | Full files | Configuration templates provided with placeholder values. Actual config files excluded from version control via `.gitignore`. Secrets management follows env-first pattern documented in README.md. |
| PR.PS-01 | Configuration management | `.gitignore` | 137-223 | Sensitive files systematically excluded: `.env`, `backend/.env`, `backend/config.yaml`, `docker-prod/config.yaml`, knowledge directories containing uploaded documents. Prevents accidental secret commits. |
| PR.PS-06 | Secure software development practices integrated | `backend/utils/db_utils.py` | 28-32, 46-52, 63-70, 91-100 | All database operations use parameterized queries with psycopg2 `%s` placeholders. No string interpolation, f-strings, or concatenation used in any SQL statement across the entire data access layer. Prevents SQL injection at the pattern level. |
| PR.PS-06 | Secure development practices | `backend/api/search_api.py` | 22-26 | Pydantic models enforce API contract validation: `AskRequest` with `min_length=1` for questions, `ge=1, le=12` bounds for result count. FastAPI auto-rejects malformed requests with 422 before handler code executes. |
| PR.PS-06 | Secure development practices | `backend/api/erd_processor.py` | 267-270, 319-326 | UUID format validation (`uuid.UUID()` parse attempt, lines 267-270) prevents malformed session IDs. File extension allowlists (lines 319-326) restrict upload types at the API layer. Defense-in-depth with both client and server validation. |
| PR.PS-06 | Secure development practices | `backend/utils/config_loader.py` | 13-14 | YAML deserialization uses `yaml.safe_load()` (line 14) instead of `yaml.load()`, preventing arbitrary code execution via malicious YAML objects. |

### PR.IR -- Technology Infrastructure Resilience

| CSF ID | Subcategory | File | Lines | What Was Done |
|--------|------------|------|-------|---------------|
| PR.IR-01 | Networks and environments are protected from unauthorized logical access | `backend/api/search_api.py` | 51-69 | CORS origin restrictions limit which domains can make API requests. Environment variable `CORS_ALLOW_ORIGINS` allows production-specific origin configuration (lines 51-53). LAN regex restricts private network access to port 3000 only (line 66). |
| PR.IR-01 | Networks protected | `docker-prod/docker-compose.yml` | 46-52 | Container-level network protection: all Linux capabilities dropped (`cap_drop: ALL`, lines 49-50), privilege escalation prevented (`no-new-privileges:true`, lines 51-52), temporary filesystems mounted as tmpfs (lines 46-48) reducing persistent attack surface. |
| PR.IR-01 | Networks protected | `docker-prod/backend.Dockerfile` | 17-23 | Non-root container execution: dedicated `app` user and group created (line 17), container runs as `USER app` (line 23). Limits blast radius if container is compromised. |
| PR.IR-01 | Networks protected | `docker-prod/frontend.Dockerfile` | 12-25 | Frontend container also runs non-root with `read_only: true` filesystem in docker-compose, preventing any file modification from within the container. |
| PR.IR-03 | Resilience mechanisms implemented | `backend/services/diagram_vision.py` | 33-37 | Image decompression bomb protection: Pillow `MAX_IMAGE_PIXELS` capped at 250 million pixels (line 36). Prevents memory exhaustion from maliciously crafted images that decompress to gigabytes. Images immediately downscaled after loading. |
| PR.IR-03 | Resilience mechanisms | `backend/services/erd_extraction.py` | 77-80 | Text truncation at 500K characters (`truncate_text`, lines 77-80) prevents unbounded memory consumption from extremely large documents. Truncated content is marked with `[Content truncated for storage.]` for traceability. |
| PR.IR-04 | Adequate resource capacity maintained | `backend/api/erd_processor.py` | 325-326, 355-357 | File size limits (50MB) on all upload endpoints prevent storage exhaustion attacks. Applied to both ERD documents (line 325) and diagram images (line 355). |
| PR.IR-04 | Resource capacity maintained | `backend/qa/qa_chain.py` | 256-267 | LLM context budget capped at 40,000 tokens (line 258). Each chunk individually truncated to prevent exceeding model context windows. Total `used` tokens tracked and capped (lines 264-266), preventing resource exhaustion from large document sets. |

---

## DETECT (DE)

### DE.CM -- Continuous Monitoring

| CSF ID | Subcategory | File | Lines | What Was Done |
|--------|------------|------|-------|---------------|
| DE.CM-09 | Computing environments monitored | `backend/api/search_api.py` | 244-249 | `/metrics` endpoint exposes in-process application metrics via `get_metrics().get_summary()` (lines 244-249). Provides runtime visibility into application behavior for monitoring systems. |
| DE.CM-09 | Computing environments monitored | `docker-prod/docker-compose.yml` | Healthcheck sections | Docker healthchecks configured for services, enabling container orchestration to detect and restart unhealthy instances automatically. |

---

## Areas Not Currently Covered (Gaps by Function)

| NIST CSF Function | Category | Gap Description |
|---|---|---|
| **GOVERN** | GV.RR | No documented roles and responsibilities for cybersecurity within the application |
| **PROTECT** | PR.AA-05 | No access permissions or authorization (anyone with `analysis_id` can access data) |
| **PROTECT** | PR.PS-04 | No structured security audit logging (uses `print()` statements) |
| **PROTECT** | PR.DS-01 | No application-layer encryption for files on disk or database fields |
| **DETECT** | DE.CM-03 | No personnel activity monitoring or audit trails |
| **DETECT** | DE.AE | No adverse event analysis capability (no SIEM integration, no alert rules) |
| **RESPOND** | RS.MA | No documented incident response plan |
| **RECOVER** | RC.RP | No documented recovery procedures |

---

## Summary by NIST CSF 2.0 Function

| Function | Category | Subcategories Covered | Key Implementation Highlights |
|----------|----------|----------------------|-------------------------------|
| **GOVERN** | GV.PO, GV.SC | GV.PO-01, GV.SC-04 | Security policy (SECURITY.md), dependency vulnerability scanning |
| **IDENTIFY** | ID.AM, ID.RA | ID.AM-02, ID.AM-03, ID.RA-01 | HLD/LLD/DFD documentation, dependency inventories, vulnerability scan reports |
| **PROTECT** | PR.AA | PR.AA-01, PR.AA-03 | OAuth client credentials for LLM service authentication |
| **PROTECT** | PR.DS | PR.DS-01, PR.DS-02 | NUL byte sanitization, SHA256 integrity hashing, HTTPS for external APIs, CORS restrictions |
| **PROTECT** | PR.PS | PR.PS-01, PR.PS-06 | Secrets via env vars, .gitignore exclusions, parameterized SQL, Pydantic validation, safe YAML parsing |
| **PROTECT** | PR.IR | PR.IR-01, PR.IR-03, PR.IR-04 | Docker hardening (cap_drop ALL, non-root, no-new-privileges, read_only), pixel flood protection, text truncation, file size limits, LLM token budgets |
| **DETECT** | DE.CM | DE.CM-09 | Application metrics endpoint, Docker healthchecks |
| **Total** | | **17 subcategories** | Strongest coverage in platform security (PR.PS) and infrastructure resilience (PR.IR) |

---

## Coverage Summary

| NIST CSF 2.0 Function | Subcategories Implemented | Notes |
|------------------------|--------------------------|-------|
| GOVERN (GV) | 2 | GV.PO-01, GV.SC-04 |
| IDENTIFY (ID) | 3 | ID.AM-02, ID.AM-03, ID.RA-01 |
| PROTECT (PR) | 10 | PR.AA-01, PR.AA-03, PR.DS-01, PR.DS-02, PR.PS-01, PR.PS-06, PR.IR-01, PR.IR-03, PR.IR-04 (strongest area) |
| DETECT (DE) | 1 | DE.CM-09 |
| RESPOND (RS) | 0 | No incident response capabilities implemented |
| RECOVER (RC) | 0 | No recovery procedures implemented; Docker restart policies provide basic container-level recovery |
| **Total** | **16 subcategories** | Strongest coverage in PROTECT function -- platform security and infrastructure resilience via Docker hardening |
