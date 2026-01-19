"""Setup configuration for Chakravyuh RAG."""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="chakravyuh-rag",
    version="1.0.0",
    author="Chakravyuh Team",
    description="Enterprise-grade RAG system for security threat modeling",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/chakravyuh",
    packages=find_packages(exclude=["tests", "scripts", "docs"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Security",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "chakravyuh-api=chakravyuh.api.app:app",
            "chakravyuh-scrape=scripts.ingestion.scrape_aws:main",
            "chakravyuh-ingest=scripts.ingestion.ingest_documents:main",
        ],
    },
)
