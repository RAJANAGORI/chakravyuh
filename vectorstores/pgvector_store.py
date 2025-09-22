# vectorstores/pgvector_store.py
import os
import glob
import json
import psycopg2
from langchain_community.vectorstores import PGVector
from langchain_openai import OpenAIEmbeddings
from utils.config_loader import load_config
from langchain_core.documents import Document

def get_vectorstore():
    cfg = load_config("config.yaml")

    # OpenAI setup
    openai_cfg = cfg.get("openai", {})
    os.environ["OPENAI_API_KEY"] = openai_cfg["api_key"]
    embeddings = OpenAIEmbeddings(model=openai_cfg.get("model", "text-embedding-3-small"))

    # DB config
    db_cfg = cfg.get("database", {})
    conn_string = (
        f"postgresql+psycopg2://{db_cfg['user']}:{db_cfg['password']}"
        f"@{db_cfg['host']}:{db_cfg['port']}/{db_cfg['dbname']}"
    )

    # Create index if it doesn't exist
    index_type = db_cfg.get("index_type", "hnsw")
    try:
        conn = psycopg2.connect(
            dbname=db_cfg['dbname'],
            user=db_cfg['user'],
            password=db_cfg['password'],
            host=db_cfg['host'],
            port=db_cfg['port']
        )
        cur = conn.cursor()
        if index_type == "hnsw":
            cur.execute("""
                CREATE INDEX IF NOT EXISTS documents_hnsw_idx
                ON documents
                USING hnsw (embedding vector_l2_ops);
            """)
        elif index_type == "ivfflat":
            lists = db_cfg.get("index_params", {}).get("lists", 100)
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS documents_ivfflat_idx
                ON documents
                USING ivfflat (embedding vector_l2_ops) WITH (lists = {lists});
            """)
        conn.commit()
    finally:
        cur.close()
        conn.close()

    return PGVector(
        connection_string=conn_string,
        collection_name=db_cfg.get("collection", "documents"),
        embedding_function=embeddings,
    )

def bulk_insert(embedded_dir="./embedded_docs"):
    store = get_vectorstore()
    count = 0

    for service in os.listdir(embedded_dir):
        service_dir = os.path.join(embedded_dir, service)
        if not os.path.isdir(service_dir):
            continue

        for file in glob.glob(os.path.join(service_dir, "*.json")):
            with open(file, "r", encoding="utf-8") as f:
                docs = json.load(f)

            # Convert to LangChain Documents
            lc_docs = [
                Document(
                    page_content=d.get("text") or d.get("page_content", ""),
                    metadata=d.get("metadata", {}),
                )
                for d in docs
                if d.get("text") or d.get("page_content")
            ]
            skipped = len(docs) - len(lc_docs)
            if skipped:
                print(f"⚠️ Skipped {skipped} docs in {file} (missing text/page_content)")

            store.add_documents(lc_docs)
            count += len(lc_docs)
            print(f"✅ Inserted {len(lc_docs)} docs from {file}")

    print(f"🎯 Total inserted: {count} documents")

if __name__ == "__main__":
    bulk_insert()