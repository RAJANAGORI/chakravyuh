# api/search_api.py
from fastapi import FastAPI, Query
from rag_retriever.retriever import Retriever
from qa.qa_chain import QAService
from fastapi.openapi.utils import get_openapi


app = FastAPI(title="RAG Search API")

retriever = Retriever(k=5)          # existing basic retriever (used by /search)
qa = QAService(k=6)                 # new reasoning service (used by /ask)

@app.get("/search")
def search(q: str = Query(..., description="Search query")):
    docs = retriever.search(q)
    return {"results": [{"content": d.page_content, "metadata": d.metadata} for d in docs]}

@app.get("/ask")
def ask(
    q: str = Query(..., description="Question"),
    k: int = 6,
    structured: bool = False,
    service: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
):
    result = qa.answer(q, k=k, structured=structured, service=service, start_date=start_date, end_date=end_date)
    return result

@app.get("/openapi.json")
def openapi_endpoint():
    return get_openapi(
        title="Chakravyuh RAG API",
        version="1.0.0",
        routes=app.routes,
    )

@app.get("/favicon.ico")
def favicon():
    return {}