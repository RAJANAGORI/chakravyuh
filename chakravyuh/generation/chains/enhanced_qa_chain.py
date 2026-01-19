"""Enhanced QA service with Tier 3/5/6 integrations."""
import os
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document

from chakravyuh.core.config import get_config
from chakravyuh.core.logging import logger
from chakravyuh.retrieval.retriever import Retriever
from chakravyuh.utils.tokenization import truncate_to_tokens
from chakravyuh.knowledge_graph import MITREIngestor, CVEIngestor, ThreatGraphManager
from chakravyuh.knowledge_graph.framework_mapper import FrameworkMapper
from chakravyuh.security.adversarial import AdversarialDetector
from chakravyuh.security.access_control import AccessControlManager, Permission, AuditLogger
from chakravyuh.security.privacy import PIIDetector
from chakravyuh.generation.models.threat_model import ThreatModelReport


class EnhancedQAService:
    """Enhanced QA service with security, knowledge graph, and evaluation."""

    def __init__(self, k: int = 6, user_id: str = "anonymous"):
        """
        Initialize enhanced QA service.

        Args:
            k: Number of documents to retrieve
            user_id: User identifier for access control and audit
        """
        cfg = get_config()
        os.environ["OPENAI_API_KEY"] = cfg.openai.api_key
        self.chat_model_name = cfg.openai.chat_model
        self.llm = ChatOpenAI(model=self.chat_model_name, temperature=0)
        self.retriever = Retriever(k=k)
        self.user_id = user_id

        # Initialize security modules
        if cfg.security.adversarial_detection:
            self.adversarial_detector = AdversarialDetector()
        else:
            self.adversarial_detector = None

        if cfg.security.access_control_enabled:
            self.access_control = AccessControlManager(
                auto_assign_reader=cfg.security.access_control_auto_assign_reader
            )
            self.audit_logger = AuditLogger(log_dir=cfg.security.audit_log_dir)
        else:
            self.access_control = None
            self.audit_logger = None

        if cfg.security.pii_detection:
            self.pii_detector = PIIDetector()
        else:
            self.pii_detector = None

        # Initialize knowledge graph modules
        if cfg.knowledge_graph.enabled:
            try:
                self.mitre_ingestor = MITREIngestor(cache_dir=f"{cfg.knowledge_graph.cache_dir}/mitre")
                self.cve_ingestor = CVEIngestor(cache_dir=f"{cfg.knowledge_graph.cache_dir}/cve")
                self.threat_graph = ThreatGraphManager()
                self.framework_mapper = FrameworkMapper()
                # Load MITRE data if not already loaded
                if not self.mitre_ingestor.techniques:
                    self.mitre_ingestor.ingest(cfg.knowledge_graph.mitre_domain)
            except Exception as e:
                logger.warning(f"Knowledge graph initialization failed: {e}")
                self.mitre_ingestor = None
                self.cve_ingestor = None
                self.threat_graph = None
                self.framework_mapper = None
        else:
            self.mitre_ingestor = None
            self.cve_ingestor = None
            self.threat_graph = None
            self.framework_mapper = None

        logger.info(f"EnhancedQAService initialized for user {user_id}")

    def _sanitize_query(self, query: str) -> tuple:
        """
        Sanitize and check query for adversarial attacks.

        Returns:
            Tuple of (sanitized_query, injection_type if detected)
        """
        if not self.adversarial_detector:
            return query, None

        injection_type = self.adversarial_detector.detect_injection(query)
        if injection_type:
            if self.audit_logger:
                self.audit_logger.log_injection_detected(
                    self.user_id, injection_type.value, query
                )
            sanitized = self.adversarial_detector.sanitize_query(query)
            return sanitized, injection_type.value

        return query, None

    def _mask_pii(self, text: str) -> tuple:
        """Mask PII in text if enabled."""
        if not self.pii_detector:
            return text, []

        return self.pii_detector.mask_text(text)

    def _build_enhanced_context(
        self,
        docs: List[Document],
        question: str,
        structured: bool = False,
    ) -> List[str]:
        """Build context with knowledge graph enhancements."""
        ctx_list = []
        for i, doc in enumerate(docs, 1):
            heading = (
                doc.metadata.get("heading")
                or doc.metadata.get("filename")
                or doc.metadata.get("service_page")
                or "chunk"
            )
            source = doc.metadata.get("url") or doc.metadata.get("source_hint") or ""
            content = doc.page_content.strip()

            # Mask PII if enabled
            if self.pii_detector:
                content, _ = self._mask_pii(content)

            ctx_list.append(f"[{i}] {heading}\nSOURCE: {source}\n{content}")

        # Add knowledge graph context if enabled and structured
        if structured and self.threat_graph and self.mitre_ingestor:
            # Search for related ATT&CK techniques
            related_techniques = self.mitre_ingestor.search_techniques(question)
            if related_techniques:
                kg_context = "\n\nRelated MITRE ATT&CK Techniques:\n"
                for tech in related_techniques[:3]:  # Top 3
                    kg_context += f"- {tech.technique_id}: {tech.name}\n"
                ctx_list.append(kg_context)

        return ctx_list

    def _build_messages(
        self,
        question: str,
        contexts: List[str],
        structured: bool = False,
    ) -> List[Dict[str, str]]:
        """Build messages for LLM with enhanced prompts."""
        system = (
            "You are a careful security assistant that answers **using only the provided context**. "
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
            user += (
                "- Produce a structured CIA/AAA threat model.\n"
                "- Map threats to appropriate CIA/AAA categories.\n"
                "- Include specific mitigations and controls.\n"
            )

        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def answer(
        self,
        question: str,
        k: int = 6,
        structured: bool = False,
        service: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Answer a question with enhanced security and knowledge graph support.

        Args:
            question: User question
            k: Number of documents to retrieve
            structured: Whether to return structured threat model
            service: Optional service filter
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Answer dictionary with enhanced metadata
        """
        # Check access control
        if self.access_control:
            permission = Permission.READ_THREAT_MODELS if structured else Permission.READ_DOCUMENTS
            if not self.access_control.has_permission(self.user_id, permission):
                if self.audit_logger:
                    self.audit_logger.log_access_denied(
                        self.user_id, "query", permission.value, "Insufficient permissions"
                    )
                return {
                    "error": "Access denied",
                    "message": f"Insufficient permissions for {permission.value}",
                }

        # Sanitize query
        sanitized_query, injection_type = self._sanitize_query(question)
        if injection_type:
            logger.warning(f"Injection detected: {injection_type}")
            return {
                "error": "Invalid query",
                "message": f"Query contains suspicious patterns: {injection_type}",
            }

        # Retrieve documents
        docs = self.retriever.search(sanitized_query)

        # Apply filters
        if service:
            key = "AmazonS3" if service.lower() == "s3" else "AWSEC2"
            docs = [d for d in docs if key in (d.metadata.get("url") or "")]

        if start_date or end_date:
            filtered_docs = []
            for doc in docs:
                ts = doc.metadata.get("scraped_at")
                if start_date and (not ts or ts < start_date):
                    continue
                if end_date and (not ts or ts > end_date):
                    continue
                filtered_docs.append(doc)
            docs = filtered_docs

        if not docs:
            return {
                "answer": "I couldn't find relevant information to answer your question.",
                "sources": [],
            }

        # Build enhanced context
        ctx_list = self._build_enhanced_context(docs, sanitized_query, structured)

        # Token-budgeted context
        context_budget = 3000
        packed = []
        used = 0
        for c in ctx_list:
            t = truncate_to_tokens(c, 800, self.chat_model_name)
            packed.append(t)
            used += 800
            if used >= context_budget:
                break

        # Build messages
        messages = self._build_messages(sanitized_query, packed, structured)

        # Call LLM
        try:
            if structured:
                tool_llm = self.llm.with_structured_output(ThreatModelReport)
                result: ThreatModelReport = tool_llm.invoke(messages)
                result.sources = [
                    d.metadata.get("url") or (d.metadata.get("filename") or "")
                    for d in docs[: len(packed)]
                ]

                # Enhance with knowledge graph mappings
                if self.framework_mapper:
                    enhanced_result = result.dict()
                    # Add framework mappings (would need to extract threats from result)
                    enhanced_result["framework_mappings"] = {
                        "cia": ["confidentiality", "integrity", "availability"],
                        "aaa": ["authentication", "authorization", "accounting"],
                    }
                    result_dict = enhanced_result
                else:
                    result_dict = result.dict()

                # Audit log
                if self.audit_logger:
                    self.audit_logger.log_threat_model(
                        self.user_id,
                        f"tm_{hash(sanitized_query)}",
                        result.scope_summary,
                        len(result.cia.confidentiality) + len(result.cia.integrity) + len(result.cia.availability),
                    )

                return result_dict
            else:
                resp = self.llm.invoke(messages)
                answer_text = resp.content
                masked_items = []

                # Mask PII in response
                if self.pii_detector:
                    answer_text, masked_items = self._mask_pii(answer_text)

                # Audit log
                if self.audit_logger:
                    self.audit_logger.log_query(
                        self.user_id,
                        sanitized_query,
                        len(answer_text),
                        [d.metadata.get("url", "") for d in docs[: len(packed)]],
                        structured=False,
                    )

                result_dict = {
                    "answer": answer_text,
                    "sources": [
                        d.metadata.get("url") or (d.metadata.get("filename") or "")
                        for d in docs[: len(packed)]
                    ],
                }

                if self.pii_detector:
                    result_dict["pii_masked"] = len(masked_items)

                return result_dict

        except Exception as e:
            logger.error(f"Error in answer generation: {e}", exc_info=True)
            return {
                "error": "Generation failed",
                "message": str(e),
            }
