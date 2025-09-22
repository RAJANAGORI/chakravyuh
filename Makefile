.PHONY: scrape ingest erd insert api

scrape:
	python main.py

ingest:
	python -m ingestion.langchain_ingestion

erd:
	python -m ingestion.erd_ingestion

insert:
	python -m vectorstores.pgvector_store

api:
	uvicorn api.search_api:app --reload --port 8000