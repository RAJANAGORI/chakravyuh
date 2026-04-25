import json
import os
from typing import Iterable

from fastapi import HTTPException


def sanitize_filename(filename: str) -> str:
    safe = os.path.basename((filename or "").strip())
    if not safe or safe in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    if any(ch in safe for ch in ("/", "\\", "\x00")):
        raise HTTPException(status_code=400, detail="Invalid filename.")
    return safe


def ensure_extension(filename: str, allowed: Iterable[str]) -> None:
    low = filename.lower()
    if not any(low.endswith(ext) for ext in allowed):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed)}",
        )


def sniff_text_type(content: bytes, expected: str) -> None:
    # Expected in {"json", "txt"}.
    if expected == "json":
        try:
            json.loads(content.decode("utf-8"))
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON content.") from exc
    elif expected == "txt":
        try:
            content.decode("utf-8")
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid UTF-8 text file.") from exc


def sniff_binary_type(content: bytes, expected: str) -> None:
    sig = content[:16]
    if expected == "pdf" and not sig.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Invalid PDF signature.")
    if expected == "png" and not sig.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(status_code=400, detail="Invalid PNG signature.")
    if expected == "jpg" and not sig.startswith(b"\xff\xd8\xff"):
        raise HTTPException(status_code=400, detail="Invalid JPEG signature.")
    if expected == "webp":
        if len(sig) < 12 or not (sig[0:4] == b"RIFF" and sig[8:12] == b"WEBP"):
            raise HTTPException(status_code=400, detail="Invalid WEBP signature.")
