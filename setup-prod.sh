#!/usr/bin/env bash
# One-shot production stack: Docker Compose (db, backend, frontend, ollama) in docker-prod/
# Usage: ./setup-prod.sh
# Run from repository root.
#
# Env:
#   THREAT_MODEL_PULL_OLLAMA=1  — after compose up, pull embeddinggemma into Ollama (slow)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$ROOT/docker-prod"
cd "$COMPOSE_DIR"

info() { echo "[setup-prod] $*"; }
die() { echo "[setup-prod] ERROR: $*" >&2; exit 1; }

command -v docker >/dev/null || die "Docker is required"

if docker compose version >/dev/null 2>&1; then
  DC=(docker compose)
elif docker-compose version >/dev/null 2>&1; then
  DC=(docker-compose)
else
  die "Install Docker Compose (docker compose or docker-compose)"
fi

info "Compose directory: $COMPOSE_DIR"

# --- .env for compose ---
if [[ ! -f .env ]]; then
  if [[ -f ".env copy.example" ]]; then
    cp ".env copy.example" .env
    info "Created .env from '.env copy.example'"
  else
    cat > .env << 'EOF'
POSTGRES_USER=chakravyuh
POSTGRES_PASSWORD=chakravyuh
POSTGRES_DB=chakravyuh
POSTGRES_PORT=5432
CONFIG_PATH=
EOF
    info "Created minimal .env"
  fi
fi

# CONFIG_PATH: absolute path to config mounted into the backend container
CONFIG_ABS="$(cd "$COMPOSE_DIR" && pwd)/config.yaml"
if [[ ! -f "$CONFIG_ABS" ]]; then
  die "Missing $CONFIG_ABS — add config.yaml with provider and credentials."
fi
if [[ -f .env ]]; then
  grep -v '^CONFIG_PATH=' .env > .env.tmp || true
  mv .env.tmp .env
fi
echo "CONFIG_PATH=${CONFIG_ABS}" >> .env
info "CONFIG_PATH=${CONFIG_ABS}"

# --- Persisted data dirs (mounted into containers) ---
mkdir -p "$COMPOSE_DIR/data/knowledge"

info "Building images and starting services..."
"${DC[@]}" up -d --build

info ""
info "Stack is starting. Health checks:"
info "  Backend:  http://localhost:8000/health"
info "  Frontend: http://localhost:3000"
info "  Ollama:   http://localhost:11434"
info ""
info "Set TM_* and OPENAI_API_KEY in the environment or in the mounted config.yaml as documented."
info ""

if [[ "${THREAT_MODEL_PULL_OLLAMA:-}" == "1" ]]; then
  info "Pulling Ollama embedding model (THREAT_MODEL_PULL_OLLAMA=1)..."
  bash "$COMPOSE_DIR/scripts/pull-ollama-embedding.sh" || info "Ollama pull failed; run manually: docker exec chakravyuh_ollama ollama pull embeddinggemma"
fi

info "Done."
