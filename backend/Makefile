.PHONY: api

# Legacy scrape/ingest/vector targets removed — use API upload flow only.

api:
	bash -c "set -e; cd '$(CURDIR)' && set -a && [ -f .env ] && . ./.env; set +a && source venv/bin/activate && exec uvicorn api.search_api:app --reload --port 8000"
