# Chakravyuh RAG - Complete Setup Guide

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Configuration](#configuration)
4. [Database Setup](#database-setup)
5. [Data Ingestion](#data-ingestion)
6. [Running the API](#running-the-api)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)
9. [Next Steps](#next-steps)

---

## Prerequisites

### Required Software

- **Python 3.10+** (tested with 3.13.7)
- **Docker & Docker Compose** (for PostgreSQL with pgvector)
- **OpenAI API Key** (for embeddings and LLM)
- **Git** (for cloning the repository)

### System Requirements

- **RAM**: Minimum 4GB (8GB+ recommended)
- **Disk Space**: At least 5GB for data and dependencies
- **Network**: Internet connection for API calls and document scraping

### Verify Prerequisites

```bash
# Check Python version
python3 --version  # Should be 3.10 or higher

# Check Docker
docker --version
docker-compose --version

# Check Git
git --version
```

---

## Initial Setup

### 1. Clone or Navigate to Project

```bash
cd /path/to/chakravyuh
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
# .venv\Scripts\activate
```

**Note**: The virtual environment should be activated for all subsequent steps.

### 3. Install Dependencies

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt

# Install package in development mode (recommended)
pip install -e .
```

### 4. Verify Installation

```bash
# Check key packages
python -c "import langchain; import fastapi; import psycopg2; print('✅ All dependencies installed')"

# Verify package installation
python -c "from chakravyuh.core.config import get_config; print('✅ Chakravyuh package installed')"
```

---

## Configuration

### 1. Create Configuration File

```bash
# Copy example configuration
cp config/config.example.yaml config/config.yaml
```

### 2. Edit Configuration

Open `config/config.yaml` and update the following:

#### OpenAI Configuration (Required)

```yaml
openai:
  api_key: "sk-your-actual-api-key-here"  # Replace with your OpenAI API key
  model: "text-embedding-3-small"          # Embedding model
  chat_model: "gpt-4o-mini"                 # Chat/LLM model
```

**Get your OpenAI API key**: https://platform.openai.com/api-keys

#### Database Configuration

```yaml
database:
  user: "chakravyuh"           # PostgreSQL username
  password: "chakravyuh"       # PostgreSQL password
  host: "localhost"            # Database host
  port: 5432                   # Database port
  dbname: "chakravyuh"         # Database name
  collection: "documents"      # Collection name for vector store
  index_type: "hnsw"           # Index type: "hnsw" or "ivfflat"
  index_params:
    lists: 100                 # Only used for ivfflat
```

**Note**: These should match your Docker PostgreSQL setup (see next section).

#### AWS Documentation Sources (Optional)

```yaml
aws_docs:
  base_dir: "./data/raw"       # Directory for scraped documents
  max_workers: 4               # Number of parallel workers
  services:
    - name: "s3"
      url: "https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html"
    - name: "ec2"
      url: "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html"
```

#### Advanced Configuration (Optional)

```yaml
# Knowledge Graph (Tier 3 features)
knowledge_graph:
  enabled: true
  cache_dir: "./data/knowledge"
  mitre_domain: "enterprise"  # enterprise, mobile, ics
  graph_storage: "memory"      # memory, neo4j, arango

# Security (Tier 5 features)
security:
  adversarial_detection: true
  access_control_enabled: true
  audit_log_dir: "./logs/audit"
  pii_detection: true
  pii_masking: true

# Evaluation (Tier 6 features)
evaluation:
  benchmark_dataset_path: "./data/evaluation/benchmark"
  reviews_storage_path: "./data/evaluation/reviews"
  enable_continuous_evaluation: false
```

### 3. Verify Configuration

```bash
# Test configuration loading
python -c "from chakravyuh.core.config import get_config; cfg = get_config(); print('✅ Configuration loaded successfully')"
```

---

## Database Setup

### 1. Start PostgreSQL with pgvector (Docker)

```bash
# Using docker-compose (recommended)
docker-compose -f infrastructure/docker/docker-compose.yaml up -d

# Or create your own docker-compose.yml in project root:
```

**docker-compose.yml** (if creating manually):
```yaml
version: "3.9"
services:
  db:
    image: ankane/pgvector:latest
    container_name: chakravyuh_pgvector
    restart: always
    environment:
      POSTGRES_USER: chakravyuh
      POSTGRES_PASSWORD: chakravyuh
      POSTGRES_DB: chakravyuh
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

### 2. Initialize Database

```bash
# Run database initialization script
python scripts/setup/init_db.py
```

This script will:
- Create the `vector` extension (pgvector)
- Create the `documents` table
- Create the `doc_hashes` table for version tracking
- Set up proper indexes

### 3. Verify Database Connection

```bash
# Test database connection
python -c "
from chakravyuh.core.database import get_connection
conn = get_connection()
print('✅ Database connection successful')
conn.close()
"
```

### 4. Check Database Status

```bash
# Connect to database
docker exec -it chakravyuh_pgvector psql -U chakravyuh -d chakravyuh

# In psql, run:
\dt                    # List tables
\d documents           # Describe documents table
SELECT COUNT(*) FROM documents;  # Check document count
\q                     # Quit
```

---

## Data Ingestion

### Overview

The data ingestion pipeline consists of three main steps:
1. **Scraping**: Collect documents from sources (AWS, Kubernetes, etc.)
2. **Processing**: Chunk and embed documents
3. **Storage**: Insert into vector database

### Step 1: Scrape Documentation

```bash
# Scrape AWS documentation
python scripts/ingestion/scrape_aws.py

# Or using Makefile
make scrape
```

**What happens:**
- Downloads AWS documentation pages
- Saves as JSON files in `data/raw/` (or configured `base_dir`)
- Organizes by service (s3, ec2, etc.)

**Verify scraping:**
```bash
# Check scraped files
ls -la data/raw/
tree data/raw -L 2
```

### Step 2: Process and Embed Documents

```bash
# Process documents (chunk and embed)
python -m chakravyuh.ingestion.processors.document_processor

# Or using Makefile
make ingest
```

**What happens:**
- Reads scraped JSON files
- Chunks documents using LangChain
- Generates embeddings using OpenAI
- Saves processed documents to `data/processed/`

**Verify processing:**
```bash
# Check processed files
ls -la data/processed/
```

### Step 3: Load ERD Documents (Optional)

If you have ERD (Entity Relationship Diagram) documents:

```bash
# Place ERD files in knowledge/erd/
# Supported formats: PDF, TXT

# Process ERD documents
python -m chakravyuh.ingestion.loaders.erd_loader

# Or using Makefile
make erd
```

### Step 4: Insert into Vector Database

```bash
# Bulk insert into pgvector
python -m chakravyuh.storage.vector.pgvector_store

# Or using Makefile
make insert
```

**What happens:**
- Reads processed documents
- Inserts into PostgreSQL with vector embeddings
- Creates vector indexes for fast similarity search

**Verify insertion:**
```bash
# Check document count
docker exec -it chakravyuh_pgvector psql -U chakravyuh -d chakravyuh -c "SELECT COUNT(*) FROM documents;"
```

**Expected output:**
```
✅ Inserted 128 docs from ./data/processed/s3/...
✅ Inserted 95 docs from ./data/processed/ec2/...
🎯 Total inserted: 223 documents
```

---

## Running the API

### Option 1: Enhanced API (Recommended)

The enhanced API includes all Tier 3/5/6 features (security, knowledge graph, evaluation):

```bash
# Start enhanced API
uvicorn chakravyuh.api.enhanced_api:app --reload --port 8000

# Or using Makefile
make api
```

### Option 2: Legacy API

The original API (simpler, without advanced features):

```bash
# Start legacy API
uvicorn api.search_api:app --reload --port 8000

# Or using Makefile
make api-legacy
```

### Access API Documentation

Once the API is running:

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc
- **OpenAPI JSON**: http://127.0.0.1:8000/openapi.json

### Test API Endpoints

```bash
# Health check
curl http://127.0.0.1:8000/health

# Search documents
curl "http://127.0.0.1:8000/api/v1/ask?q=What%20is%20AWS%20S3&k=5"

# Threat modeling (structured CIA/AAA)
curl -H "X-User-Id: user123" \
  "http://127.0.0.1:8000/api/v1/ask?q=Perform%20a%20CIA%2FAAA%20threat%20model%20for%20S3%20bucket%20security&structured=true"

# System evaluation (requires admin)
curl -X POST -H "X-User-Id: admin" \
  "http://127.0.0.1:8000/api/v1/evaluate"
```

### API Features

**Enhanced API** (`chakravyuh.api.enhanced_api`):
- ✅ Adversarial detection
- ✅ Access control (RBAC)
- ✅ PII masking
- ✅ Knowledge graph integration
- ✅ Audit logging
- ✅ Evaluation endpoints

**Legacy API** (`api.search_api`):
- ✅ Basic search
- ✅ Question answering
- ✅ Structured threat modeling

---

## Testing

### Setup Testing Environment

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Install test dependencies (if not already installed)
pip install pytest pytest-cov pytest-asyncio
```

### Run Tests

```bash
# Run all tests
pytest tests/

# Or using Makefile (auto-activates venv)
make test

# Run with verbose output
pytest tests/ -v

# Run specific test suite
make test-security    # Security tests
make test-kg         # Knowledge graph tests
make test-eval       # Evaluation tests

# Run with coverage report
make test-coverage
# View report: open htmlcov/index.html
```

### Test Results

Expected output:
```
============================= test session starts ==============================
collected 20 items

tests/unit/test_security.py::TestAdversarialDetector::test_prompt_injection_detection PASSED
tests/unit/test_security.py::TestPIIDetector::test_email_detection PASSED
...
============================= 17 passed, 3 failed, 13 warnings in 0.13s ==============================
```

**Note**: Some tests may fail if they require actual implementations. This is expected during development.

---

## Troubleshooting

### Common Issues

#### 1. Module Not Found Errors

**Problem**: `ModuleNotFoundError: No module named 'chakravyuh'`

**Solution**:
```bash
# Install package in development mode
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

#### 2. Database Connection Errors

**Problem**: `psycopg2.OperationalError: could not connect to server`

**Solutions**:
```bash
# Check if Docker container is running
docker ps | grep chakravyuh_pgvector

# Start container if not running
docker-compose -f infrastructure/docker/docker-compose.yaml up -d

# Verify database credentials in config/config.yaml match Docker setup
```

#### 3. OpenAI API Key Errors

**Problem**: `openai.error.AuthenticationError: Invalid API key`

**Solutions**:
```bash
# Verify API key in config/config.yaml
# Ensure key starts with "sk-"
# Check key is valid at https://platform.openai.com/api-keys

# Test API key
python -c "
import os
os.environ['OPENAI_API_KEY'] = 'your-key-here'
from openai import OpenAI
client = OpenAI()
print('✅ API key is valid')
"
```

#### 4. Import Errors in Tests

**Problem**: `ImportError while importing test module`

**Solution**:
```bash
# Ensure package is installed
pip install -e .

# Run tests from project root
cd /path/to/chakravyuh
pytest tests/
```

#### 5. Vector Extension Not Found

**Problem**: `ERROR: extension "vector" does not exist`

**Solution**:
```bash
# Re-run database initialization
python scripts/setup/init_db.py

# Or manually create extension
docker exec -it chakravyuh_pgvector psql -U chakravyuh -d chakravyuh -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

#### 6. Port Already in Use

**Problem**: `Address already in use` when starting API

**Solution**:
```bash
# Find process using port 8000
lsof -i :8000

# Kill process or use different port
uvicorn chakravyuh.api.enhanced_api:app --reload --port 8001
```

---

## Quick Reference

### Essential Commands

```bash
# Setup
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

# Database
docker-compose -f infrastructure/docker/docker-compose.yaml up -d
python scripts/setup/init_db.py

# Data Pipeline
make scrape      # Scrape documents
make ingest      # Process documents
make insert      # Insert into database

# API
make api         # Start enhanced API
make api-legacy  # Start legacy API

# Testing
make test        # Run all tests
make test-coverage  # Run with coverage
```

### Important Files

- **Configuration**: `config/config.yaml`
- **Database Init**: `scripts/setup/init_db.py`
- **Scraping**: `scripts/ingestion/scrape_aws.py`
- **API**: `chakravyuh/api/enhanced_api.py`
- **Makefile**: `Makefile` (for common commands)

### Important Directories

- **Source Code**: `chakravyuh/`
- **Tests**: `tests/`
- **Scripts**: `scripts/`
- **Config**: `config/`
- **Data**: `data/` (gitignored)

---