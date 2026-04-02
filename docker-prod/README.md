# Production Docker Setup (Frontend + Backend + DB + Ollama)

This folder contains a hardened Docker Compose setup and production Dockerfiles for the full stack.

## 1) Create your local config.yaml

Create a config.yaml on your host (outside the container) and point Docker to it via CONFIG_PATH.

Minimum example (adjust for your keys):

```yaml
provider: "openai"
embedding_provider: "ollama"

openai:
  api_key: "sk-REPLACE_ME"
  chat_model: "gpt-4o-mini"

ollama:
  base_url: "http://ollama:11434"
  model: "embeddinggemma"

database:
  user: "chakravyuh"
  password: "changeme"
  host: "db"
  port: 5432
  dbname: "ragdb"
  collection: "documents"
  index_type: "hnsw"
  index_params:
    lists: 100
```

## 2) Configure environment variables

Copy the example env file and update values:

```bash
cp .env.example .env
```

Set CONFIG_PATH to the absolute path of your local config.yaml file.

## 3) Build and start

Run from this folder:

```bash
docker compose up -d --build
```

## 4) Embeddings: Ollama vs Azure OpenAI

The app needs **embeddings** so the chat can find relevant ERD sections for each question (RAG). You can use either:

- **Ollama (default)** – The compose stack uses a custom Ollama image that pulls the embedding model on first start. No extra step.
- **Azure OpenAI only** – No Ollama container. In your `config.yaml` set `embedding_provider: "azure_openai"` and under `azure_openai` set `embedding_deployment` to your Azure embedding model (e.g. `text-embedding-ada-002`). Then you can remove or disable the `ollama` service in `docker-compose.yml`.

## 5) Verify

- Backend health: http://localhost:8000/health
- Frontend: http://localhost:3000
- Ollama: http://localhost:11434

## Notes

- The database is initialized with pgvector and tables via initdb/01_schema.sql.
- Backend uploads persist under the mounted volume: `/app/knowledge` (ERD PDFs, diagrams, etc.).
- If you want to change models or providers, update config.yaml on your host.

## Hardening included

- Non-root users in app containers
- Read-only root filesystems for frontend/backend
- Dropped Linux capabilities
- no-new-privileges security option
- tmpfs for writable temp paths