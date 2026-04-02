<p align="center">
  <img src="./assets/image.png" alt="Chakravyuh Logo" width="250"/>
</p>

# Chakravyuh

AI-assisted **security threat modeling** from uploaded **ERD and supporting documents** plus **architecture diagrams**. The app extracts and stores text, generates **vision summaries** for diagrams, and answers questions via a **chat LLM** scoped to an analysis session (`analysis_id`). **Vector RAG / semantic search** is not part of the current flow; context comes only from what you upload.

## Architecture (summary)

| Layer | Stack |
|--------|--------|
| **Frontend** | Next.js 15, React 18, Tailwind CSS, shadcn/ui |
| **Backend** | FastAPI (`api.search_api`), LangChain for LLM calls |
| **Data** | PostgreSQL (`analysis_sessions`, `analysis_documents`); files under `backend/knowledge/` |
| **LLM** | Azure OpenAI (default) or OpenAI; OAuth/token via `TM_*` env vars |

Design docs: **[docs/HLD.md](docs/HLD.md)** (high level), **[docs/LLD.md](docs/LLD.md)** (modules & APIs), **[docs/DFD.md](docs/DFD.md)** (data flows).

## Repository layout

```
threat-model/
├── frontend/              # Next.js app (upload UI + chat)
├── backend/
│   ├── api/               # search_api.py, erd_processor.py
│   ├── qa/                # QAService, CIA/AAA playbook prompts
│   ├── services/          # ERD extraction, diagram vision
│   ├── utils/             # DB, LLM provider, tokenizer, metrics
│   ├── migrations/        # SQL helpers (e.g. analysis_documents)
│   ├── config.example.yaml# copy to config.yaml
│   └── knowledge/         # uploaded ERD/diagram files (gitignored)
├── docker-prod/           # Compose, Dockerfiles, initdb
├── docs/                  # HLD / LLD / DFD
├── start-dev.sh           # backend + frontend (dev)
├── setup-local.sh         # local venv, deps, optional DB
└── setup-prod.sh          # Docker Compose stack
```

## Prerequisites

- **Node.js** 18+
- **Python** 3.10+
- **PostgreSQL** 13+ (local or Docker)
- LLM access: **Azure OpenAI–compatible** endpoint or **OpenAI** API key

## Quick start

### Option A — automated setup (recommended)

```bash
./setup-local.sh
```

Then start both services:

```bash
./start-dev.sh
```

- **Frontend:** http://localhost:3000  
- **Backend API:** http://localhost:8000  
- **OpenAPI:** http://localhost:8000/docs  

### Option B — manual

**1. Database**

Create a database and user, then set **`backend/.env`** (see `backend/.env.example`):

```bash
PG_HOST=localhost
PG_PORT=5432
PG_DB=chakravyuh
PG_USER=chakravyuh
PG_PASSWORD=chakravyuh
```

The app reads **only** these `PG_*` variables for connections (not the `database:` block in YAML).

**2. Backend**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp config.example.yaml config.yaml
# Edit config.yaml — use env for secrets (TM_*, OPENAI_API_KEY) in production

make api
# → http://localhost:8000
```

**3. Frontend** (from repository root, npm workspaces)

```bash
npm install
npm run dev --workspace=frontend
# → http://localhost:3000
```

## Configuration

| Artifact | Purpose |
|----------|---------|
| `backend/config.example.yaml` | Template; copy to **`config.yaml`** (gitignored if you add secrets) |
| `backend/.env` | **`PG_*`** for PostgreSQL; optional overrides |
| Env vars | **`TM_API_CLIENT_ID`**, **`TM_API_CLIENT_SECRET`**, **`TM_TOKEN_URL`**, **`TM_API_APP_KEY`**, **`TM_API_USER_ID`** (Azure/gateway), **`OPENAI_API_KEY`** (OpenAI provider) |

Prompts for chat live in **`backend/qa/qa_chain.py`** (system text + CIA/AAA playbook). Diagram vision system text is in **`backend/services/diagram_vision.py`**.

## Features

- **Multi-file analysis session** — `analysis_id` ties ERD PDFs, supporting text/PDF/JSON/TXT, and architecture diagrams.
- **ERD text extraction** — PDF (with optional OCR settings), JSON, TXT.
- **Diagram processing** — images/PDF; vision model produces a **stored text summary** (not re-run on every chat turn).
- **Guided threat modeling chat** — `/ask` and structured **`/threat-modeling`** with CIA/AAA-oriented playbook in the backend.
- **Health** — `GET /health` (database + LLM readiness).
- **Metrics** — `GET /metrics` (in-process collector).

## Operations

| URL | Description |
|-----|-------------|
| http://localhost:8000/health | Liveness and dependency checks |
| http://localhost:8000/metrics | Basic metrics summary |
| http://localhost:8000/docs | Swagger UI |

## Docker (production-style)

See **`docker-prod/README.md`** and **`setup-prod.sh`**. Backend mounts **`config.yaml`** and persists uploads under **`docker-prod/data/knowledge`**.

## Development commands

```bash
# Root — run Next.js dev (workspace)
npm run dev

# Backend — API only (from backend/, with venv active)
make api

# Frontend — typecheck
npm run typecheck --workspace=frontend
```

## Security

See **[backend/SECURITY.md](backend/SECURITY.md)** for guidelines. Do not commit real **`config.yaml`** credentials; use **`config.example.yaml`** as the template.

## License

Specify your license here.

---

**Built with:** Next.js, FastAPI, PostgreSQL, LangChain, Pydantic.
