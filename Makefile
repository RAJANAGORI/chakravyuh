.PHONY: scrape ingest erd insert api test install aws-list aws-update aws-update-high

# Install dependencies
install:
	pip install -r requirements.txt

# Scraping
scrape:
	python scripts/ingestion/scrape_aws.py

# Ingestion
ingest:
	python -m chakravyuh.ingestion.processors.document_processor

erd:
	python -m chakravyuh.ingestion.loaders.erd_loader

# Storage
insert:
	python -m chakravyuh.storage.vector.pgvector_store

# API
api:
	uvicorn chakravyuh.api.enhanced_api:app --reload --port 8000

api-legacy:
	uvicorn api.search_api:app --reload --port 8000

# Testing (uses virtual environment if available)
test:
	@if [ -f .venv/bin/activate ]; then \
		source .venv/bin/activate && pytest tests/ -v; \
	elif [ -f chakravyuh/bin/activate ]; then \
		source chakravyuh/bin/activate && pytest tests/ -v; \
	else \
		python3 -m pytest tests/ -v; \
	fi

test-coverage:
	@if [ -f .venv/bin/activate ]; then \
		source .venv/bin/activate && pytest tests/ --cov=chakravyuh --cov-report=html; \
	elif [ -f chakravyuh/bin/activate ]; then \
		source chakravyuh/bin/activate && pytest tests/ --cov=chakravyuh --cov-report=html; \
	else \
		python3 -m pytest tests/ --cov=chakravyuh --cov-report=html; \
	fi

test-security:
	@if [ -f .venv/bin/activate ]; then \
		source .venv/bin/activate && pytest tests/unit/test_security.py -v; \
	elif [ -f chakravyuh/bin/activate ]; then \
		source chakravyuh/bin/activate && pytest tests/unit/test_security.py -v; \
	else \
		python3 -m pytest tests/unit/test_security.py -v; \
	fi

test-kg:
	@if [ -f .venv/bin/activate ]; then \
		source .venv/bin/activate && pytest tests/unit/test_knowledge_graph.py -v; \
	elif [ -f chakravyuh/bin/activate ]; then \
		source chakravyuh/bin/activate && pytest tests/unit/test_knowledge_graph.py -v; \
	else \
		python3 -m pytest tests/unit/test_knowledge_graph.py -v; \
	fi

test-eval:
	@if [ -f .venv/bin/activate ]; then \
		source .venv/bin/activate && pytest tests/unit/test_evaluation.py -v; \
	elif [ -f chakravyuh/bin/activate ]; then \
		source chakravyuh/bin/activate && pytest tests/unit/test_evaluation.py -v; \
	else \
		python3 -m pytest tests/unit/test_evaluation.py -v; \
	fi

# AWS Services Management
aws-list:
	python scripts/aws_services_manager.py list --by-category

aws-update:
	python scripts/aws_services_manager.py update --dry-run

aws-update-high:
	python scripts/aws_services_manager.py update --priority high
