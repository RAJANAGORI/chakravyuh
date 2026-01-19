"""Loader for ERD (Entity Relationship Diagram) documents."""
import os
from pathlib import Path
from typing import List
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

try:
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

from chakravyuh.core.config import get_config
from chakravyuh.core.logging import logger


class ERDLoader:
    """Loads and processes ERD documents (PDF, TXT)."""

    def __init__(self, input_dir: str = "./knowledge/erd"):
        """
        Initialize ERD loader.

        Args:
            input_dir: Directory containing ERD files
        """
        self.input_dir = Path(input_dir)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
        )

    def load_erd_files(self) -> List[Document]:
        """
        Load ERD files from directory.

        Returns:
            List of LangChain Document objects
        """
        documents = []

        if not self.input_dir.exists():
            logger.warning(f"ERD directory not found: {self.input_dir}")
            return documents

        # Load text files
        for txt_file in self.input_dir.glob("*.txt"):
            try:
                with open(txt_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    chunks = self.text_splitter.split_text(content)
                    for chunk in chunks:
                        documents.append(
                            Document(
                                page_content=chunk,
                                metadata={"source": str(txt_file), "type": "erd"},
                            )
                        )
                logger.info(f"Loaded {txt_file.name}")
            except Exception as e:
                logger.warning(f"Failed to load {txt_file}: {e}")

        # Load PDF files
        if PDF_SUPPORT:
            for pdf_file in self.input_dir.glob("*.pdf"):
                try:
                    doc = fitz.open(pdf_file)
                    content_parts = []
                    for page_num in range(len(doc)):
                        page = doc[page_num]
                        text = page.get_text()
                        if text.strip():
                            content_parts.append(text)
                    doc.close()
                    
                    if content_parts:
                        full_content = "\n\n".join(content_parts)
                        chunks = self.text_splitter.split_text(full_content)
                        for chunk in chunks:
                            documents.append(
                                Document(
                                    page_content=chunk,
                                    metadata={"source": str(pdf_file), "type": "erd", "format": "pdf"},
                                )
                            )
                        logger.info(f"Loaded {pdf_file.name} ({len(chunks)} chunks)")
                except Exception as e:
                    logger.warning(f"Failed to load {pdf_file}: {e}")
        else:
            pdf_files = list(self.input_dir.glob("*.pdf"))
            if pdf_files:
                logger.warning(
                    f"PDF files found but PyMuPDF not available. "
                    f"Install with: pip install PyMuPDF. "
                    f"Found {len(pdf_files)} PDF file(s): {[f.name for f in pdf_files]}"
                )

        logger.info(f"Loaded {len(documents)} ERD document chunks")
        return documents


def main():
    """Main entry point for ERD loading."""
    import sys
    from pathlib import Path

    # Add project root to path
    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root))

    try:
        loader = ERDLoader()
        documents = loader.load_erd_files()

        logger.info(f"✅ Loaded {len(documents)} ERD document chunks")

    except Exception as e:
        logger.error(f"Error loading ERD documents: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
