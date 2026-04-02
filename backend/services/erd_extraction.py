"""
Hybrid PDF text: PyMuPDF first, OCR fallback when text is too short (image-only PDFs).
Requires optional system deps: poppler (pdf2image), Tesseract (pytesseract).
"""
from __future__ import annotations

import io
from typing import Any, Dict, Tuple

import fitz  # PyMuPDF


def _min_chars_threshold(cfg: Dict[str, Any]) -> int:
    ocr_cfg = cfg.get("ocr") or {}
    return int(ocr_cfg.get("min_chars_before_ocr", 50))


def extract_text_pymupdf(file_path: str) -> str:
    doc = fitz.open(file_path)
    try:
        texts = [page.get_text("text") for page in doc]
        return "\n".join(texts)
    finally:
        doc.close()


def extract_text_pdf_hybrid(file_path: str, cfg: Dict[str, Any]) -> Tuple[str, str]:
    """
    Returns (text, method) where method is 'pymupdf' or 'ocr' or 'pymupdf+empty'.
    """
    threshold = _min_chars_threshold(cfg)
    raw = extract_text_pymupdf(file_path)
    stripped = raw.strip()
    if len(stripped) >= threshold:
        return raw, "pymupdf"

    ocr_text = _ocr_pdf_pages(file_path, cfg)
    if ocr_text.strip():
        return ocr_text, "ocr"

    if stripped:
        return raw, "pymupdf"
    return (
        f"[No extractable text from PDF: tried PyMuPDF and OCR. "
        f"Install poppler + tesseract for OCR fallback.]",
        "none",
    )


def _ocr_pdf_pages(file_path: str, cfg: Dict[str, Any]) -> str:
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError:
        return ""

    ocr_cfg = cfg.get("ocr") or {}
    dpi = int(ocr_cfg.get("dpi", 200))
    max_pages = int(ocr_cfg.get("max_pages", 30))

    try:
        images = convert_from_path(file_path, dpi=dpi, first_page=1, last_page=max_pages)
    except Exception:
        return ""

    parts = []
    for i, pil in enumerate(images):
        try:
            text = pytesseract.image_to_string(pil)
            if text.strip():
                parts.append(f"--- Page {i + 1} ---\n{text}")
        except Exception:
            continue
    return "\n\n".join(parts)


def truncate_text(text: str, max_chars: int = 500_000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[Content truncated for storage.]"
