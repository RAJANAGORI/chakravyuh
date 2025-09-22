# ingestion/erd_ingestion.py
import os, glob, json
import fitz  # PyMuPDF
from datetime import datetime
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from utils.config_loader import load_config

INPUT_DIR = "./knowledge/erd"          # put your ERD PDFs/TXT here
OUTPUT_DIR = "./embedded_docs/erd"     # aligned with Phase 3 bulk insert
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_text_from_pdf(path: str) -> str:
    doc = fitz.open(path)
    texts = []
    for page in doc:
        texts.append(page.get_text("text"))
    doc.close()
    return "\n".join(texts)

def read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def main():
    cfg = load_config("config.yaml")
    os.environ["OPENAI_API_KEY"] = cfg["openai"]["api_key"]
    model = cfg["openai"].get("model", "text-embedding-3-small")

    splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
    embedder = OpenAIEmbeddings(model=model)

    files = glob.glob(os.path.join(INPUT_DIR, "*.pdf")) + glob.glob(os.path.join(INPUT_DIR, "*.txt"))
    for fpath in files:
        base = os.path.splitext(os.path.basename(fpath))[0]
        if fpath.lower().endswith(".pdf"):
            text = extract_text_from_pdf(fpath)
        else:
            text = read_text_file(fpath)

        chunks = splitter.split_text(text)
        now = datetime.utcnow().isoformat()

        docs = []
        for i, ch in enumerate(chunks):
            docs.append({
                "page_content": ch,
                "metadata": {
                    "doc_type": "erd",
                    "filename": os.path.basename(fpath),
                    "page_chunk": i,
                    "ingested_at": now,
                    "source_hint": "ERD"
                }
            })

        out = os.path.join(OUTPUT_DIR, f"{base}_lc.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(docs, f, indent=2, ensure_ascii=False)

        print(f"✅ {os.path.basename(fpath)} → {len(docs)} chunks → {out}")

if __name__ == "__main__":
    main()