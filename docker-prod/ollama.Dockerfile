# Ollama with embedding model pulled on first start (for backend embeddings)
FROM ollama/ollama:latest
COPY scripts/ollama-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENV OLLAMA_EMBEDDING_MODEL=embeddinggemma
ENTRYPOINT ["/entrypoint.sh"]
