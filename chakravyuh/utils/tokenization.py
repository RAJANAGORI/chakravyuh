"""Tokenization utilities."""
import tiktoken
from typing import Optional


def truncate_to_tokens(text: str, limit: int, model: str = "gpt-4o-mini") -> str:
    """
    Truncate text to token limit.

    Args:
        text: Text to truncate
        limit: Maximum number of tokens
        model: Model name for encoding

    Returns:
        Truncated text
    """
    enc = tiktoken.encoding_for_model(model if model else "gpt-4o-mini")
    tokens = enc.encode(text)
    if len(tokens) <= limit:
        return text
    return enc.decode(tokens[:limit])


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """
    Count tokens in text.

    Args:
        text: Text to count
        model: Model name for encoding

    Returns:
        Number of tokens
    """
    enc = tiktoken.encoding_for_model(model if model else "gpt-4o-mini")
    return len(enc.encode(text))
