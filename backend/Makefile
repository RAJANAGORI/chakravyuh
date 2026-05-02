.PHONY: api test

# Legacy scrape/ingest/vector targets removed — use API upload flow only.

test:
	bash -c 'set -e; PY=python3; if [ -x venv/bin/python ]; then PY=venv/bin/python; fi; "$$PY" -m pytest tests/ -q --tb=short'

api:
	bash -c "set -e; cd '$(CURDIR)' && set -a && [ -f .env ] && . ./.env; set +a && source venv/bin/activate && exec uvicorn api.search_api:app --reload --port 8000"
