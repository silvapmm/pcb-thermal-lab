#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file render.py
@brief Page rendering and text layers with pypdfium2 and Pillow (imported late, so the rest of the tool works without them).
"""

from __future__ import annotations

import io
from pathlib import Path

DEFAULT_DPI = 200       # the resolution that worked for the scanned papers (230 to 1080 words per page)
MAX_PIXELS = 40_000_000  # a hostile or odd page (a 200 x 200 inch box) would need GB at 200 dpi: the dpi is lowered
INFO_PAGES = 3           # pages whose text the confidential check reads (a mark is often on page 2, as in the ODB++ spec)
HALVES = ((0.0, 0.0, 1.0, 0.55), (0.0, 0.45, 1.0, 1.0))   # top and bottom with 10 % overlap, for RECITATION
# Three horizontal strips with 10 % overlap: a page that is refused as a whole and as two halves is often accepted in
# pieces of 40 % (the filter acts on the amount of recognisable text in one answer).
STRIPS = ((0.0, 0.0, 1.0, 0.40), (0.0, 0.30, 1.0, 0.70), (0.0, 0.60, 1.0, 1.0))


def _pdfium():
    """!
    @brief Import pypdfium2.
    @return module The pypdfium2 module.
    @throws RuntimeError If it is not installed.
    """
    try:
        import pypdfium2
        return pypdfium2
    except ImportError as e:
        raise RuntimeError("pypdfium2 is needed to render pages: pip install pypdfium2 in the Python that runs "
                           "the tool") from e


def _clean(text: str) -> str:
    """!
    @brief Normalise the line ends of a text layer (pdfium writes CR LF, the callers expect LF, a final line end and hyphens before a break).
    @param text Raw text of a page.
    @return str The text with LF line ends.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # pdfium marks a hyphen put in by the typesetter at a line end with U+FFFE and joins the lines: give back the
    # hyphen and the line break so that the words split as in the file (the callers count words and match lines).
    text = text.replace("\ufffe", "-\n")
    return text if not text or text.endswith("\n") else text + "\n"


def page_texts(pdf: Path, limit: int | None = None) -> list[str]:
    """!
    @brief Text layer of the pages of a PDF, one string per page.
    @param pdf   Path of the PDF.
    @param limit Maximum number of pages read from the start (None: all).
    @return list[str] Text of each page (LF line ends).
    @throws Exception If the file cannot be opened.
    """
    doc = _pdfium().PdfDocument(str(pdf))
    try:
        n = len(doc) if limit is None else min(limit, len(doc))
        out = []
        for i in range(n):
            page = doc[i]
            tp = page.get_textpage()
            out.append(_clean(tp.get_text_range()))
            tp.close()
            page.close()
        return out
    finally:
        doc.close()


def page_count(pdf: Path) -> int:
    """!
    @brief Number of pages of a PDF.
    @param pdf Path of the PDF.
    @return int Page count.
    """
    doc = _pdfium().PdfDocument(str(pdf))
    try:
        return len(doc)
    finally:
        doc.close()


def render_page(pdf: Path, page_no: int, dpi: int = DEFAULT_DPI, clip: tuple | None = None) -> bytes:
    """!
    @brief Render one page, or a part of it, to PNG bytes.
    @param pdf     Path of the PDF.
    @param page_no 1-based page number.
    @param dpi     Resolution in dots per inch.
    @param clip    Optional (x0, y0, x1, y1) as fractions of the page (y downwards), for the half-page crops.
    @return bytes PNG image.
    @throws ValueError If the page is outside the document.
    """
    doc = _pdfium().PdfDocument(str(pdf))
    try:
        if not 1 <= page_no <= len(doc):
            raise ValueError(f"page {page_no} is outside {pdf.name} (1 to {len(doc)})")
        page = doc[page_no - 1]
        w, h = page.get_size()                      # points
        # pdfium crops by the amount removed from each side, in points, from the left, bottom, right and top.
        crop = (0.0, 0.0, 0.0, 0.0)
        bw, bh = w, h
        if clip:
            crop = (clip[0] * w, (1.0 - clip[3]) * h, (1.0 - clip[2]) * w, clip[1] * h)
            bw, bh = (clip[2] - clip[0]) * w, (clip[3] - clip[1]) * h
        # Lower the resolution of an oversized page instead of allocating an image of several GB.
        pixels = (bw * dpi / 72.0) * (bh * dpi / 72.0)
        if pixels > MAX_PIXELS:
            dpi = max(1, int(dpi * (MAX_PIXELS / pixels) ** 0.5))
        image = page.render(scale=dpi / 72.0, crop=crop).to_pil()
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        page.close()
        return buf.getvalue()
    finally:
        doc.close()


def first_page_info(pdf: Path) -> tuple[str, str]:
    """!
    @brief Text of the first pages and the metadata, for the confidential-file check.
    @param pdf Path of the PDF.
    @return tuple[str, str] (text of the first INFO_PAGES pages, metadata values joined).
    @throws Exception If the PDF cannot be read (the caller refuses to send a file it could not check).
    """
    doc = _pdfium().PdfDocument(str(pdf))
    try:
        meta = " ".join(str(v) for v in (doc.get_metadata_dict() or {}).values() if v)
    finally:
        doc.close()
    return "\n".join(page_texts(pdf, INFO_PAGES)), meta


def png_to_pdf(png: bytes, dpi: int, path: Path) -> None:
    """!
    @brief Wrap a page image in a one-page PDF whose size follows the image resolution.
    @param png  PNG bytes.
    @param dpi  Resolution of the image in dots per inch.
    @param path Output PDF path.
    @return None
    """
    from PIL import Image
    Image.open(io.BytesIO(png)).convert("RGB").save(str(path), format="PDF", resolution=float(dpi))


def synthetic_png() -> bytes:
    """!
    @brief A small page with a known equation, drawn locally (no third-party content), to test a provider.
    @return bytes PNG image.
    """
    from PIL import Image, ImageDraw, ImageFont
    scale = 150 / 72.0                              # the page is 400 x 200 points at 150 dpi
    img = Image.new("RGB", (round(400 * scale), round(200 * scale)), "white")
    draw = ImageDraw.Draw(img)
    for y, size, text in ((60, 18, "Test page 12"), (110, 16, "R = ln(b/a) / (2 pi k L)    (7)"),
                          (150, 12, "a = 0.30 mm, b = 0.45 mm, k = 385 W/mK")):
        draw.text((30 * scale, y * scale), text, fill="black", font=ImageFont.load_default(size=round(size * scale)),
                  anchor="ls")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
