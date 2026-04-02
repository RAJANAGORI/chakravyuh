#!/bin/sh
# Start Ollama server, pull the embedding model (used by the backend), then keep server running.
set -e
MODEL="${OLLAMA_EMBEDDING_MODEL:-embeddinggemma}"

# Start server in background
ollama serve &
OLLAMA_PID=$!

# Wait for server to accept connections
sleep 15
# Pull embedding model (idempotent; no-op if already present)
ollama pull "$MODEL" || true

# Keep container running by waiting on server
wait $OLLAMA_PID
