# Data Flow Diagrams (DFD)

Notation: **External entity** = square-corner box; **Process** = rounded rectangle; **Data store** = open rectangle; **Data flow** = labeled arrow. Diagrams use Mermaid for rendering in GitHub / many Markdown viewers.

---

## Level 0 — Context (system as a single process)

Shows the system boundary and external interactions.

```mermaid
flowchart LR
  subgraph entities["External entities"]
    U[Analyst user]
    LLM[LLM / Vision API]
    TOK[Token / OAuth service]
  end

  P0["Chakravyuh Platform\n(ingest + store + Q&A)"]

  U -->|"Upload files, questions,\nanalysis_id"| P0
  P0 -->|"HTML/JSON UI"| U
  P0 -->|"Chat + vision requests"| LLM
  P0 -->|"Client credentials"| TOK
  TOK -->|"Access token"| P0
  LLM -->|"Model output"| P0
```

**Flows summary**

| From | To | Data |
|------|-----|------|
| Analyst | Platform | ERD/supporting files, diagram files, questions, `analysis_id` |
| Platform | Analyst | Chat answers, structured threat JSON, readiness status |
| Platform | LLM | Prompts, image payloads (diagram summary), text context |
| LLM | Platform | Answer text, structured fields |
| Platform | Token service | OAuth client credentials (env) |
| Token service | Platform | Bearer token for gateway |

---

## Level 1 — Major processes

Decomposes the platform into logical processes and data stores.

```mermaid
flowchart TB
  subgraph ext["External entities"]
    U[Analyst]
    LLM[LLM / Vision API]
  end

  subgraph stores["Data stores"]
    D1[("D1: PostgreSQL\nsessions + documents")]
    D2[("D2: File store\nknowledge/erd,\nknowledge/diagrams")]
  end

  P1["1.0\nIngest & extract\nERD / text"]
  P2["2.0\nIngest & summarize\ndiagrams"]
  P3["3.0\nPersist session &\ndocuments"]
  P4["4.0\nThreat modeling\nQ&A"]

  U -->|"PDF/JSON/TXT"| P1
  P1 -->|"extracted text"| P3
  P1 -->|"file bytes"| D2

  U -->|"image/PDF diagram"| P2
  P2 -->|"vision summary text"| P3
  P2 -->|"file bytes"| D2
  P2 <-->|"multimodal API"| LLM

  P3 <-->|"read/write"| D1

  U -->|"question, analysis_id"| P4
  P4 <-->|"load context"| D1
  P4 <-->|"chat"| LLM
  P4 -->|"answer, sources"| U
```

**Process catalog**

| ID | Name | Description |
|----|------|-------------|
| 1.0 | Ingest & extract ERD/text | PDF/JSON/TXT → extracted string; optional OCR path from config |
| 2.0 | Ingest & summarize diagrams | Image/PDF page → raster/resize → vision LLM → plain-text summary |
| 3.0 | Persist session & documents | Writes/updates `analysis_sessions`, `analysis_documents`; links file paths |
| 4.0 | Threat modeling Q&A | Loads bundle for `analysis_id`, packs context, invokes chat LLM (CIA/AAA playbook) |

---

## Level 2 — Q&A process (4.0 detail)

```mermaid
flowchart LR
  subgraph P4["Process 4.0 — Q&A"]
    P4a["4.1 Resolve\nanalysis context"]
    P4b["4.2 Build & truncate\ncontext strings"]
    P4c["4.3 Invoke\nLLM"]
  end

  D1[("D1 PostgreSQL")]
  LLM[LLM API]
  U[Analyst]

  U -->|"q, analysis_id"| P4a
  P4a <-->|"bundle"| D1
  P4a -->|"documents"| P4b
  P4b -->|"messages"| P4c
  P4c <-->|"HTTPS"| LLM
  P4c -->|"answer / JSON"| U
```

**Internal data flows**

| Flow | Data |
|------|------|
| To 4.1 | `analysis_id` (optional → latest session) |
| 4.1 → 4.2 | List of `{ kind, filename, content_text }` plus legacy session fields |
| 4.2 → 4.3 | System + user messages; context chunks labeled by doc type (ERD / supporting / diagram) |
| 4.3 → User | `{ answer, sources }` or structured `ThreatModelReport` |

**Caching:** In-process bundle cache in `qa_chain` (TTL) reduces repeated DB reads for the same `analysis_id`.

---

## Level 2 — Diagram upload process (2.0 + 3.0)

```mermaid
flowchart TB
  U[Analyst] -->|"multipart file"| P2["2.0 Vision pipeline"]
  P2 -->|"JPEG/PNG bytes"| V["Vision LLM\n(image_detail low/high)"]
  V -->|"summary text"| P3["3.0 Persist"]
  P2 -->|"save file"| D2[("D2 Files")]
  P3 -->|"INSERT/UPDATE"| D1[("D1 PostgreSQL")]
  P3 --> U
```

---

## Data dictionary (selected)

| Data | Description |
|------|-------------|
| `analysis_id` | UUID string for an `analysis_sessions` row; ties uploads and chat |
| `erd_text` | Extracted plain text from ERD/supporting uploads |
| `architecture_diagram_summary` | Text summary from vision model (and/or aggregated from `diagram_vision` docs) |
| `content_text` | Row in `analysis_documents` — full text for that chunk (ERD, supporting, or diagram summary) |
| `ready_for_chat` | Derived: has text + diagram content per `GET /api/analysis-status` rules |

---

## Related documents

- [HLD.md](./HLD.md) — containers and trust boundaries
- [LLD.md](./LLD.md) — modules and APIs
