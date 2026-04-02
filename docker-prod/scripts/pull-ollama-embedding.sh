#!/usr/bin/env bash
# Pull the Ollama embedding model used by the backend (embeddinggemma).
# Run once after 'docker compose up -d'. Uses model name from backend config default.
set -e
MODEL="${1:-embeddinggemma}"
echo "Waiting for Ollama (chakravyuh_ollama) to be ready, then pulling $MODEL..."
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  if docker exec chakravyuh_ollama ollama pull "$MODEL" 2>/dev/null; then
    echo "Done. Embedding model $MODEL is ready."
    exit 0
  fi
  echo "Attempt $i: server may still be starting..."
  sleep 5
done
echo "Failed to pull $MODEL. Ensure the container is up: docker ps | grep chakravyuh_ollama"
exit 1
