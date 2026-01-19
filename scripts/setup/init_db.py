"""Database initialization script."""
import sys
import os
from pathlib import Path

# Add project root to path for direct script execution
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from chakravyuh.core.config import get_config
from chakravyuh.core.database import get_connection, get_db_manager
from chakravyuh.core.logging import logger


def init_db():
    """Initialize database with required tables and extensions."""
    try:
        cfg = get_config()
        
        commands = [
            # Enable pgvector extension
            "CREATE EXTENSION IF NOT EXISTS vector;",
            
            # Main documents table
            """
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                content TEXT,
                metadata JSONB,
                embedding VECTOR(1536)
            );
            """,
            
            # Ensure metadata column is JSONB
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'documents' 
                    AND column_name = 'metadata' 
                    AND data_type != 'jsonb'
                ) THEN
                    ALTER TABLE documents
                    ALTER COLUMN metadata TYPE JSONB
                    USING metadata::JSONB;
                END IF;
            END $$;
            """,
            
            # Hash tracking table
            """
            CREATE TABLE IF NOT EXISTS doc_hashes (
                id SERIAL PRIMARY KEY,
                doc_name TEXT NOT NULL,
                service TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW(),
                UNIQUE (doc_name, service)
            );
            """,
        ]

        # Use direct connection for initialization
        conn = get_connection()
        try:
            cur = conn.cursor()
            for cmd in commands:
                try:
                    cur.execute(cmd)
                    logger.debug("Executed SQL command")
                except Exception as e:
                    logger.warning(f"Skipped command due to error: {e}")
            conn.commit()
            cur.close()
        finally:
            conn.close()

        logger.info("✅ Database initialized with pgvector, documents, and doc_hashes tables")

    except Exception as e:
        logger.error(f"Error initializing database: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    init_db()
