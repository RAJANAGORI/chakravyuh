"""Bulk insert embedded documents into pgvector database."""
import json
import sys
from pathlib import Path
from typing import List

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import PGVector
from langchain_core.documents import Document

from chakravyuh.core.config import get_config
from chakravyuh.core.logging import logger


def load_embedded_documents(embedded_docs_dir: Path) -> List[Document]:
    """
    Load embedded documents from JSON files.
    
    Args:
        embedded_docs_dir: Directory containing embedded document JSON files
        
    Returns:
        List of LangChain Document objects
    """
    documents = []
    
    if not embedded_docs_dir.exists():
        logger.warning(f"Embedded docs directory not found: {embedded_docs_dir}")
        return documents
    
    # Find all JSON files recursively
    json_files = list(embedded_docs_dir.rglob("*.json"))
    logger.info(f"Found {len(json_files)} JSON files in {embedded_docs_dir}")
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Handle both single document and list of documents
            if isinstance(data, list):
                for doc_dict in data:
                    if isinstance(doc_dict, dict) and 'page_content' in doc_dict:
                        doc = Document(
                            page_content=doc_dict['page_content'],
                            metadata=doc_dict.get('metadata', {})
                        )
                        documents.append(doc)
            elif isinstance(data, dict) and 'page_content' in data:
                doc = Document(
                    page_content=data['page_content'],
                    metadata=data.get('metadata', {})
                )
                documents.append(doc)
                
        except Exception as e:
            logger.warning(f"Failed to load {json_file}: {e}")
    
    logger.info(f"Loaded {len(documents)} document chunks from JSON files")
    return documents


def insert_documents(documents: List[Document], batch_size: int = 100):
    """
    Insert documents into pgvector database.
    
    Args:
        documents: List of LangChain Document objects
        batch_size: Number of documents to insert per batch
    """
    if not documents:
        logger.warning("No documents to insert")
        return
    
    cfg = get_config()
    
    # Initialize embeddings
    import os
    os.environ["OPENAI_API_KEY"] = cfg.openai.api_key
    embeddings = OpenAIEmbeddings(model=cfg.openai.model)
    
    # Initialize vector store
    conn_string = cfg.database.connection_string
    store = PGVector(
        connection_string=conn_string,
        collection_name=cfg.database.collection,
        embedding_function=embeddings,
    )
    
    # Insert documents in batches
    total_inserted = 0
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        try:
            store.add_documents(batch)
            total_inserted += len(batch)
            logger.info(f"✅ Inserted batch {i//batch_size + 1}: {len(batch)} documents (total: {total_inserted})")
        except Exception as e:
            logger.error(f"Error inserting batch {i//batch_size + 1}: {e}", exc_info=True)
    
    logger.info(f"🎯 Total inserted: {total_inserted} documents")


def main():
    """Main entry point for bulk insertion."""
    # Add project root to path
    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    try:
        cfg = get_config()
        
        # Default to ./embedded_docs if not specified in config
        embedded_docs_dir = Path("./embedded_docs")
        if hasattr(cfg, 'embedded_docs_dir'):
            embedded_docs_dir = Path(cfg.embedded_docs_dir)
        
        logger.info(f"Loading embedded documents from: {embedded_docs_dir}")
        
        # Load documents
        documents = load_embedded_documents(embedded_docs_dir)
        
        if not documents:
            logger.warning("No documents found to insert. Make sure you've run ingestion first.")
            return
        
        # Group by source for logging
        sources = {}
        for doc in documents:
            source = doc.metadata.get('source_hint', doc.metadata.get('filename', 'unknown'))
            sources[source] = sources.get(source, 0) + 1
        
        for source, count in sources.items():
            logger.info(f"  - {source}: {count} chunks")
        
        # Insert into database
        logger.info("Inserting documents into pgvector database...")
        insert_documents(documents)
        
        logger.info("✅ Bulk insertion complete!")
        
    except Exception as e:
        logger.error(f"Error during bulk insertion: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
