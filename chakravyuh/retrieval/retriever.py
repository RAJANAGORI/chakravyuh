"""Document retriever with vector similarity search."""
import os
from typing import List, Optional, Dict, Any

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import PGVector
from langchain_core.documents import Document

from chakravyuh.core.config import get_config
from chakravyuh.core.logging import logger


class Retriever:
    """Retriever for semantic search over vector store."""

    def __init__(self, k: int = 5, filters: Optional[Dict[str, Any]] = None):
        """
        Initialize retriever.

        Args:
            k: Number of documents to retrieve
            filters: Optional metadata filters
        """
        cfg = get_config()

        # OpenAI embeddings
        os.environ["OPENAI_API_KEY"] = cfg.openai.api_key
        self.embeddings = OpenAIEmbeddings(model=cfg.openai.model)

        # Database connection
        conn_string = cfg.database.connection_string

        self.store = PGVector(
            connection_string=conn_string,
            collection_name=cfg.database.collection,
            embedding_function=self.embeddings,
        )

        self.retriever = self.store.as_retriever(search_kwargs={"k": k})
        self.filters = filters or {}
        self.k = k

        logger.debug(f"Retriever initialized with k={k}")

    def search(self, query: str) -> List[Document]:
        """
        Search for relevant documents.

        Args:
            query: Search query

        Returns:
            List of relevant documents
        """
        try:
            docs = self.retriever.get_relevant_documents(query)

            # Apply filters if any
            if self.filters:
                docs = [
                    d
                    for d in docs
                    if all(d.metadata.get(fk) == fv for fk, fv in self.filters.items())
                ]

            logger.debug(f"Retrieved {len(docs)} documents for query: {query[:50]}...")
            return docs

        except Exception as e:
            logger.error(f"Error in retrieval: {e}", exc_info=True)
            return []
