"""
Architecture diagram summarization via Azure OpenAI multimodal chat (vision).
"""
from __future__ import annotations

import base64
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from utils.llm_provider import get_llm


DIAGRAM_SYSTEM = """You are a security-minded solutions architect. Analyze the architecture diagram image.
Produce a structured plain-text summary including:
- Major components (services, apps, data stores, gateways, external systems)
- Trust boundaries and security zones if visible
- Data flows and key integrations
- Notes on assumptions or unclear areas

Be concise but complete. Use bullet points and short headings. No markdown code fences."""


def _resize_image_bytes(image_bytes: bytes, max_side: int, mime: str) -> tuple[bytes, str]:
    """Downscale large images to reduce API payload."""
    try:
        from PIL import Image
    except ImportError:
        return image_bytes, mime

    import io

    # Default Pillow cap (~89M px) rejects some legitimate large diagrams before resize.
    # We downscale immediately; keep a high ceiling to block pathological decompression bombs.
    cap = 250_000_000
    if getattr(Image, "MAX_IMAGE_PIXELS", None):
        Image.MAX_IMAGE_PIXELS = max(Image.MAX_IMAGE_PIXELS, cap)

    img = Image.open(io.BytesIO(image_bytes))
    img = img.convert("RGB")
    w, h = img.size
    if max(w, h) <= max_side:
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=85)
        return out.getvalue(), "image/jpeg"

    ratio = max_side / float(max(w, h))
    nw, nh = int(w * ratio), int(h * ratio)
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=85)
    return out.getvalue(), "image/jpeg"


def summarize_diagram_image(image_bytes: bytes, mime_type: str, cfg: Dict[str, Any]) -> str:
    vision_cfg = cfg.get("vision") or {}
    max_side = int(vision_cfg.get("max_image_side_px", 1600))
    # Some Azure / gateway deployments reject omitted or null vision detail; require low|high.
    detail = vision_cfg.get("image_detail", "low")
    if detail not in ("low", "high"):
        detail = "low"
    data, out_mime = _resize_image_bytes(image_bytes, max_side, mime_type)
    b64 = base64.standard_b64encode(data).decode("ascii")
    url = f"data:{out_mime};base64,{b64}"

    llm = get_llm(cfg, temperature=0.2)
    human = HumanMessage(
        content=[
            {"type": "text", "text": "Analyze this architecture diagram."},
            {"type": "image_url", "image_url": {"url": url, "detail": detail}},
        ]
    )
    sys = SystemMessage(content=DIAGRAM_SYSTEM)
    resp = llm.invoke([sys, human])
    return (resp.content or "").strip()


def rasterize_pdf_first_page(pdf_path: str, cfg: Dict[str, Any]) -> tuple[bytes, str]:
    """Return JPEG bytes and mime for first page of PDF."""
    try:
        from pdf2image import convert_from_path
    except ImportError as e:
        raise RuntimeError("pdf2image required for PDF diagrams") from e

    ocr_cfg = cfg.get("ocr") or {}
    dpi = int(ocr_cfg.get("diagram_pdf_dpi", 200))
    images = convert_from_path(pdf_path, dpi=dpi, first_page=1, last_page=1)
    if not images:
        raise RuntimeError("No pages in PDF")
    import io

    from PIL import Image

    pil = images[0].convert("RGB")
    buf = io.BytesIO()
    pil.save(buf, format="JPEG", quality=90)
    return buf.getvalue(), "image/jpeg"
