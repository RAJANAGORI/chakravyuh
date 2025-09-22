# qa/qa_chain.py
import os
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from utils.config_loader import load_config
from rag_retriever.retriever import Retriever
import tiktoken

# ---------- Structured output schema (CIA / AAA) ----------
class RiskItem(BaseModel):
    risk: str
    impact: str
    likelihood: str
    mitigations: List[str] = Field(default_factory=list)

class CIASection(BaseModel):
    confidentiality: List[RiskItem] = Field(default_factory=list)
    integrity: List[RiskItem] = Field(default_factory=list)
    availability: List[RiskItem] = Field(default_factory=list)

class AAASection(BaseModel):
    authentication: List[RiskItem] = Field(default_factory=list)
    authorization: List[RiskItem] = Field(default_factory=list)
    accounting: List[RiskItem] = Field(default_factory=list)

class ThreatModelReport(BaseModel):
    scope_summary: str
    cia: CIASection
    aaa: AAASection
    key_controls: List[str] = Field(default_factory=list)
    residual_risk_rating: str
    assumptions: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)  # urls or titles

# ---------- Helpers ----------
def _truncate_to_tokens(text: str, limit: int, model: str) -> str:
    enc = tiktoken.encoding_for_model(model if model else "gpt-4o-mini")
    tokens = enc.encode(text)
    if len(tokens) <= limit:
        return text
    return enc.decode(tokens[:limit])

def _render_context(docs, per_doc_prefix=True) -> List[str]:
    chunks = []
    for i, d in enumerate(docs, 1):
        head = f"[{i}] {d.metadata.get('heading') or d.metadata.get('filename') or d.metadata.get('service_page') or 'chunk'}"
        src = d.metadata.get("url") or d.metadata.get("source_hint") or ""
        content = d.page_content.strip()
        if per_doc_prefix:
            chunks.append(f"{head}\nSOURCE: {src}\n{content}")
        else:
            chunks.append(content)
    return chunks

# ---------- Main service ----------
class QAService:
    def __init__(self, k: int = 6):
        cfg = load_config("config.yaml")
        os.environ["OPENAI_API_KEY"] = cfg["openai"]["api_key"]
        self.chat_model_name = cfg["openai"].get("chat_model", "gpt-4o-mini")
        self.llm = ChatOpenAI(model=self.chat_model_name, temperature=0)
        self.retriever = Retriever(k=k)

    def _build_messages(self, question: str, contexts: List[str], structured: bool) -> List[dict]:
        system = (
            "You are a careful assistant that answers **using only the provided context**. "
            "If the context seems insufficient or conflicting, say so and ask for clarification. "
            "Prefer quoting exact phrasing when justifying. Cite with [n] using the bracket numbers of context items."
        )
        joined = "\n\n".join(f"[{i+1}] {c}" for i, c in enumerate(contexts))
        user = (
            "Context:\n"
            f"{joined}\n\n"
            "Question:\n"
            f"{question}\n\n"
            "Instructions:\n"
            "- Use the most relevant context chunks.\n"
            "- Include bracketed citations like [1], [2].\n"
        )
        if structured:
            user += "- Produce a structured CIA/AAA threat model.\n"
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def answer(self, question: str, k: int = 6, structured: bool = False, service: Optional[str] = None,
               start_date: Optional[str] = None, end_date: Optional[str] = None):
        # 1) Retrieve
        docs = self.retriever.search(question)
        # Optional post-filter by service (S3/EC2 heuristic based on URL)
        if service:
            key = "AmazonS3" if service.lower() == "s3" else "AWSEC2"
            docs = [d for d in docs if key in (d.metadata.get("url") or "")]
        # Optional date filter (scraped_at within [start_date, end_date])
        def keep(d):
            ts = d.metadata.get("scraped_at")
            if start_date and (not ts or ts < start_date): return False
            if end_date and (not ts or ts > end_date): return False
            return True
        docs = [d for d in docs if keep(d)]

        # 2) Token-budgeted context
        ctx_list = _render_context(docs)
        # 3k tokens budget for context by default (adjust model-dependent)
        context_budget = 3000
        packed = []
        used = 0
        for c in ctx_list:
            t = _truncate_to_tokens(c, 800, self.chat_model_name)  # ~800 tokens per chunk
            packed.append(t)
            used += 800
            if used >= context_budget:
                break

        # 3) Build messages
        messages = self._build_messages(question, packed, structured)

        # 4) Call LLM
        if structured:
            # Use structured output to ThreatModelReport
            tool_llm = self.llm.with_structured_output(ThreatModelReport)
            result: ThreatModelReport = tool_llm.invoke(messages)
            # Add citations as sources (urls or titles)
            result.sources = [d.metadata.get("url") or (d.metadata.get("filename") or "") for d in docs[:len(packed)]]
            return result.dict()
        else:
            resp = self.llm.invoke(messages)
            return {
                "answer": resp.content,
                "sources": [d.metadata.get("url") or (d.metadata.get("filename") or "") for d in docs[:len(packed)]]
            }