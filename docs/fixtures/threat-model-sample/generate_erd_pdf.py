#!/usr/bin/env python3
"""Build 01_erd_medflow.pdf from 01_erd_medflow.txt (needs: pip install PyMuPDF)."""
from __future__ import annotations

from pathlib import Path

import fitz


def _wrap_line(line: str, width: int) -> list[str]:
    if len(line) <= width:
        return [line]
    out: list[str] = []
    s = line
    while s:
        if len(s) <= width:
            out.append(s)
            break
        cut = s.rfind(" ", 0, width)
        if cut <= 0:
            cut = width
        out.append(s[:cut].rstrip())
        s = s[cut:].lstrip()
    return out


def main() -> None:
    root = Path(__file__).resolve().parent
    src = root / "01_erd_medflow.txt"
    dst = root / "01_erd_medflow.pdf"
    raw = src.read_text(encoding="utf-8")
    header = (
        "MedFlow Telehealth — ERD fixture for Chakravyuh\n"
        "Primary ERD document (PDF). Companion: 02_architecture_mermaid.txt + architecture_diagram.png\n\n"
    )
    text = header + raw

    w, h = fitz.paper_size("letter")
    margin_x = 48
    margin_top = 52
    margin_bot = 52
    fontsize = 8
    line_height = fontsize * 1.35
    max_chars = 105
    fontname = "cour"

    lines: list[str] = []
    for para in text.splitlines():
        lines.extend(_wrap_line(para, max_chars) if para else [""])

    doc = fitz.open()
    page = doc.new_page(width=w, height=h)
    y = margin_top
    x = margin_x

    for line in lines:
        if y + line_height > h - margin_bot:
            page = doc.new_page(width=w, height=h)
            y = margin_top
        page.insert_text(
            fitz.Point(x, y + fontsize),
            line,
            fontname=fontname,
            fontsize=fontsize,
        )
        y += line_height

    doc.save(dst)
    print(f"Wrote {dst} ({doc.page_count} pages)")


if __name__ == "__main__":
    main()
