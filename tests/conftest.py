"""Pytest configuration and fixtures."""
import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp)


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        "openai": {
            "api_key": "test-key",
            "model": "text-embedding-3-small",
            "chat_model": "gpt-4o-mini",
        },
        "database": {
            "user": "test",
            "password": "test",
            "host": "localhost",
            "port": 5432,
            "dbname": "test",
        },
        "aws_docs": {
            "base_dir": "./test_data",
            "max_workers": 2,
            "services": [],
        },
    }
