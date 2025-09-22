import os
from utils.config_loader import load_config
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import PGVector

class Retriever:
    def __init__(self, k=5, filters=None):
        cfg = load_config("config.yaml")

        # OpenAI API key
        openai_cfg = cfg["openai"]
        os.environ["OPENAI_API_KEY"] = openai_cfg["api_key"]

        self.embeddings = OpenAIEmbeddings(
            model=openai_cfg.get("model", "text-embedding-3-small")
        )

        # DB connection
        db_cfg = cfg["database"]
        conn_string = (
            f"postgresql+psycopg2://{db_cfg['user']}:{db_cfg['password']}"
            f"@{db_cfg['host']}:{db_cfg['port']}/{db_cfg['dbname']}"
        )

        self.store = PGVector(
            connection_string=conn_string,
            collection_name=db_cfg.get("collection", "documents"),
            embedding_function=self.embeddings,
        )

        self.retriever = self.store.as_retriever(search_kwargs={"k": k})
        self.filters = filters or {}

    def search(self, query: str):
        docs = self.retriever.get_relevant_documents(query)
        # Apply filters if any
        if self.filters:
            docs = [
                d for d in docs
                if all(d.metadata.get(fk) == fv for fk, fv in self.filters.items())
            ]
        return docs