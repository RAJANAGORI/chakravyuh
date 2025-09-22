# lc_ingestion.py
import os
import glob
from langchain_community.document_loaders import JSONLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from utils.config_loader import load_config
from langsmith import Client

def main():
    cfg = load_config("config.yaml")

    # Setup LangSmith observability
    if "langsmith" in cfg:
        os.environ["LANGSMITH_API_KEY"] = cfg["langsmith"]["api_key"]
        os.environ["LANGSMITH_PROJECT"] = cfg["langsmith"]["project"]
        os.environ["LANGSMITH_ENDPOINT"] = cfg["langsmith"].get("endpoint", "https://api.smith.langchain.com")

    # Setup embeddings
    openai_cfg = cfg.get("openai", {})
    os.environ["OPENAI_API_KEY"] = openai_cfg.get("api_key")
    model = openai_cfg.get("model", "text-embedding-3-small")

    embeddings = OpenAIEmbeddings(model=model)

    # Text splitter
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

    input_dir = cfg["aws_docs"]["base_dir"]
    output_dir = "./embedded_docs"
    os.makedirs(output_dir, exist_ok=True)

    for service in os.listdir(input_dir):
        service_dir = os.path.join(input_dir, service)
        if not os.path.isdir(service_dir):
            continue

        out_service_dir = os.path.join(output_dir, service)
        os.makedirs(out_service_dir, exist_ok=True)

        for file in glob.glob(os.path.join(service_dir, "*.json")):
            print(f"📄 Processing {file}")

            loader = JSONLoader(
                file_path=file,
                jq_schema='.[] | {text: .text, metadata: .metadata}',
                text_content=False
            )
            docs = loader.load()
            docs_split = splitter.split_documents(docs)

            # Add embeddings
            for d in docs_split:
                d.metadata["embedding"] = embeddings.embed_query(d.page_content)

            # Save output
            base = os.path.basename(file).replace(".json", "_lc.json")
            out_file = os.path.join(out_service_dir, base)

            with open(out_file, "w", encoding="utf-8") as f:
                import json
                json.dump([d.dict() for d in docs_split], f, indent=2)

            print(f"✅ Saved {len(docs_split)} chunks with embeddings → {out_file}")

if __name__ == "__main__":
    main()