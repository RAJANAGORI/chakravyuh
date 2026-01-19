"""Database connection management."""
import psycopg2
from psycopg2 import pool
from typing import Optional
from contextlib import contextmanager

from chakravyuh.core.config import get_config
from chakravyuh.core.logging import logger


class DatabaseManager:
    """Manages PostgreSQL database connections with connection pooling."""

    def __init__(self):
        """Initialize database manager."""
        self._pool: Optional[pool.ThreadedConnectionPool] = None

    def _create_pool(self):
        """Create connection pool."""
        if self._pool is not None:
            return

        cfg = get_config()
        params = cfg.database.psycopg2_params

        try:
            self._pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                **params,
            )
            logger.info(f"Database connection pool created for {cfg.database.dbname}")
        except Exception as e:
            logger.error(f"Error creating connection pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """
        Get a database connection from the pool.

        Yields:
            Database connection
        """
        if self._pool is None:
            self._create_pool()

        conn = self._pool.getconn()
        try:
            yield conn
        finally:
            self._pool.putconn(conn)

    def close(self):
        """Close all connections in the pool."""
        if self._pool:
            self._pool.closeall()
            logger.info("Database connection pool closed")


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get or create database manager (singleton pattern)."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def get_connection():
    """
    Get a database connection (backward compatibility).

    Returns:
        Database connection
    """
    cfg = get_config()
    params = cfg.database.psycopg2_params
    return psycopg2.connect(**params)
