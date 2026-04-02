import base64, os, requests, sys
from functools import lru_cache
from typing import Optional
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings, ChatOpenAI, OpenAIEmbeddings 
from langchain_ollama import OllamaEmbeddings

# Cache for LLM instances (keyed by provider + temperature)
_llm_cache = {}
# Cache for embeddings instances (keyed by provider)
_embeddings_cache = {}

def get_bridgeit_token(cfg):
    """OAuth client credentials: env overrides YAML (no secrets in repo)."""
    creds = cfg.get("api_credentials", {}) or {}
    client_id = (os.environ.get("TM_API_CLIENT_ID") or "").strip() or creds.get("client_id")
    client_secret = (
        (os.environ.get("TM_API_CLIENT_SECRET") or "").strip() or creds.get("client_secret")
    )
    token_url = (os.environ.get("TM_TOKEN_URL") or "").strip() or creds.get("token_url")

    if not client_id or not client_secret or not token_url:
        print(
            "[!] Error: Set TM_API_CLIENT_ID, TM_API_CLIENT_SECRET, TM_TOKEN_URL "
            "or provide api_credentials in config.yaml"
        )
        sys.exit(1)

    payload = "grant_type=client_credentials"
    value = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("utf-8")
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {value}",
    }

    resp = requests.post(token_url, headers=headers, data=payload, timeout=60)
    if resp.status_code != 200:
        print(f"[!] Token fetch failed: {resp.status_code} {resp.text}")
        sys.exit(1)

    return resp.json()["access_token"]

def get_llm(cfg, temperature=0):
    """
    Get cached LLM instance. Creates new instance only if not in cache.
    Performance improvement: ~200-500ms saved per call after first initialization.
    """
    provider = cfg.get("provider", "openai")
    cache_key = f"{provider}_temp{temperature}"
    
    # Return cached instance if available
    if cache_key in _llm_cache:
        return _llm_cache[cache_key]

    # Create new instance based on provider
    if provider == "azure_openai":
        if "azure_openai" not in cfg or "api_credentials" not in cfg:
            raise ValueError("Azure OpenAI selected but config is missing required sections")

        creds = cfg.get("api_credentials", {}) or {}
        app_key = (os.environ.get("TM_API_APP_KEY") or "").strip() or creds.get("app_key")
        user_id = (os.environ.get("TM_API_USER_ID") or "").strip() or creds.get("user_id")
        token = get_bridgeit_token(cfg)

        llm = AzureChatOpenAI(
            azure_endpoint=cfg["azure_openai"]["endpoint"],
            deployment_name=cfg["azure_openai"]["chat_deployment"],
            openai_api_version=cfg["azure_openai"]["api_version"],
            api_key=token,
            temperature=temperature,
            model_kwargs={
                "user": f'{{"appkey": "{app_key or ""}", "user": "{user_id or ""}"}}'
            },
        )

    elif provider == "openai":
        oa = cfg.get("openai", {}) or {}
        api_key = (os.environ.get("OPENAI_API_KEY") or "").strip() or oa.get("api_key")
        if not api_key:
            raise ValueError("OpenAI selected: set OPENAI_API_KEY or openai.api_key in config.yaml")
        llm = ChatOpenAI(
            model=oa.get("chat_model", "gpt-4o-mini"),
            openai_api_key=api_key,
            temperature=temperature,
        )

    else:
        raise ValueError(f"Unknown provider: {provider}")
    
    # Cache and return
    _llm_cache[cache_key] = llm
    print(f"⚡ LLM instance cached ({provider}, temp={temperature})")
    return llm


def get_embeddings(cfg):
    """
    Get cached embeddings instance based on embedding_provider in config.
    Supports: openai, azure_openai, ollama
    Falls back to use_ollama_for_embeddings for backward compatibility.
    
    Performance improvement: ~200-500ms saved per call after first initialization.
    """
    # Check for new embedding_provider config (preferred)
    embedding_provider = cfg.get("embedding_provider")
    
    # Backward compatibility: use old flag if embedding_provider not set
    if not embedding_provider:
        if cfg.get("use_ollama_for_embeddings", False):
            embedding_provider = "ollama"
        else:
            embedding_provider = cfg.get("provider", "openai")
    
    # Return cached instance if available
    if embedding_provider in _embeddings_cache:
        return _embeddings_cache[embedding_provider]
    
    # Create new embeddings instance
    embeddings = None
    
    # Ollama embeddings (local, free)
    if embedding_provider == "ollama":
        if "ollama" not in cfg:
            raise ValueError("Ollama selected for embeddings but 'ollama' section missing in config.yaml")
        
        ollama_cfg = cfg["ollama"]
        # Env override for Docker: OLLAMA_BASE_URL=http://ollama:11434
        base_url = os.environ.get("OLLAMA_BASE_URL") or ollama_cfg.get("base_url", "http://localhost:11434")
        embeddings = OllamaEmbeddings(
            model=ollama_cfg.get("model", "embeddinggemma"),
            base_url=base_url,
        )
    
    # Azure OpenAI embeddings
    elif embedding_provider == "azure_openai":
        if "azure_openai" not in cfg or "api_credentials" not in cfg:
            raise ValueError("Azure OpenAI selected for embeddings but config sections are missing")
        
        azure_cfg = cfg["azure_openai"]
        token = get_bridgeit_token(cfg)
        
        # Check if embedding_deployment is configured
        if "embedding_deployment" not in azure_cfg:
            raise ValueError("Azure OpenAI embeddings require 'embedding_deployment' in config.yaml")
        
        embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=azure_cfg["endpoint"],
            deployment=azure_cfg["embedding_deployment"],
            openai_api_version=azure_cfg["api_version"],
            api_key=token,
        )
    
    # OpenAI embeddings
    elif embedding_provider == "openai":
        if "openai" not in cfg:
            raise ValueError("OpenAI selected for embeddings but 'openai' section missing in config.yaml")
        
        openai_cfg = cfg["openai"]
        oa_key = (os.environ.get("OPENAI_API_KEY") or "").strip() or openai_cfg.get("api_key")
        if not oa_key:
            raise ValueError("OpenAI embeddings: set OPENAI_API_KEY or openai.api_key in config.yaml")
        embeddings = OpenAIEmbeddings(
            model=openai_cfg.get("embedding_model", "text-embedding-3-large"),
            openai_api_key=oa_key,
        )
    
    else:
        raise ValueError(f"Unsupported embedding_provider: {embedding_provider}. Use: openai, azure_openai, or ollama")
    
    # Cache and return
    _embeddings_cache[embedding_provider] = embeddings
    print(f"⚡ Embeddings instance cached ({embedding_provider})")
    return embeddings


def clear_llm_cache():
    """Clear all LLM caches. Useful for testing or config changes."""
    global _llm_cache, _embeddings_cache
    _llm_cache = {}
    _embeddings_cache = {}
    print("🔄 LLM and embeddings caches cleared")