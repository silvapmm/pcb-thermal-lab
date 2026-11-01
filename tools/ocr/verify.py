#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file verify.py
@brief Verify mode: the page image next to its transcription, in one HTML file, for the reviewer.

@details A transcription counts as READ only after someone has compared it with the page image. The HTML has
the image (embedded, so the file is self-contained) on the left and the text on the right, with the PDF and
printed page numbers. Nothing is sent anywhere; the file is written inside the papers folder (git-ignored).
"""

from __future__ import annotations

import base64
import html
from pathlib import Path


def build_html(png: bytes, text: str, title: str) -> str:
    """!
    @brief The comparison page.
    @param png   Page image (PNG bytes).
    @param text  Transcription (Markdown/LaTeX shown as plain text).
    @param title Heading (file and page numbers).
    @return str A complete HTML document.
    """
    img = base64.b64encode(png).decode()
    return ("<!doctype html><html><head><meta charset='utf-8'><title>" + html.escape(title) + "</title>"
            "<style>body{margin:0;font:14px sans-serif}h1{font-size:16px;margin:8px}"
            ".row{display:flex;gap:8px;height:calc(100vh - 40px)}.row>div{flex:1;overflow:auto;border:1px solid #888}"
            "img{width:100%}pre{white-space:pre-wrap;margin:8px;font:13px monospace}</style></head><body>"
            "<h1>" + html.escape(title) + "</h1><div class='row'><div><img src='data:image/png;base64," + img + "'></div>"
            "<div><pre>" + html.escape(text) + "</pre></div></div></body></html>")


def write_verify(png: bytes, text: str, title: str, out: Path) -> Path:
    """!
    @brief Write the comparison page to a file.
    @param png   Page image.
    @param text  Transcription.
    @param title Heading.
    @param out   Output path.
    @return Path The path written.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_html(png, text, title), encoding="utf-8")
    return out
