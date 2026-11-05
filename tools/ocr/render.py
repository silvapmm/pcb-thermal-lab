#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file render.py
@brief Page rendering with PyMuPDF (imported late, so the rest of the tool works without it).
"""

from __future__ import annotations

from pathlib import Path

DEFAULT_DPI = 200       # the resolution that worked for the scanned papers (230 to 1080 words per page)
MAX_PIXELS = 40_000_000  # a hostile or odd page (a 200 x 200 inch box) would need GB at 200 dpi: the dpi is lowered
INFO_PAGES = 3           # pages whose text the confidential check reads (a mark is often on page 2, as in the ODB++ spec)
HALVES = ((0.0, 0.0, 1.0, 0.55), (0.0, 0.45, 1.0, 1.0))   # top and bottom with 10 % overlap, for RECITATION


def _pymupdf():
    """!
    @brief Import PyMuPDF.
    @return module The pymupdf module.
    @throws RuntimeError If it is not installed.
    """
    try:
        import pymupdf
        return pymupdf
    except ImportError as e:
        raise RuntimeError("PyMuPDF is needed to render pages: run with a Python that has it "
                           "(for example the markitdown environment)") from e


def page_count(pdf: Path) -> int:
    """!
    @brief Number of pages of a PDF.
    @param pdf Path of the PDF.
    @return int Page count.
    """
    with _pymupdf().open(pdf) as doc:
        return len(doc)


def render_page(pdf: Path, page_no: int, dpi: int = DEFAULT_DPI, clip: tuple | None = None) -> bytes:
    """!
    @brief Render one page, or a part of it, to PNG bytes.
    @param pdf     Path of the PDF.
    @param page_no 1-based page number.
    @param dpi     Resolution in dots per inch.
    @param clip    Optional (x0, y0, x1, y1) as fractions of the page, for the half-page crops.
    @return bytes PNG image.
    @throws ValueError If the page is outside the document.
    """
    mu = _pymupdf()
    with mu.open(pdf) as doc:
        if not 1 <= page_no <= len(doc):
            raise ValueError(f"page {page_no} is outside {pdf.name} (1 to {len(doc)})")
        page = doc[page_no - 1]
        r = page.rect
        rect = None
        if clip:
            rect = mu.Rect(r.x0 + clip[0] * r.width, r.y0 + clip[1] * r.height,
                           r.x0 + clip[2] * r.width, r.y0 + clip[3] * r.height)
        # Lower the resolution of an oversized page instead of allocating an image of several GB.
        box = rect or r
        pixels = (box.width * dpi / 72.0) * (box.height * dpi / 72.0)
        if pixels > MAX_PIXELS:
            dpi = max(1, int(dpi * (MAX_PIXELS / pixels) ** 0.5))
        return page.get_pixmap(dpi=dpi, clip=rect).tobytes("png")


def first_page_info(pdf: Path) -> tuple[str, str]:
    """!
    @brief Text of the first pages and the metadata, for the confidential-file check.
    @param pdf Path of the PDF.
    @return tuple[str, str] (text of the first INFO_PAGES pages, metadata values joined).
    @throws Exception If the PDF cannot be read (the caller refuses to send a file it could not check).
    """
    with _pymupdf().open(pdf) as doc:
        meta = " ".join(str(v) for v in (doc.metadata or {}).values() if v)
        return "\n".join(doc[i].get_text() for i in range(min(INFO_PAGES, len(doc)))), meta


def synthetic_png() -> bytes:
    """!
    @brief A small page with a known equation, drawn locally (no third-party content), to test a provider.
    @return bytes PNG image.
    """
    mu = _pymupdf()
    doc = mu.open()
    page = doc.new_page(width=400, height=200)
    page.insert_text((30, 60), "Test page 12", fontsize=18)
    page.insert_text((30, 110), "R = ln(b/a) / (2 pi k L)    (7)", fontsize=16)
    page.insert_text((30, 150), "a = 0.30 mm, b = 0.45 mm, k = 385 W/mK", fontsize=12)
    return page.get_pixmap(dpi=150).tobytes("png")
