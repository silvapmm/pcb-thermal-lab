#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file build_manual_pdf.py
@brief Build the PDF of the user manual (docs/USER_MANUAL.md): a cover with the program version, a table of contents, numbered chapters, figures with captions, page headers and footers.

@details Pure Python: reportlab (BSD licence, `requirements-docs.txt`) lays out the pages and the DejaVu fonts bundled with Matplotlib give the Unicode
         coverage (°, ×, θ, ψ, ≥, µ), so no system library is needed. The layout follows the user manual of the maintainer's Water Pump Simulator
         (same author, MIT). Only the Markdown subset of the manual is read:

           - headings `#` (title), `##` (chapter: a new page and a TOC entry), `###` (section: a TOC entry), paragraphs;
           - bullet lists (`- `) and numbered lists (`1. `), with indented continuation lines;
           - pipe tables (the first row is the header), fenced code blocks;
           - an image on its own line, `![alt](images/x.png)`, followed by an italic paragraph: its caption, kept on the page of the image;
           - inline `**bold**`, `*italic*`, `` `code` `` and `[text](link)` (web links stay clickable).

         The `## Contents` section of the Markdown is left out (the PDF has its own table of contents with page numbers). The screenshots are
         re-encoded as JPEG (quality 82, at most 1400 pixels wide) in a temporary folder, which keeps the PDF small; the PNG files are not touched.

         The version on the cover is `pcbthermal.__version__`. The build stops when the stamp line of the Markdown (`Program version X.Y.Z`, line 3)
         names another version, so a PDF never carries a stale stamp (tests/test_user_manual.py holds the Markdown to the same rule).

         Usage: `.venv/bin/python -m tools.manual.build_manual_pdf [--out FILE]` (default `docs/USER_MANUAL.pdf`, git-ignored; at a release the file
         is attached to the GitHub release as `PCB-Thermal-Lab-User-Manual.pdf`, docs/versions.md A1).
"""

import argparse
import logging
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANUAL = ROOT / "docs" / "USER_MANUAL.md"
STAMP = re.compile(r"^Program version (\S+) ")           # The stamp line of the manual: 'Program version 2.8.0 · PMS Labs · MIT licence'
RELEASE_ASSET = "PCB-Thermal-Lab-User-Manual.pdf"         # Name of the file attached to a GitHub release (no version: 'latest/download' finds it)

log = logging.getLogger("tools.manual")


def manual_stamp(text):
    """!
    @brief The version named by the stamp line of the manual.
    @param text Content of docs/USER_MANUAL.md.
    @return str The version (for example '2.8.0'), or None when line 3 is not a stamp line.
    """
    lines = text.splitlines()
    m = STAMP.match(lines[2]) if len(lines) > 2 else None
    return m.group(1) if m else None


def chapter_titles(text):
    """!
    @brief The chapters of the manual: the `## ` headings, in order, without the Contents heading.
    @param text Content of docs/USER_MANUAL.md.
    @return list of str The heading texts (for example '1. About the program').
    """
    return [ln[3:].strip() for ln in text.splitlines() if ln.startswith("## ") and ln[3:].strip() != "Contents"]


def contents_entries(text):
    """!
    @brief The chapters listed in the `## Contents` section of the manual.
    @param text Content of docs/USER_MANUAL.md.
    @return list of str The entries as 'N. Title', in order.
    """
    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.strip() == "## Contents")
    out = []
    for ln in lines[start + 1:]:
        if ln.startswith("## "):
            break
        if re.match(r"^\d+\.\s", ln.strip()):
            out.append(ln.strip())
    return out


# ------------------------------------------------------------------------------------------------------------------------------------
# Layout (reportlab is imported here only: the helpers above are used by the tests without it)
# ------------------------------------------------------------------------------------------------------------------------------------
def _layout():
    """!
    @brief Import reportlab, register the fonts and return the styles and the classes the build uses.
    @return dict Name -> object (styles, colours, page geometry, reportlab classes).
    @throws SystemExit When reportlab is not installed (it is in requirements-docs.txt, not in requirements.txt).
    """
    try:
        import matplotlib
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        raise SystemExit("reportlab is needed to build the PDF: .venv/bin/pip install -r requirements-docs.txt")

    font_dir = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    for name, file in (("DejaVu", "DejaVuSans.ttf"), ("DejaVu-Bold", "DejaVuSans-Bold.ttf"), ("DejaVu-Oblique", "DejaVuSans-Oblique.ttf"),
                       ("DejaVu-BoldOblique", "DejaVuSans-BoldOblique.ttf"), ("DejaVuMono", "DejaVuSansMono.ttf")):
        pdfmetrics.registerFont(TTFont(name, str(font_dir / file)))
    pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold", italic="DejaVu-Oblique", boldItalic="DejaVu-BoldOblique")

    ink, ink2, ink3 = colors.HexColor("#1f1f1e"), colors.HexColor("#52514e"), colors.HexColor("#8a8984")
    accent, light, grid = colors.HexColor("#1f6fb2"), colors.HexColor("#f3f2ef"), colors.HexColor("#e4e3df")
    base = dict(fontName="DejaVu", textColor=ink)
    styles = {
        "cover_title": ParagraphStyle("cover_title", fontSize=30, leading=36, fontName="DejaVu-Bold", textColor=ink),
        "cover_sub": ParagraphStyle("cover_sub", fontSize=18, leading=24, fontName="DejaVu", textColor=accent, spaceBefore=6),
        "cover_line": ParagraphStyle("cover_line", fontSize=11, leading=16, fontName="DejaVu", textColor=ink2),
        "h2": ParagraphStyle("h2", fontSize=18, leading=23, spaceAfter=10, fontName="DejaVu-Bold", textColor=accent),
        "h3": ParagraphStyle("h3", fontSize=12.5, leading=16, spaceBefore=10, spaceAfter=5, fontName="DejaVu-Bold", textColor=ink),
        "body": ParagraphStyle("body", fontSize=9.5, leading=13.5, spaceAfter=5, **base),
        "bullet": ParagraphStyle("bullet", fontSize=9.5, leading=13.5, spaceAfter=2, leftIndent=12, bulletIndent=2, **base),
        "numbered": ParagraphStyle("numbered", fontSize=9.5, leading=13.5, spaceAfter=2, leftIndent=18, bulletIndent=0,
                                   bulletFontName="DejaVu-Bold", **base),
        "subbullet": ParagraphStyle("subbullet", fontSize=9.5, leading=13.5, spaceAfter=2, leftIndent=32, bulletIndent=22, **base),
        "caption": ParagraphStyle("caption", fontSize=8.5, leading=11.5, spaceBefore=3, spaceAfter=10, fontName="DejaVu-Oblique", textColor=ink2),
        "cell": ParagraphStyle("cell", fontSize=8.2, leading=10.6, **base),
        "cellhead": ParagraphStyle("cellhead", fontSize=8.2, leading=10.6, fontName="DejaVu-Bold", textColor=ink),
        "code": ParagraphStyle("code", fontSize=7.6, leading=10, fontName="DejaVuMono", textColor=ink, backColor=light,
                               borderPadding=(4, 5, 4, 5), spaceBefore=3, spaceAfter=9, leftIndent=5, rightIndent=5),
        "toc0": ParagraphStyle("toc0", fontSize=10.5, leading=16, fontName="DejaVu-Bold", textColor=ink),
        "toc1": ParagraphStyle("toc1", fontSize=9, leading=12, leftIndent=16, **base),
    }
    page_w, page_h = A4
    margin = 18 * mm
    return dict(colors=colors, mm=mm, A4=A4, styles=styles, ink=ink, ink2=ink2, ink3=ink3, accent=accent, light=light, grid=grid,
                page_w=page_w, page_h=page_h, margin=margin, frame_w=page_w - 2 * margin, frame_h=page_h - 2 * margin - 16 * mm)


def inline(text):
    """!
    @brief Convert inline Markdown (code, bold, italic, links) to the paragraph markup of reportlab.
    @param text Markdown text of one paragraph, list item or table cell.
    @return str Markup for a reportlab Paragraph; code spans are cut out first so that the other rules never touch them.
    """
    def esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    out = []
    for part in re.split(r"(`[^`]+`)", text):
        if part.startswith("`") and part.endswith("`") and len(part) > 1:
            out.append(f'<font name="DejaVuMono" size="-0.6" color="#3a3936">{esc(part[1:-1])}</font>')
            continue
        s = esc(part)
        # A web link stays clickable; a link to a file of the repository keeps only its text (the PDF is read outside the repository)
        s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<link href="\2" color="#1f6fb2">\1</link>', s)
        s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", s)
        out.append(s)
    return "".join(out)


def jpeg_copy(png, work):
    """!
    @brief A JPEG copy of a screenshot for the PDF (quality 82, at most 1400 pixels wide): about a third of the bytes of the same picture embedded raw.
    @param png Path of the PNG file in docs/images.
    @param work Temporary folder that receives the copy.
    @return Path The JPEG file.
    """
    from PIL import Image                                                    # Pillow comes with Matplotlib

    im = Image.open(png).convert("RGB")
    if im.width > 1400:
        im = im.resize((1400, round(im.height * 1400 / im.width)), Image.LANCZOS)
    out = Path(work) / (png.stem + ".jpg")
    im.save(out, "JPEG", quality=82, optimize=True, progressive=True)
    return out


def parse(md_text, md_dir, work, L):
    """!
    @brief Turn the Markdown of the manual into reportlab flowables (the cover and the table of contents are added by build()).
    @param md_text Content of docs/USER_MANUAL.md.
    @param md_dir Folder of the Markdown file (image paths are relative to it).
    @param work Temporary folder for the JPEG copies of the pictures.
    @param L The layout of _layout().
    @return list The flowables of the body, from the first chapter on.
    """
    from reportlab.platypus import CondPageBreak, PageBreak, Paragraph, Preformatted, Spacer, Table, TableStyle

    S = L["styles"]
    lines = md_text.splitlines()
    story, para = [], []
    code_chars = int((L["frame_w"] - 20) / (7.6 * 0.602))    # characters on one code line at the code font size

    def flush():
        if para:
            story.append(Paragraph(inline(" ".join(para)), S["body"]))
            para.clear()

    # The body starts at the first numbered chapter: the title block, the introduction and the Contents list are on the cover pages
    i = next(k for k, ln in enumerate(lines) if re.match(r"^##\s+1\.\s", ln))
    first_chapter = True
    while i < len(lines):
        ln, s = lines[i], lines[i].strip()
        if s.startswith("```"):                              # fenced code block
            flush()
            j, code = i + 1, []
            while j < len(lines) and not lines[j].strip().startswith("```"):
                code.append(lines[j])
                j += 1
            story.append(Preformatted("\n".join(code), S["code"], maxLineLength=code_chars, newLineChars="  "))
            i = j + 1
            continue
        m = re.match(r"^(#{2,3})\s+(.*)$", s)
        if m:                                                # chapter or section heading
            flush()
            level, text = len(m.group(1)), m.group(2)
            if level == 2:
                if not first_chapter:
                    story.append(PageBreak())                # every chapter starts a page
                first_chapter = False
            else:
                story.append(CondPageBreak(0.18 * L["frame_h"]))
            p = Paragraph(inline(text), S["h2" if level == 2 else "h3"])
            p._toc_level = level - 2
            p._chapter = text if level == 2 else None
            p.keepWithNext = True
            story.append(p)
            i += 1
            continue
        m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", s)
        if m:                                                # image, then its italic caption
            flush()
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            caption = None
            if j < len(lines) and lines[j].strip().startswith("*") and not lines[j].strip().startswith("**"):
                cap = []
                while j < len(lines) and lines[j].strip():
                    cap.append(lines[j].strip())
                    j += 1
                text = " ".join(cap)
                caption = Paragraph(inline(text[1:-1] if text.startswith("*") and text.endswith("*") else text), S["caption"])
                i = j
            else:
                i += 1
            story.append(_figure(jpeg_copy((md_dir / m.group(2)).resolve(), work), caption, L))
            continue
        if s.startswith("|"):                                # table
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            story.append(_table(rows, L, Paragraph, Table, TableStyle))
            continue
        bullet = s.startswith("- ")
        number = re.match(r"^\d+\.\s", s)
        if bullet or number:                                 # list (bullets or numbers kept as written)
            flush()
            pattern = r"^- " if bullet else r"^\d+\.\s"
            while i < len(lines) and re.match(pattern, lines[i].strip()):
                head = lines[i].strip()
                mark, first = ("•", head[2:]) if bullet else head.split(" ", 1)
                item, subs = [first], []
                i += 1
                while i < len(lines) and lines[i].startswith("  ") and lines[i].strip() and not re.match(pattern, lines[i].strip()):
                    inner = lines[i].strip()
                    if not bullet and inner.startswith("- "):
                        subs.append([inner[2:]])             # an indented bullet under a numbered step: a sub-list
                    elif subs:
                        subs[-1].append(inner)               # continuation of that sub-bullet
                    else:
                        item.append(inner)
                    i += 1
                story.append(Paragraph(inline(" ".join(item)), S["bullet" if bullet else "numbered"], bulletText=mark))
                for sub in subs:
                    story.append(Paragraph(inline(" ".join(sub)), S["subbullet"], bulletText="–"))
            story.append(Spacer(1, 4))
            continue
        if not s:
            flush()
        else:
            para.append(s)
        i += 1
    flush()
    return story


def _figure(path, caption, L):
    """!
    @brief A flowable that draws a picture at the frame width (capped at 62 % of the frame height) with its caption, never split across pages.
    @param path JPEG file.
    @param caption Paragraph of the caption, or None.
    @param L The layout of _layout().
    @return Flowable The figure.
    """
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import Flowable

    class Figure(Flowable):
        """!
        @brief Picture plus caption that shrinks (down to 38 % of the frame height) to stay on the page of the text before it.
        """

        def __init__(self):
            """!
            @brief Read the size of the picture.
            """
            super().__init__()
            self.iw, self.ih = ImageReader(str(path)).getSize()

        def wrap(self, avail_w, avail_h):
            """!
            @brief Choose the size of the picture for the space available.
            @param avail_w Width available in points.
            @param avail_h Height available in points.
            @return tuple (width, height) in points.
            """
            # The caption keeps its own spaces: spaceBefore under the picture, spaceAfter under the caption (before the text that follows,
            # often the numbered list of an annotated picture, which otherwise sat flush under the caption)
            cap_h = caption.wrap(avail_w, avail_h)[1] + caption.getSpaceBefore() + caption.getSpaceAfter() if caption else 8
            full_h = min(self.ih * avail_w / self.iw, 0.62 * L["frame_h"])
            room = avail_h - cap_h - 4
            self.img_h = room if full_h > room >= 0.38 * L["frame_h"] else full_h
            self.img_w = self.iw * self.img_h / self.ih
            self.cap_h = cap_h
            self.width, self.height = avail_w, self.img_h + 4 + cap_h
            return self.width, self.height

        def split(self, avail_w, avail_h):
            """!
            @brief Never split: the figure moves to the next page whole.
            @param avail_w Width available in points.
            @param avail_h Height available in points.
            @return list Empty.
            """
            return []

        def draw(self):
            """!
            @brief Draw the picture centred with a thin frame, and the caption under it.
            """
            x = (self.width - self.img_w) / 2
            y = self.height - self.img_h
            self.canv.drawImage(str(path), x, y, self.img_w, self.img_h)
            self.canv.setStrokeColor(L["grid"])
            self.canv.setLineWidth(0.5)
            self.canv.rect(x, y, self.img_w, self.img_h)
            if caption:
                caption.drawOn(self.canv, 0, caption.getSpaceAfter())

    return Figure()


def _table(rows, L, Paragraph, Table, TableStyle):
    """!
    @brief A table from Markdown pipe rows (the first row is the header, the second the alignment row).
    @param rows The lines of the table.
    @param L The layout of _layout().
    @param Paragraph The reportlab Paragraph class.
    @param Table The reportlab Table class.
    @param TableStyle The reportlab TableStyle class.
    @return Table The table; column widths follow the longest text of each column, between 10 % and 60 % of the frame.
    """
    S = L["styles"]
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    header, body = cells[0], cells[2:]
    ncol = len(header)
    lengths = [max(len(re.sub(r"[`*]", "", r[k])) if k < len(r) else 0 for r in [header] + body) for k in range(ncol)]
    weights = [min(max(n, 6), 80) ** 0.8 for n in lengths]
    fw = L["frame_w"]
    widths = [min(max(fw * w / sum(weights), 0.10 * fw), 0.60 * fw) for w in weights]
    widths = [w * fw / sum(widths) for w in widths]
    data = [[Paragraph(inline(c), S["cellhead"]) for c in header]]
    data += [[Paragraph(inline(c), S["cell"]) for c in r[:ncol]] + [""] * (ncol - len(r)) for r in body]
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), L["light"]), ("LINEBELOW", (0, 0), (-1, 0), 0.8, L["ink3"]),
                           ("LINEBELOW", (0, 1), (-1, -1), 0.4, L["grid"]), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                           ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    t.spaceAfter = 8
    return t


def build(md_path, pdf_path):
    """!
    @brief Build the PDF: cover, table of contents, chapters; headers with the current chapter, footers with the version and the page.
    @param md_path The Markdown of the manual.
    @param pdf_path The PDF to write.
    @return int The number of pages.
    @throws SystemExit When the stamp of the manual is not the version of the program.
    """
    import pcbthermal

    # The stamp is checked before anything is laid out (and before reportlab is imported), so a stale manual stops at once
    text = md_path.read_text(encoding="utf-8")
    version = pcbthermal.__version__
    stamp = manual_stamp(text)
    if stamp != version:
        raise SystemExit(f"{md_path.name} says 'Program version {stamp}' on line 3 but the program is {version}: update the stamp first")
    L = _layout()
    from reportlab.platypus import BaseDocTemplate, Frame, NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer
    from reportlab.platypus import Image as RLImage
    from reportlab.platypus.tableofcontents import TableOfContents
    S, mm = L["styles"], L["mm"]
    title = "PCB Thermal Lab: User Manual"

    class ManualDoc(BaseDocTemplate):
        """!
        @brief Document template that records the chapters for the headers and the TOC entries and PDF bookmarks of the headings.
        """

        def __init__(self, path):
            """!
            @brief Two page templates: the cover (no header) and the pages of the manual.
            @param path PDF to write.
            """
            super().__init__(str(path), pagesize=L["A4"], leftMargin=L["margin"], rightMargin=L["margin"], topMargin=L["margin"] + 8 * mm,
                             bottomMargin=L["margin"] + 8 * mm, title=title, author="Pedro Silva (PMS Labs)",
                             subject=f"User manual of PCB Thermal Lab {version}", creator="tools/manual/build_manual_pdf.py")
            frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="body")
            self.addPageTemplates([PageTemplate("cover", [frame], onPageEnd=self._cover_page),
                                   PageTemplate("body", [frame], onPageEnd=self._body_page)])
            self.chapter, self._key = "", 0

        def beforeDocument(self):
            """!
            @brief Reset the bookmark counter and the chapter at each pass of multiBuild (the keys must be the same in every pass).
            """
            self._key, self.chapter = 0, ""

        def afterFlowable(self, flowable):
            """!
            @brief Record a heading: the chapter for the header, a TOC entry and a PDF bookmark.
            @param flowable The flowable just laid out.
            """
            level = getattr(flowable, "_toc_level", None)
            if level is None:
                return
            if getattr(flowable, "_chapter", None):
                self.chapter = flowable._chapter
            text = flowable.getPlainText()
            self._key += 1
            key = f"h{self._key}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=level, closed=level > 0)
            self.notify("TOCEntry", (level, text, self.page, key))

        def _cover_page(self, canv, doc):
            """!
            @brief The cover band and its footer line.
            @param canv The canvas of the page.
            @param doc This document.
            """
            canv.saveState()
            canv.setFillColor(L["accent"])
            canv.rect(0, L["page_h"] - 14 * mm, L["page_w"], 14 * mm, stroke=0, fill=1)
            canv.setFont("DejaVu", 8)
            canv.setFillColor(L["ink3"])
            canv.drawString(L["margin"], L["margin"], "MIT licence · Copyright (c) 2025-2026 Pedro Silva (PMS Labs)")
            canv.restoreState()

        def _body_page(self, canv, doc):
            """!
            @brief The header (manual title, current chapter) and the footer (version, page) of a page of the manual.
            @param canv The canvas of the page.
            @param doc This document.
            """
            canv.saveState()
            top = L["page_h"] - L["margin"] + 2 * mm
            canv.setFont("DejaVu", 7.5)
            canv.setFillColor(L["ink3"])
            canv.drawString(L["margin"], top, title)
            canv.drawRightString(L["page_w"] - L["margin"], top, re.sub(r"[*`]", "", self.chapter))
            canv.setStrokeColor(L["grid"])
            canv.setLineWidth(0.6)
            canv.line(L["margin"], top - 2 * mm, L["page_w"] - L["margin"], top - 2 * mm)
            bottom = L["margin"]
            canv.line(L["margin"], bottom + 4 * mm, L["page_w"] - L["margin"], bottom + 4 * mm)
            canv.drawString(L["margin"], bottom, f"PCB Thermal Lab {version}")
            canv.drawRightString(L["page_w"] - L["margin"], bottom, f"Page {doc.page}")
            canv.restoreState()

    with tempfile.TemporaryDirectory() as work:
        body = parse(text, md_path.parent, work, L)
        # The cover: title, version, the window, the disclaimer; then the introduction of the Markdown (between the stamp and the Contents)
        lines = text.splitlines()
        intro_end = next(k for k, ln in enumerate(lines) if ln.strip() == "## Contents")
        intro = [p.replace("\n", " ") for p in "\n".join(lines[3:intro_end]).strip().split("\n\n") if p.strip()]
        shot = jpeg_copy(md_path.parent / "images" / "manual_window_tour.png", work)
        from reportlab.lib.utils import ImageReader
        sw, sh = ImageReader(str(shot)).getSize()
        img = RLImage(str(shot), width=L["frame_w"], height=L["frame_w"] * sh / sw)
        story = [Spacer(1, 12 * mm), Paragraph("PCB Thermal Lab", S["cover_title"]), Paragraph("User Manual", S["cover_sub"]),
                 Spacer(1, 4 * mm), Paragraph(f"Program version {version}", S["cover_line"]),
                 Paragraph("Thermal simulation of printed circuit boards", S["cover_line"]), Spacer(1, 10 * mm), img, Spacer(1, 10 * mm),
                 Paragraph("<i>PCB Thermal Lab is a design aid. Its models have not yet been compared with measurements of a real board: "
                           "validate critical designs by measurement.</i>", S["cover_line"]),
                 NextPageTemplate("body"), PageBreak()]
        story += [Paragraph(inline(p), S["body"]) for p in intro]
        toc = TableOfContents()
        toc.levelStyles = [S["toc0"], S["toc1"]]
        toc.dotsMinLevel = 0
        story += [PageBreak(), Paragraph("Contents", S["h2"]), toc, PageBreak()] + body
        doc = ManualDoc(pdf_path)
        doc.multiBuild(story)
    pages = doc.page
    log.info("wrote %s (%d pages)", pdf_path, pages)
    return pages


def main(argv=None):
    """!
    @brief Command line: build the PDF of the user manual.
    @param argv Argument list (default sys.argv[1:]).
    @return int Exit code 0.
    """
    ap = argparse.ArgumentParser(description="Build the PDF of the user manual (docs/USER_MANUAL.md).")
    ap.add_argument("--md", type=Path, default=MANUAL, help="the Markdown of the manual (default docs/USER_MANUAL.md)")
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "USER_MANUAL.pdf", help="the PDF to write (default docs/USER_MANUAL.pdf, git-ignored)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    pages = build(args.md.resolve(), args.out.resolve())
    size = args.out.stat().st_size / 1e6
    log.info("%d pages, %.1f MB; attach it to the release as %s", pages, size, RELEASE_ASSET)
    return 0


if __name__ == "__main__":
    sys.exit(main())
