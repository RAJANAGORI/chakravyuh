# qa/qa_chain.py — Q&A from stored ERD text + architecture diagram analysis only (no RAG/embeddings).
from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Literal, Optional

from langchain_core.documents import Document
from pydantic import BaseModel, Field

from utils.auth import is_production_mode
from utils.config_loader import load_config
from utils.db_utils import get_analysis_context_by_id_or_latest
from utils.llm_provider import get_llm
from utils.tokenizer import get_cached_encoding

_analysis_cache: Dict[str, Any] = {
    "data": None,
    "key": None,
    "timestamp": 0,
    "ttl": 300,
}

_CIA_AAA_PLAYBOOK = """
THREAT MODEL REVIEW PLAYBOOK (CIA AAA)
Use this when the user asks about threat modeling, security review, ERD changes, risks, or CIA/AAA.

Framework: CIA (Confidentiality, Integrity, Availability) and AAA (Authentication, Authorization, Accountability).

When producing a full review, structure output in this order and use markdown tables with reference columns:

**Section 1 — Understand ERD / document changes**
- Summarise new or modified entities, relationships, data flows/integrations, external systems and trust boundaries.
- Every row must include an "ERD / doc reference" (section, page, diagram name, or filename from context).

**Section 2 — Security risks from those changes**
- Table: Risk description | Related change | CIA AAA area | Reference (ERD/doc/diagram).

**Section 3 — Threat model (CIA AAA)**
- **3.1 Actors:** Actor | Description | ERD/Diagram reference.
- **3.2 Assets:** Asset | Description | CIA AAA lens (C/I/A/Auth/Authz/Acct) | ERD/Diagram reference.
- **3.3 Trust boundaries and threats:** Boundary | Description | Threats | ERD/Diagram reference.
- **3.4 Security controls:** Boundary | Affected asset | Control name | Description (include **Summary**, **Boundary description**, **Control description**, **Proposed mitigation**) | Severity (Critical/High/Medium/Low) | ERD/Diagram reference.

**Section 4 — Questions for the team**
- Numbered table: Question | Reference (document/section/diagram/filename).

**Section 5 — Closing statement**
- Provide a short closing that references "the analysis above."
- State **there is no security risk** (or that residual risks are acceptable) **only if** the analysis above supports it; otherwise list residual risks and next steps. Do not claim zero risk if you listed material risks in Sections 2–3.

Always cite which uploaded file or diagram each claim comes from when possible (use filenames from context headers).
"""

_STRUCTURED_GROUNDING_RULES = """
STRUCTURED OUTPUT — ANTI-HALLUCINATION / ERD SCOPE (mandatory for JSON)
- You only know this system from the numbered context blocks above. There is no other retrieval.
- threat_analysis: include ONLY risks that are plausibly tied to elements named or described in those blocks.
- Every threat_analysis item MUST set erd_reference to a short phrase or identifier **copied verbatim** from the context (table/entity/API field/diagram label/sentence fragment). If you cannot find such a substring, **omit that threat** entirely.
- Do not populate threats from generic industry checklists unless the upload text explicitly supports them for **this** design (e.g. named external integration, auth boundary, or datastore).
- Prefer fewer, well-anchored findings over many speculative ones.
- If the user asks for breadth beyond what the uploads support, explain the gap in scope_summary and keep threat_analysis small or empty rather than inventing components.
"""


def _norm_ctx_blob(s: str) -> str:
    return " ".join(s.lower().split())


def _threat_row_anchors_context(
    erd_reference: str,
    affected_asset: str,
    boundary_name: str,
    threat_title: str,
    context_blob: str,
) -> bool:
    """Heuristic: require a verbatim-ish anchor in session text to reduce generic false positives."""
    ctx = _norm_ctx_blob(context_blob)
    if not ctx:
        return False
    for chunk in (erd_reference, affected_asset, boundary_name):
        c = _norm_ctx_blob((chunk or "").strip())
        if len(c) >= 8 and c in ctx:
            return True
    blob = f"{erd_reference} {affected_asset} {boundary_name} {threat_title}"
    tokens = re.findall(r"[A-Za-z0-9_]{4,}", blob)
    hits = 0
    seen: set[str] = set()
    for t in tokens:
        tl = t.lower()
        if tl in seen or len(tl) < 4:
            continue
        seen.add(tl)
        if tl in ctx:
            hits += 1
            if hits >= 2:
                return True
    return False


def _enforce_erd_grounding_on_report(report: ThreatModelReport, context_blob: str) -> ThreatModelReport:
    """Drop threat rows that cannot be tied to substrings of the uploaded context."""
    if not (context_blob or "").strip():
        return report
    kept: List[ThreatAnalysisItem] = []
    discarded: List[str] = list(report.discarded_ungrounded)
    for row in report.threat_analysis:
        ok = _threat_row_anchors_context(
            row.erd_reference,
            row.affected_asset,
            row.boundary_name,
            row.threat_title,
            context_blob,
        )
        if ok:
            kept.append(row)
        else:
            ref_preview = (row.erd_reference or "")[:120]
            discarded.append(
                f"Not anchored in session uploads (no matching ERD/doc fragment): {row.threat_title!r}; erd_reference={ref_preview!r}"
            )
    report.threat_analysis = kept
    report.discarded_ungrounded = discarded
    return report


def clear_analysis_cache() -> None:
    _analysis_cache["data"] = None
    _analysis_cache["key"] = None
    _analysis_cache["timestamp"] = 0


class ThreatAnalysisItem(BaseModel):
    boundary_name: str = Field(description="Trust boundary or security perimeter")
    threat_title: str = Field(description="Specific threat name/title")
    affected_asset: str = Field(description="Which asset is impacted")
    control_name: str = Field(description="Security control or mitigation name")
    description: str = Field(description="Detailed threat description and impact")
    severity: str = Field(description="Critical/High/Medium/Low")
    erd_reference: str = Field(
        default="",
        description="Verbatim or near-verbatim phrase from the uploaded ERD/diagram/supporting text this row is about (required for inclusion).",
    )
    grounding_basis: Literal["document_anchored", "diagram_anchored", "inferred_from_context"] = Field(
        default="document_anchored",
        description="document_anchored=ERD/supporting text; diagram_anchored=architecture diagram summary; inferred_from_context=logical extension still requiring erd_reference substring from uploads.",
    )


class AssetItem(BaseModel):
    asset_name: str = Field(description="Process (service) or datastore name")
    description_interface: str = Field(description="Purpose, function, and interfaces")


class ActorItem(BaseModel):
    actor_name: str = Field(description="User type, system, or external entity")
    description_role_auth: str = Field(description="Role description, authentication and authorization details")


class ThreatModelReport(BaseModel):
    scope_summary: str = Field(description="Summary of the threat modeling scope")
    threat_analysis: List[ThreatAnalysisItem] = Field(default_factory=list, description="Threat analysis table")
    assets: List[AssetItem] = Field(default_factory=list, description="Assets table - processes and datastores")
    actors: List[ActorItem] = Field(default_factory=list, description="Users/Actors table")
    key_controls: List[str] = Field(default_factory=list, description="Key security controls identified")
    residual_risk_rating: str = Field(description="Overall residual risk rating")
    assumptions: List[str] = Field(default_factory=list, description="Key assumptions made")
    sources: List[str] = Field(default_factory=list, description="Reference sources used")
    discarded_ungrounded: List[str] = Field(
        default_factory=list,
        description="Threat candidates removed because they could not be tied to text present in the session uploads (reduces hallucinated/generic findings).",
    )


def _truncate_to_tokens(text: str, limit: int, model: str) -> str:
    enc = get_cached_encoding(model if model else "gpt-4o-mini")
    tokens = enc.encode(text)
    if len(tokens) <= limit:
        return text
    return enc.decode(tokens[:limit])


def _bundle_cache_key(analysis_id: Optional[str]) -> str:
    return (analysis_id or "").strip() or "__latest__"


def _get_cached_bundle(
    analysis_id: Optional[str], owner_subject: Optional[str], allow_latest_fallback: bool
) -> Dict[str, Any]:
    global _analysis_cache
    key = f"{owner_subject or 'anon'}::{_bundle_cache_key(analysis_id)}::{allow_latest_fallback}"
    now = time.time()
    if (
        _analysis_cache.get("key") == key
        and _analysis_cache.get("data") is not None
        and (now - _analysis_cache["timestamp"]) < _analysis_cache["ttl"]
    ):
        return _analysis_cache["data"]

    data = get_analysis_context_by_id_or_latest(
        analysis_id if analysis_id and analysis_id.strip() else None,
        owner_subject=owner_subject,
        allow_latest_fallback=allow_latest_fallback,
    )
    _analysis_cache["data"] = data
    _analysis_cache["key"] = key
    _analysis_cache["timestamp"] = now
    return data


def _context_documents_from_bundle(bundle: Dict[str, Any]) -> List[Document]:
    out: List[Document] = []
    for d in bundle.get("documents") or []:
        content = (d.get("content_text") or "").strip()
        if not content:
            continue
        kind = d.get("kind") or "erd_text"
        fn = d.get("filename") or "document"
        if kind in ("erd_text", "supporting_text"):
            doc_type = "erd_text" if kind == "erd_text" else "supporting_text"
        elif kind == "diagram_vision":
            doc_type = "architecture_diagram"
        else:
            doc_type = "supporting_text"
        out.append(
            Document(
                page_content=content,
                metadata={"filename": fn, "doc_type": doc_type},
            )
        )
    return out


def _label_for_doc_type(doc_type: str) -> str:
    if doc_type == "erd_text":
        return "[ERD / PRIMARY DOCUMENT TEXT]"
    if doc_type == "supporting_text":
        return "[SUPPORTING DOCUMENT TEXT]"
    return "[ARCHITECTURE DIAGRAM ANALYSIS]"


def _render_context(docs: List[Document], per_doc_prefix: bool = True) -> List[str]:
    chunks = []
    for i, d in enumerate(docs, 1):
        label = _label_for_doc_type(str(d.metadata.get("doc_type") or "supporting_text"))
        head = f"[{i}] {label} filename={d.metadata.get('filename', 'doc')}"
        content = d.page_content.strip()
        if per_doc_prefix:
            chunks.append(f"{head}\n{content}")
        else:
            chunks.append(content)
    return chunks


def _source_filenames(bundle: Dict[str, Any]) -> List[str]:
    seen: List[str] = []
    for d in bundle.get("documents") or []:
        fn = (d.get("filename") or "").strip()
        if fn and fn not in seen:
            seen.append(fn)
    if not seen:
        if bundle.get("erd_filename"):
            seen.append(str(bundle["erd_filename"]))
        if bundle.get("diagram_filename"):
            seen.append(str(bundle["diagram_filename"]))
    return seen


class QAService:
    def __init__(self, k: int = 6):
        cfg = load_config("config.yaml")
        provider = cfg.get("provider", "openai")
        if provider == "azure_openai":
            if "azure_openai" not in cfg:
                raise ValueError("Azure OpenAI configuration is missing from config.yaml")
            if "api_credentials" not in cfg:
                raise ValueError(
                    "API credentials configuration is missing from config.yaml"
                )
            self.chat_model_name = cfg["azure_openai"].get(
                "chat_deployment", "gpt-4o-mini"
            )
        elif provider == "openai":
            oa = cfg.get("openai", {}) or {}
            self.chat_model_name = oa.get("chat_model", "gpt-4o-mini")
        else:
            raise ValueError(
                f"Unsupported provider '{provider}'. Use 'openai' or 'azure_openai'."
            )
        self.llm = get_llm(cfg, temperature=0.3)
        self.llm_structured = get_llm(cfg, temperature=0.1)

    def _build_messages(self, question: str, contexts: List[str], structured: bool) -> List[dict]:
        system = (
            "You are an expert security consultant and helpful AI assistant. "
            "You answer using only the user-provided context below when it is relevant: "
            "extracted text from uploaded PDF/JSON/TXT files and text summaries of uploaded "
            "architecture diagrams from a vision model. "
            "There is no external document retrieval.\n\n"
            + _CIA_AAA_PLAYBOOK
            + "\nYOUR CAPABILITIES:\n"
            "- Answer questions about their system using the provided context\n"
            "- Provide security analysis and threat modeling aligned with the playbook when asked\n"
            "- Use markdown tables for structured deliverables\n"
            "- Explain technical concepts clearly\n\n"
            "GENERAL GUIDELINES:\n"
            "- Ground answers in the provided context; cite filenames from context headers\n"
            "- If the context is empty or insufficient, say so clearly\n"
        )

        if contexts:
            joined = "\n\n".join(f"[{i + 1}] {c}" for i, c in enumerate(contexts))
            user = (
                "Context (user uploads only):\n\n"
                f"{joined}\n\n"
                f"User question: {question}\n\n"
                "Provide a helpful response using the context when it applies."
            )
        else:
            user = (
                f"User question: {question}\n\n"
                "No document context is loaded. "
                "Say that the user should upload documents and diagrams for system-specific analysis, "
                "or answer generally only if the question does not require their artifacts."
            )

        if structured:
            user += (
                "\n\nReturn the result as valid JSON matching the ThreatModelReport schema "
                "(include erd_reference and grounding_basis on every threat_analysis item).\n"
            )
            user += _STRUCTURED_GROUNDING_RULES

        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def answer(
        self,
        question: str,
        k: int = 6,
        structured: bool = False,
        service: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        analysis_id: Optional[str] = None,
        owner_subject: Optional[str] = None,
    ):
        allow_latest_fallback = not is_production_mode()
        bundle = _get_cached_bundle(
            analysis_id, owner_subject=owner_subject, allow_latest_fallback=allow_latest_fallback
        )
        docs = _context_documents_from_bundle(bundle)

        if service or start_date or end_date:
            pass

        ctx_list = _render_context(docs) if docs else []
        context_budget_tokens = 40000
        n = max(len(ctx_list), 1)
        per_chunk = max(2000, context_budget_tokens // n)
        packed: List[str] = []
        used = 0
        for c in ctx_list:
            t = _truncate_to_tokens(c, per_chunk, self.chat_model_name)
            packed.append(t)
            used += per_chunk
            if used >= context_budget_tokens:
                break

        messages = self._build_messages(question, packed, structured)

        if structured:
            context_blob = "\n\n".join(packed)
            tool_llm = self.llm_structured.with_structured_output(ThreatModelReport)
            result: ThreatModelReport = tool_llm.invoke(messages)
            names = _source_filenames(bundle)
            result.sources = names or result.sources
            result = _enforce_erd_grounding_on_report(result, context_blob)
            return result.model_dump()

        resp = self.llm.invoke(messages)
        sources = _source_filenames(bundle)
        return {"answer": resp.content, "sources": sources}
