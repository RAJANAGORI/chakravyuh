"""Document processor for chunking and embedding scraped documents."""
import json
import os
from pathlib import Path
from typing import List, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

from chakravyuh.core.config import get_config
from chakravyuh.core.logging import logger


class DocumentProcessor:
    """Processes scraped documents: chunks and generates embeddings."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        output_dir: str = "./data/processed",
    ):
        """
        Initialize document processor.

        Args:
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            output_dir: Directory to save processed documents
        """
        cfg = get_config()
        os.environ["OPENAI_API_KEY"] = cfg.openai.api_key

        self.embeddings = OpenAIEmbeddings(model=cfg.openai.model)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_scraped_documents(self, input_dir: str) -> List[Dict[str, Any]]:
        """
        Load scraped JSON documents from directory.

        Args:
            input_dir: Directory containing scraped JSON files

        Returns:
            List of document dictionaries
        """
        input_path = Path(input_dir)
        documents = []

        for json_file in input_path.rglob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Handle both dict and list formats
                    if isinstance(data, list):
                        documents.extend(data)
                    elif isinstance(data, dict):
                        documents.append(data)
            except Exception as e:
                logger.warning(f"Failed to load {json_file}: {e}")

        logger.info(f"Loaded {len(documents)} documents from {input_dir}")
        return documents

    def process_document(self, doc_data: Dict[str, Any]) -> List[Document]:
        """
        Process a single document: chunk and create LangChain Documents.

        Args:
            doc_data: Document data from scraped JSON

        Returns:
            List of LangChain Document objects
        """
        content = doc_data.get("content", "")
        if not content:
            return []

        # Split into chunks
        chunks = self.text_splitter.split_text(content)

        # Create LangChain Documents
        langchain_docs = []
        for i, chunk in enumerate(chunks):
            metadata = doc_data.get("metadata", {}).copy()
            metadata.update({
                "chunk_index": i,
                "total_chunks": len(chunks),
                "source_file": doc_data.get("url", ""),
            })

            langchain_docs.append(Document(page_content=chunk, metadata=metadata))

        return langchain_docs

    def save_processed_documents(
        self,
        documents: List[Document],
        service_name: str,
        source_url: str = "",
    ):
        """
        Save processed documents to JSON files.

        Args:
            documents: List of LangChain Document objects
            service_name: Service name (e.g., "s3", "ec2")
            source_url: Original source URL
        """
        service_dir = self.output_dir / service_name
        service_dir.mkdir(parents=True, exist_ok=True)

        # Create filename from source URL
        if source_url:
            url_path = source_url.replace("https://", "").replace("http://", "")
            url_path = url_path.replace("/", "_").replace(":", "_")
            filename = f"{url_path}_lc.json"
        else:
            filename = f"processed_{len(documents)}_lc.json"

        filepath = service_dir / filename

        # Convert to serializable format
        output_data = {
            "source_url": source_url,
            "service": service_name,
            "chunks": [
                {
                    "page_content": doc.page_content,
                    "metadata": doc.metadata,
                }
                for doc in documents
            ],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(documents)} chunks to {filepath}")

    def process_directory(self, input_dir: str):
        """
        Process all documents in a directory.

        Args:
            input_dir: Directory containing scraped JSON files
        """
        logger.info(f"Processing documents from {input_dir}")

        # Load all scraped documents
        scraped_docs = self.load_scraped_documents(input_dir)

        total_chunks = 0
        for doc_data in scraped_docs:
            # Ensure doc_data is a dict
            if not isinstance(doc_data, dict):
                logger.warning(f"Skipping non-dict document: {type(doc_data)}")
                continue

            # Extract service name from metadata or directory structure
            metadata = doc_data.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}

            service_name = metadata.get("service", "unknown")
            source_url = doc_data.get("url", "")

            # Process document
            langchain_docs = self.process_document(doc_data)

            if langchain_docs:
                # Save processed documents
                self.save_processed_documents(langchain_docs, service_name, source_url)
                total_chunks += len(langchain_docs)

        logger.info(f"✅ Processed {len(scraped_docs)} documents into {total_chunks} chunks")


def main():
    """Main entry point for document processing."""
    import sys
    from pathlib import Path

    # Add project root to path
    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root))

    try:
        cfg = get_config()

        # Process AWS docs
        input_dir = cfg.aws_docs.base_dir
        processor = DocumentProcessor()

        processor.process_directory(input_dir)

        logger.info("✅ Document processing complete")

    except Exception as e:
        logger.error(f"Error in document processing: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
