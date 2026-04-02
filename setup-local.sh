#!/usr/bin/env bash
# One-shot local development setup: Python venv, pip, npm, optional Docker Postgres, backend/.env
# Usage: ./setup-local.sh
# Env:
#   THREAT_MODEL_SKIP_DOCKER_DB=1  — do not start PostgreSQL in Docker
#   THREAT_MODEL_PG_PORT=5433      — host port when starting the dev DB container
#   PYTHON_CMD=/path/to/python3.12 — force interpreter (requires Python 3.10+)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

info() { echo "[setup-local] $*"; }
warn() { echo "[setup-local] WARNING: $*" >&2; }
die() { echo "[setup-local] ERROR: $*" >&2; exit 1; }

command -v node >/dev/null || die "Node.js is required (node)"
command -v npm >/dev/null || die "npm is required"

info "Project root: $ROOT"

# --- Python 3.10+ required (numpy 2.3.x, pandas 2.3.x, langchain stack, etc.) ---
PYTHON_CMD="${PYTHON_CMD:-}"
if [[ -z "$PYTHON_CMD" ]]; then
  for candidate in python3.13 python3.12 python3.11 python3.10; do
    if command -v "$candidate" >/dev/null 2>&1 \
      && "$candidate" -c 'import sys; assert sys.version_info >= (3, 10)' 2>/dev/null; then
      PYTHON_CMD="$candidate"
      break
    fi
  done
fi
if [[ -z "$PYTHON_CMD" ]] && command -v python3 >/dev/null 2>&1; then
  if python3 -c 'import sys; assert sys.version_info >= (3, 10)' 2>/dev/null; then
    PYTHON_CMD=python3
  fi
fi
if [[ -z "$PYTHON_CMD" ]]; then
  die "Python 3.10+ is required (your default python3 may be 3.9).
  Install:  brew install python@3.12
  Then run:  PATH=\"/opt/homebrew/opt/python@3.12/bin:\$PATH\" ./setup-local.sh
  (Intel Mac: /usr/local/opt/python@3.12/bin)
  Or set:    PYTHON_CMD=/opt/homebrew/bin/python3.12 ./setup-local.sh"
fi
if ! "$PYTHON_CMD" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
  die "PYTHON_CMD must be 3.10+: $($PYTHON_CMD --version 2>&1)"
fi
info "Using interpreter: $PYTHON_CMD ($($PYTHON_CMD --version 2>&1))"

# --- Python ---
# Recreate venv if it was copied from another machine, moved folder, or points at a dead interpreter.
venv_py="$ROOT/backend/venv/bin/python3"
if [[ -d "$ROOT/backend/venv" ]]; then
  if [[ ! -x "$venv_py" ]] || ! "$venv_py" -c "import sys" 2>/dev/null; then
    info "Removing broken backend/venv (stale path or invalid interpreter — common after moving the repo)."
    rm -rf "$ROOT/backend/venv"
  elif ! "$venv_py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    info "Removing backend/venv (built with Python < 3.10; requirements need 3.10+)."
    rm -rf "$ROOT/backend/venv"
  fi
fi
if [[ ! -d "$ROOT/backend/venv" ]]; then
  info "Creating Python virtualenv in backend/venv..."
  "$PYTHON_CMD" -m venv "$ROOT/backend/venv"
fi

info "Installing Python dependencies..."
"$ROOT/backend/venv/bin/pip" install -q -U pip wheel
"$ROOT/backend/venv/bin/pip" install -q -r "$ROOT/backend/requirements.txt"

# --- Node ---
info "Installing Node dependencies (root workspace + frontend)..."
if [[ -f "$ROOT/package-lock.json" ]]; then
  (cd "$ROOT" && npm ci)
else
  (cd "$ROOT" && npm install)
fi

# --- backend/.env ---
if [[ ! -f "$ROOT/backend/.env" ]]; then
  PG_PORT="${THREAT_MODEL_PG_PORT:-5432}"
  cat > "$ROOT/backend/.env" << EOF
PG_HOST=localhost
PG_PORT=${PG_PORT}
PG_DB=chakravyuh
PG_USER=chakravyuh
PG_PASSWORD=chakravyuh
EOF
  info "Created backend/.env (PostgreSQL). Edit if your database differs."
else
  info "Keeping existing backend/.env"
fi

# --- Optional: PostgreSQL in Docker (pgvector + init schema) ---
DEV_DB_CONTAINER="${THREAT_MODEL_DEV_DB_CONTAINER:-threat-model-dev-postgres}"
PG_PORT="${THREAT_MODEL_PG_PORT:-5432}"

if [[ "${THREAT_MODEL_SKIP_DOCKER_DB:-}" == "1" ]]; then
  info "Skipping Docker PostgreSQL (THREAT_MODEL_SKIP_DOCKER_DB=1). Ensure PG_* in backend/.env match your database."
else
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$DEV_DB_CONTAINER"; then
      info "Starting existing container: $DEV_DB_CONTAINER"
      docker start "$DEV_DB_CONTAINER" >/dev/null || true
    else
      info "Starting PostgreSQL ($DEV_DB_CONTAINER) on host port $PG_PORT..."
      if ! docker run -d \
        --name "$DEV_DB_CONTAINER" \
        -e POSTGRES_USER=chakravyuh \
        -e POSTGRES_PASSWORD=chakravyuh \
        -e POSTGRES_DB=chakravyuh \
        -p "${PG_PORT}:5432" \
        -v "$ROOT/docker-prod/initdb:/docker-entrypoint-initdb.d:ro" \
        ankane/pgvector:latest; then
        warn "Could not start Postgres container (port conflict?). Set THREAT_MODEL_SKIP_DOCKER_DB=1 and run your own Postgres, or set THREAT_MODEL_PG_PORT to a free port."
      else
        info "Waiting for database to accept connections..."
        for _ in $(seq 1 40); do
          if docker exec "$DEV_DB_CONTAINER" pg_isready -U chakravyuh -d chakravyuh >/dev/null 2>&1; then
            break
          fi
          sleep 1
        done
      fi
    fi
  else
    warn "Docker not available or daemon not running. Start PostgreSQL yourself and align backend/.env (PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD)."
  fi
fi

info ""
info "Local setup finished."
info ""
info "Configure LLM credentials (required for chat):"
info "  export TM_API_CLIENT_ID=... TM_API_CLIENT_SECRET=... TM_TOKEN_URL=... TM_API_APP_KEY=... TM_API_USER_ID=..."
info "  (see backend/config.yaml comments)"
info ""
info "Start the app:"
info "  ./start-dev.sh"
info ""
info "Or two terminals:"
info "  cd backend && make api"
info "  npm run dev --workspace=frontend"
info ""
