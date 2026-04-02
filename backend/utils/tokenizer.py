# utils/tokenizer.py
import tiktoken
from functools import lru_cache

@lru_cache(maxsize=10)
def get_cached_encoding(model: str):
    """
    Cache tiktoken encoders for reuse.
    Performance improvement: ~10-20ms saved per call after first use.
    """
    return tiktoken.encoding_for_model(model)

def split_text_by_tokens(text, model="gpt-3.5-turbo", chunk_size=500, overlap=50):
    enc = get_cached_encoding(model)
    tokens = enc.encode(text)

    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = enc.decode(chunk_tokens)
        chunks.append(chunk_text)
        start += chunk_size - overlap
    return chunks