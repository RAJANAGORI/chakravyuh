"""Centralized configuration management with type safety."""
import os
import yaml
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class OpenAIConfig:
    """OpenAI API configuration."""
    api_key: str
    model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"

    def __post_init__(self):
        """Set environment variable for OpenAI API key."""
        os.environ["OPENAI_API_KEY"] = self.api_key


@dataclass
class LangSmithConfig:
    """LangSmith observability configuration."""
    api_key: str
    project: str = "chakravyuh-rag"
    endpoint: str = "https://api.smith.langchain.com"

    def __post_init__(self):
        """Set environment variables for LangSmith."""
        os.environ["LANGSMITH_API_KEY"] = self.api_key
        os.environ["LANGSMITH_PROJECT"] = self.project
        os.environ["LANGSMITH_ENDPOINT"] = self.endpoint


@dataclass
class ServiceConfig:
    """Service/documentation source configuration."""
    name: str
    url: str


@dataclass
class AWSDocsConfig:
    """AWS documentation scraping configuration."""
    base_dir: str = "./data/raw"
    max_workers: int = 4
    services: List[ServiceConfig] = field(default_factory=list)


@dataclass
class DatabaseConfig:
    """Database configuration."""
    user: str
    password: str
    host: str = "localhost"
    port: int = 5432
    dbname: str = "chakravyuh"
    collection: str = "documents"
    index_type: str = "hnsw"  # options: hnsw, ivfflat
    index_params: Dict[str, Any] = field(default_factory=lambda: {"lists": 100})

    @property
    def connection_string(self) -> str:
        """Generate PostgreSQL connection string."""
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.dbname}"
        )

    @property
    def psycopg2_params(self) -> Dict[str, Any]:
        """Get psycopg2 connection parameters."""
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.dbname,
            "user": self.user,
            "password": self.password,
        }


@dataclass
class KnowledgeGraphConfig:
    """Knowledge graph configuration."""
    enabled: bool = True
    cache_dir: str = "./data/knowledge"
    mitre_domain: str = "enterprise"  # enterprise, mobile, ics
    graph_storage: str = "memory"  # memory, neo4j, arango
    neo4j_uri: Optional[str] = None
    neo4j_user: Optional[str] = None
    neo4j_password: Optional[str] = None


@dataclass
class SecurityConfig:
    """Security configuration."""
    adversarial_detection: bool = True
    access_control_enabled: bool = True
    access_control_auto_assign_reader: bool = False  # Don't auto-assign roles by default
    audit_log_dir: str = "./logs/audit"
    pii_detection: bool = True
    pii_masking: bool = True


@dataclass
class EvaluationConfig:
    """Evaluation configuration."""
    benchmark_dataset_path: str = "./data/evaluation/benchmark"
    reviews_storage_path: str = "./data/evaluation/reviews"
    enable_continuous_evaluation: bool = False


@dataclass
class AppConfig:
    """Main application configuration."""
    openai: OpenAIConfig
    database: DatabaseConfig
    aws_docs: AWSDocsConfig
    langsmith: Optional[LangSmithConfig] = None
    knowledge_graph: KnowledgeGraphConfig = field(default_factory=KnowledgeGraphConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)
    config_path: str = "config/config.yaml"

    @classmethod
    def from_file(cls, config_path: str = "config/config.yaml") -> "AppConfig":
        """Load configuration from YAML file."""
        config_path = Path(config_path)
        if not config_path.exists():
            # Try root directory for backward compatibility
            alt_path = Path("config.yaml")
            if alt_path.exists():
                config_path = alt_path
            else:
                raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Parse OpenAI config
        openai_data = data.get("openai", {})
        if "api_key" not in openai_data:
            raise ValueError("OpenAI API key is required in config.yaml")
        openai_config = OpenAIConfig(
            api_key=openai_data["api_key"],
            model=openai_data.get("model", "text-embedding-3-small"),
            chat_model=openai_data.get("chat_model", "gpt-4o-mini"),
        )

        # Parse database config
        db_data = data.get("database", {})
        if not all(k in db_data for k in ["user", "password", "dbname"]):
            raise ValueError("Database user, password, and dbname are required")
        db_config = DatabaseConfig(
            user=db_data["user"],
            password=db_data["password"],
            host=db_data.get("host", "localhost"),
            port=db_data.get("port", 5432),
            dbname=db_data["dbname"],
            collection=db_data.get("collection", "documents"),
            index_type=db_data.get("index_type", "hnsw"),
            index_params=db_data.get("index_params", {"lists": 100}),
        )

        # Parse AWS docs config
        aws_data = data.get("aws_docs", {})
        services = [
            ServiceConfig(name=s["name"], url=s["url"])
            for s in aws_data.get("services", [])
        ]
        aws_config = AWSDocsConfig(
            base_dir=aws_data.get("base_dir", "./data/raw"),
            max_workers=aws_data.get("max_workers", 4),
            services=services,
        )

        # Parse LangSmith config (optional)
        langsmith_config = None
        if "langsmith" in data and data["langsmith"].get("api_key"):
            ls_data = data["langsmith"]
            langsmith_config = LangSmithConfig(
                api_key=ls_data["api_key"],
                project=ls_data.get("project", "chakravyuh-rag"),
                endpoint=ls_data.get("endpoint", "https://api.smith.langchain.com"),
            )

        # Parse knowledge graph config
        kg_data = data.get("knowledge_graph", {})
        kg_config = KnowledgeGraphConfig(
            enabled=kg_data.get("enabled", True),
            cache_dir=kg_data.get("cache_dir", "./data/knowledge"),
            mitre_domain=kg_data.get("mitre_domain", "enterprise"),
            graph_storage=kg_data.get("graph_storage", "memory"),
            neo4j_uri=kg_data.get("neo4j_uri"),
            neo4j_user=kg_data.get("neo4j_user"),
            neo4j_password=kg_data.get("neo4j_password"),
        )

        # Parse security config
        security_data = data.get("security", {})
        security_config = SecurityConfig(
            adversarial_detection=security_data.get("adversarial_detection", True),
            access_control_enabled=security_data.get("access_control_enabled", True),
            access_control_auto_assign_reader=security_data.get("access_control_auto_assign_reader", False),
            audit_log_dir=security_data.get("audit_log_dir", "./logs/audit"),
            pii_detection=security_data.get("pii_detection", True),
            pii_masking=security_data.get("pii_masking", True),
        )

        # Parse evaluation config
        eval_data = data.get("evaluation", {})
        eval_config = EvaluationConfig(
            benchmark_dataset_path=eval_data.get("benchmark_dataset_path", "./data/evaluation/benchmark"),
            reviews_storage_path=eval_data.get("reviews_storage_path", "./data/evaluation/reviews"),
            enable_continuous_evaluation=eval_data.get("enable_continuous_evaluation", False),
        )

        return cls(
            openai=openai_config,
            database=db_config,
            aws_docs=aws_config,
            langsmith=langsmith_config,
            knowledge_graph=kg_config,
            security=security_config,
            evaluation=eval_config,
            config_path=str(config_path),
        )


# Global config instance (lazy loaded)
_config: Optional[AppConfig] = None


def get_config(config_path: str = "config/config.yaml") -> AppConfig:
    """Get or load application configuration (singleton pattern)."""
    global _config
    if _config is None:
        _config = AppConfig.from_file(config_path)
    return _config


def reload_config(config_path: str = "config/config.yaml") -> AppConfig:
    """Reload configuration from file."""
    global _config
    _config = AppConfig.from_file(config_path)
    return _config
