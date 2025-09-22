<p align="center">
  <img src="./assets/image.png" alt="Chakravyuh Logo" width="250"/>
</p>

# Chakravyuh RAG

A modular Retrieval - Augmented Generation (RAG) system for secure knowledge retrieval and threat modeling.

## Purpose and Setup Guide

## Introduction

This project aims to build a modular Retrieval - Augmented Generation (RAG) system designed for secure knowledge retrieval and threat modeling. Inspired by the concept of *Chakravyuh* from the Mahabharata - a complex battle formation symbolizing layered defenses - this system implements a layered architecture where each phase contributes to a robust and flexible pipeline.

This labyrinth/spiral image visually resonates with the Chakravyuh theme:

- Layers → Just like your RAG pipeline (scraping → ingestion → storage → retrieval → reasoning).
- Defense & complexity → Symbolizes security, threat modeling, and the concentric barriers from Mahabharata.
- Path inward/outward → Mirrors how queries travel through your system to uncover knowledge and insights.

---

## Purpose

- **Goal:** To create an end-to-end, modular RAG pipeline that supports scraping, ingestion, storage, retrieval, and reasoning.
- **Why "Chakravyuh":** The name reflects the layered design of the system, where each phase acts like a concentric defense layer in the chakravyuh formation.
- **Core uses:** 
  - Threat modeling (CIA/AAA frameworks)
  - Ingestion of security documentation
  - Flexible integration with LLMs, including OpenAI and custom models

---

## 0) Prerequisites

- Python 3.10+ (you’re on 3.13 ✅)
- Docker + Docker Compose
- OpenAI API key

---

## 1) Create and activate a virtualenv

```
cd /Users/rajanagori/Documents/vault/Projects/chakravyuh

python -m venv chakravyuh
source chakravyuh/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

If fastapi / uvicorn / psycopg2-binary are missing, run:

```
pip install fastapi uvicorn psycopg2-binary
```

---

## 2) Configure

### config.yaml

Create or update `config.yaml` in the repo root:

```
openai:
  api_key: "sk-REPLACE_ME"
  model: "text-embedding-3-small"
  chat_model: "gpt-4o-mini"

langsmith:            # optional
  api_key: ""
  project: "chakravyuh-rag"
  endpoint: "https://api.smith.langchain.com"

aws_docs:
  base_dir: "./aws_docs"
  max_workers: 2
  services:
    - name: "s3"
      url: "https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html"
    - name: "ec2"
      url: "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/what-is-ec2.html"

database:
  user: "raja"
  password: "secret"
  host: "localhost"
  port: 5432
  dbname: "ragdb"
  collection: "documents"
  index_type: "hnsw"     # or "ivfflat"
  index_params:
    lists: 100           # only for ivfflat
```

---

## 3) Start Postgres + pgvector (Docker)

Create `docker-compose.yml` in the repo root:

```
version: "3.9"
services:
  db:
    image: ankane/pgvector:latest
    container_name: chakravyuh_pgvector
    restart: always
    environment:
      POSTGRES_USER: raja
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: ragdb
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

Run it:

```
docker-compose up -d
```

Initialize extension & table (first time only):

```
docker exec -it chakravyuh_pgvector psql -U raja -d ragdb -c "CREATE EXTENSION IF NOT EXISTS vector;"

docker exec -it chakravyuh_pgvector psql -U raja -d ragdb -c "
  CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    content TEXT,
    metadata JSONB,
    embedding VECTOR(1536)
  );
"
```

If your metadata column was JSON earlier:

```
docker exec -it chakravyuh_pgvector psql -U raja -d ragdb -c \
"ALTER TABLE documents ALTER COLUMN metadata TYPE JSONB USING metadata::JSONB;"
```

---

## 4) Phase 1 — Scrape AWS docs

```
python main.py
```

Quick sanity check:

```
tree aws_docs -L 2
```

You should see `aws_docs/s3/*.json` and `aws_docs/ec2/*.json`.

---

## 5) Phase 2 — Ingest + Embed (LangChain)

```
python ingestion/ingestion.py
```

If you have ERD PDFs/TXT, place them in `./knowledge/erd/` then:

```
python ingestion/erd_ingestion.py
```

Check outputs:

```
tree embedded_docs -L 2
```

You should see:

- `embedded_docs/s3/*_lc.json`
- `embedded_docs/ec2/*_lc.json`
- `embedded_docs/erd/*_lc.json` (if you ran ERD ingestion)

---

## 6) Phase 3 — Bulk insert into pgvector

Run as module from project root (so imports work):

```
python -m vectorstores.pgvector_store
```

Expected logs:

```
✅ Inserted 128 docs from ./embedded_docs/s3/...
🎯 Total inserted: 1230 documents
```

---

## 7) Phase 4/5 — Run the API (Retrieval + LLM)

Start FastAPI:

```
uvicorn api.search_api:app --reload --port 8000
```

Open docs:

- Swagger → [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Redoc → [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

Test endpoints:

```
# health
curl 'http://127.0.0.1:8000/health'

# retrieve chunks
curl 'http://127.0.0.1:8000/search?q=what%20is%20amazon%20s3&k=5'

# LLM answer (plain)
curl 'http://127.0.0.1:8000/ask?q=What%20is%20Amazon%20S3%20and%20how%20is%20it%20secured?'

# LLM structured CIA/AAA
curl 'http://127.0.0.1:8000/ask?q=Perform%20a%20CIA%2FAAA%20threat%20model%20for%20our%20S3%20data%20path%20and%20EC2%20access%20patterns.%20Limit%20to%20top%205%20items%20in%20each%20category.&structured=true'
```

---

## Quick “A → B → C → D → E” Flow

```
# A: Collect
python main.py

# B: Chunk + Embed
python ingestion/ingestion.py
# (optional ERD)
python ingestion/erd_ingestion.py

# C: Store
python -m vectorstores.pgvector_store

# D + E: Retrieve + Reason
uvicorn api.search_api:app --reload --port 8000
```

---

## Tips

### Makefile to streamline

Create `Makefile`:

```
.PHONY: scrape ingest erd insert api

scrape:
python main.py

ingest:
python -m ingestion.ingestion

erd:
python -m ingestion.erd_ingestion

insert:
python -m vectorstores.pgvector_store

api:
uvicorn api.search_api:app --reload --port 8000
```

Run:

```
make scrape
make ingest
make insert
make api
```

### Common fixes

- **OPENAI_API_KEY error:** Ensure `config.yaml` has the key; code sets env automatically.
- **psycopg / libpq issues:** Run `pip install psycopg2-binary`.
- **Import errors when running files directly:** Prefer `python -m package.module` from repo root.
- **Name collision with retriever:** Renamed to `rag_retriever`; keep imports updated.
- **Deprecation warning about PGVector (community):** Safe to ignore for now; can migrate to `langchain_postgres.PGVector` later.
- Remember to add `config.yaml` to `.gitignore` to avoid committing secrets.

---

✅ Follow the steps top-to-bottom to have your full RAG pipeline up and serving answers.