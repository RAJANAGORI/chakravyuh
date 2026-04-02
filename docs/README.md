# Chakravyuh — Design Documentation

Architecture and data-flow documentation for **Chakravyuh** (Next.js UI + FastAPI backend + PostgreSQL + LLM).

| Document | Purpose |
|----------|---------|
| [HLD.md](./HLD.md) | **High-Level Design** — system context, major components, deployment view, trust boundaries |
| [LLD.md](./LLD.md) | **Low-Level Design** — modules, APIs, key classes, sequences, configuration |
| [DFD.md](./DFD.md) | **Data Flow Diagrams** — context (Level 0), major processes (Level 1), chat and upload flows |

**Scope note (current codebase):** Document Q&A is grounded in **stored extracted text** and **vision-generated diagram summaries**. Legacy **vector RAG / semantic search** has been removed; `/search` returns HTTP 410.
