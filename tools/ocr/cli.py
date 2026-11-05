#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file cli.py
@brief Command line of the OCR tool: `python -m tools.ocr {transcribe,queue,suspects,verify,providers,check-key,decode}`.

@details Run from the repository root with a Python that has PyMuPDF (for example the markitdown environment).
Pages go online to Google (Gemini) by the maintainer's decision, except confidential files (refused by name
unless `--allow-confidential`). The key is never printed; every error text is redacted. See tools/ocr/README.md.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from tools.ocr import cipher, config, render, suspects, verify
from tools.ocr.keys import KeyError_, redact
from tools.ocr.ledger import Ledger, parse_queue
from tools.ocr.pipeline import ConfidentialError, Runner, combine
from tools.ocr.providers import REGISTRY, ProviderError, get_provider

log = logging.getLogger("tools.ocr")


class RedactFilter(logging.Filter):
    """!
    @brief Logging filter that removes keys from every record.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """!
        @brief Redact the message and its arguments.
        @param record The log record.
        @return bool Always True.
        """
        record.msg = redact(record.getMessage())
        record.args = ()
        return True


def build_parser() -> argparse.ArgumentParser:
    """!
    @brief The argument parser.
    @return argparse.ArgumentParser The parser with its sub-commands.
    """
    ap = argparse.ArgumentParser(prog="python -m tools.ocr", description=__doc__.split("\n")[1])
    ap.add_argument("--papers", help="papers folder (default: env PCBT_PAPERS, else papers/ of the main checkout)")
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        """!
        @brief Add the options shared by transcribe and queue.
        @param p Sub-parser.
        @return None
        """
        p.add_argument("--provider", default="gemini", choices=sorted(REGISTRY))
        p.add_argument("--model", help="model name (default: data/models.json)")
        p.add_argument("--pause", type=float, default=4.0, help="seconds between requests (default 4)")
        p.add_argument("--daily-limit", type=int, help="stop after this many requests today")
        p.add_argument("--dpi", type=int, default=render.DEFAULT_DPI)
        p.add_argument("--allow-confidential", action="store_true",
                       help="send a file marked confidential to an online provider (the maintainer must agree)")
        p.add_argument("--force", action="store_true", help="transcribe again even if the output exists")

    t = sub.add_parser("transcribe", help="transcribe pages of one PDF")
    t.add_argument("pdf", help="PDF path or stem in papers/pdf")
    t.add_argument("--pages", default="1", help="'3,5-6', '10-' or 'all' (PDF page numbers, 1-based)")
    t.add_argument("--out", help="also write the pages joined into this file")
    common(t)
    q = sub.add_parser("queue", help="process the pending lines of a queue file")
    q.add_argument("queue", nargs="?", help="queue file (default papers/ocr/QUEUE.md)")
    q.add_argument("--limit", type=int, default=20, help="pages to try in this run (default 20)")
    q.add_argument("--status", action="store_true", help="list pending lines and exit")
    common(q)
    s = sub.add_parser("suspects", help="find suspect pages and the printed/PDF page offset")
    s.add_argument("--only", help="comma-separated file stems")
    asm_p = sub.add_parser("assemble", help="assemble the per-page outputs of PDFs into papers/md-final/<stem>.md")
    asm_p.add_argument("stems", nargs="+", help="PDF stems in papers/pdf")
    asm_p.add_argument("--root", help="repository root for the used-by search (default: parent of the papers folder)")
    map_p = sub.add_parser("map", help="write papers/notes/OCR_MAP.md and ocr_map.json (what is done and needed; offline)")
    map_p.add_argument("--root", help="repository root for the documents and the program (default: parent of the papers folder)")
    v = sub.add_parser("verify", help="write an HTML page with the page image beside its transcription")
    v.add_argument("pdf")
    v.add_argument("--page", type=int, required=True)
    v.add_argument("--md", help="transcription file (default papers/ocr/<stem>_p<N>.md)")
    v.add_argument("--out")
    sub.add_parser("providers", help="list the providers and their models")
    c = sub.add_parser("check-key", help="one tiny request; prints only OK or FAIL")
    c.add_argument("--provider", default="gemini", choices=sorted(REGISTRY))
    c.add_argument("--pdf", help="send page 1 of this PDF (default: a synthetic page)")
    d = sub.add_parser("decode", help="decode the base-36 font cipher in a text file")
    d.add_argument("file")
    d.add_argument("--out")
    d.add_argument("--force", action="store_true", help="decode every page, also one that does not look ciphered")
    return ap


def resolve_pdf(arg: str, papers: Path) -> Path:
    """!
    @brief Find a PDF from a path or a stem.
    @param arg    Path, or a file stem in papers/pdf.
    @param papers Papers folder.
    @return Path The PDF.
    @throws FileNotFoundError If it does not exist.
    """
    for cand in (Path(arg), papers / "pdf" / arg, papers / "pdf" / f"{arg}.pdf"):
        if cand.is_file():
            return cand
    raise FileNotFoundError(f"no PDF '{arg}' (looked in {papers / 'pdf'})")


def ocr_dir(papers: Path) -> Path:
    """!
    @brief Folder of the online-OCR work: per-page outputs, the ledger `usage.json` and the queue `QUEUE.md`.
    @param papers Papers folder.
    @return Path `papers/ocr`; an older library that still has `papers/gemini` and no `papers/ocr` keeps using it.
    """
    new = papers / "ocr"
    old = papers / "gemini"
    return old if (old.is_dir() and not new.exists()) else new


def out_dir(papers: Path, provider: str) -> Path:
    """!
    @brief Folder of the per-page outputs of a provider.
    @param papers   Papers folder.
    @param provider Provider name.
    @return Path `papers/ocr` for Gemini (the default provider), `papers/ocr/<provider>` for any other.
    """
    base = ocr_dir(papers)
    return base if provider == "gemini" else base / provider


def make_runner(a, papers: Path) -> Runner:
    """!
    @brief Build the runner from the parsed options.
    @param a      Parsed arguments.
    @param papers Papers folder.
    @return Runner Ready to run.
    """
    return Runner(get_provider(a.provider), out_dir(papers, a.provider),
                  Ledger(ocr_dir(papers) / "usage.json"), model=a.model, pause=a.pause,
                  daily_limit=a.daily_limit, allow_confidential=a.allow_confidential, dpi=a.dpi)


def report(outcomes) -> int:
    """!
    @brief Print a one-line summary per page and decide the exit code.
    @param outcomes List of Outcome.
    @return int 0 if every page is ok or skipped, 2 if stopped by a quota or the limit, 1 on failures.
    """
    code = 0
    for o in outcomes:
        print(f"{o.file} p{o.page}: {o.status}" + (f" ({o.note})" if o.note else ""))
        if o.status in ("quota", "limit"):
            code = 2
            print("stopped: the remaining pages stay pending for tomorrow (nothing was lost)")
        elif o.status == "failed" and code == 0:
            code = 1
    return code


def cmd_transcribe(a, papers: Path) -> int:
    """!
    @brief The `transcribe` command.
    @param a      Parsed arguments.
    @param papers Papers folder.
    @return int Exit code.
    """
    pdf = resolve_pdf(a.pdf, papers)
    pages = config.parse_pages(a.pages, render.page_count(pdf))
    runner = make_runner(a, papers)
    outcomes = runner.run_pages(pdf, pages, a.force)
    if a.out:
        Path(a.out).write_text(combine(outcomes), encoding="utf-8")
    return report(outcomes)


def cmd_queue(a, papers: Path) -> int:
    """!
    @brief The `queue` command: take the pending lines of a queue file.
    @param a      Parsed arguments.
    @param papers Papers folder.
    @return int Exit code.
    """
    qpath = Path(a.queue) if a.queue else ocr_dir(papers) / "QUEUE.md"
    ledger = Ledger(ocr_dir(papers) / "usage.json")
    done = ledger.done()
    pending = [i for i in parse_queue(qpath.read_text(encoding="utf-8"))
               if (i.file, i.page) not in done and not (out_dir(papers, a.provider) / f"{i.file}_p{i.page}.md").is_file()]
    if a.status:
        for i in pending:
            print(f"{i.file} p{i.page}  {i.why}")
        print(f"{len(pending)} pending; requests today: {ledger.requests_today(a.provider)}")
        return 0
    runner = make_runner(a, papers)
    outcomes = []
    for item in pending[:a.limit]:
        o = runner.run_page(papers / "pdf" / f"{item.file}.pdf", item.page, a.force)
        outcomes.append(o)
        if o.status in ("quota", "limit"):
            break
    return report(outcomes)


def cmd_suspects(a, papers: Path) -> int:
    """!
    @brief The `suspects` command.
    @param a      Parsed arguments.
    @param papers Papers folder.
    @return int Exit code.
    """
    res = suspects.scan(papers, a.only.split(",") if a.only else None)
    suspects.write_reports(res, papers / "md" / "suspect_pages.json", papers / "notes" / "SUSPECT_PAGES.md")
    print(f"{len(res)} files with suspect pages or an offset; {sum(len(v['suspect']) for v in res.values())} pages")
    return 0


def cmd_verify(a, papers: Path) -> int:
    """!
    @brief The `verify` command.
    @param a      Parsed arguments.
    @param papers Papers folder.
    @return int Exit code.
    """
    pdf = resolve_pdf(a.pdf, papers)
    md = Path(a.md) if a.md else out_dir(papers, "gemini") / f"{pdf.stem}_p{a.page}.md"
    out = Path(a.out) if a.out else papers / "verify" / f"{pdf.stem}_p{a.page}.html"
    text = md.read_text(encoding="utf-8")
    printed = suspects.printed_page_number(_page_text(pdf, a.page))
    title = f"{pdf.name} - PDF page {a.page}" + (f" (printed page {printed})" if printed else "")
    print(verify.write_verify(render.render_page(pdf, a.page), text, title, out))
    return 0


def _page_text(pdf: Path, page: int) -> str:
    """!
    @brief Text layer of one page.
    @param pdf  PDF path.
    @param page 1-based page.
    @return str The text, or an empty string on failure.
    """
    try:
        import pymupdf
        with pymupdf.open(pdf) as doc:
            return doc[page - 1].get_text()
    except Exception:
        return ""


def cmd_providers(a, papers: Path) -> int:
    """!
    @brief The `providers` command.
    @param a      Parsed arguments.
    @param papers Papers folder.
    @return int Exit code.
    """
    table = config.models()
    for name, cls in sorted(REGISTRY.items()):
        cfg = table.get(name, {})
        print(f"{name}: {'online' if cls.online else 'offline'}, key from {', '.join(cls.key_env) or '-'}, "
              f"default model {cfg.get('default', cls.default_model)}, fallbacks {cfg.get('fallbacks', [])}")
    return 0


def cmd_check_key(a, papers: Path) -> int:
    """!
    @brief The `check-key` command: one tiny request, no retry, a 60 s timeout; prints OK or FAIL and the time.
    @details A PDF given with `--pdf` passes the confidential guard like any transcription (its page 1 is sent).
             On a failure the line says the kind of error (HTTP status), never the key.
    @param a      Parsed arguments.
    @param papers Papers folder.
    @return int 0 for OK, 1 for FAIL, 3 when the PDF is confidential.
    """
    prov = get_provider(a.provider)
    if hasattr(prov, "retries"):
        prov.retries = 1          # a key check must answer at once: no pauses of 20 + 40 + 80 s on a 429 or 503
    model = config.models().get(a.provider, {}).get("default") or prov.default_model
    why, t0 = "", time.time()
    try:
        if a.pdf:
            pdf = resolve_pdf(a.pdf, papers)
            Runner(prov, papers, None, model=model).check_confidential(pdf)   # raises ConfidentialError
            png = render.render_page(pdf, 1, dpi=100)
        else:
            png = render.synthetic_png()
        res = prov.transcribe(png, "Reply with the text you can read, at most 30 words.",
                              {"model": model, "timeout": 60})
        ok = bool(res.text.strip())
        why = "" if ok else f"empty answer, finish {res.finish_reason}"
    except (ProviderError, KeyError_, RuntimeError) as e:
        log.error("%s", redact(e))
        ok = False
        why = f"HTTP {e.status}" if getattr(e, "status", 0) else type(e).__name__
    print(("OK" if ok else "FAIL") + f" ({model}, {time.time() - t0:.1f} s" + (f", {why})" if why else ")"))
    return 0 if ok else 1


def cmd_decode(a, papers: Path) -> int:
    """!
    @brief The `decode` command: base-36 font cipher post-processor.
    @param a      Parsed arguments.
    @param papers Papers folder.
    @return int Exit code.
    """
    text, n = cipher.decode_text(Path(a.file).read_text(encoding="utf-8"), force=a.force)
    out = Path(a.out) if a.out else Path(a.file).with_suffix(".decoded.md")
    out.write_text(text, encoding="utf-8")
    print(f"{n} tokens decoded -> {out}")
    return 0


def cmd_assemble(a, papers: Path) -> int:
    """!
    @brief The `assemble` command: one final Markdown per PDF in `papers/md-final/`.
    @param a      Parsed arguments (`stems`, `--root`).
    @param papers Papers folder.
    @return int Exit code.
    """
    import fitz  # PyMuPDF, only needed here
    from . import assemble as asm, suspects as su
    root = Path(a.root) if a.root else papers.parent
    out = papers / "md-final"
    out.mkdir(exist_ok=True)
    for stem in a.stems:
        doc = fitz.open(str(resolve_pdf(stem, papers)))
        texts = [doc[i].get_text() for i in range(len(doc))]
        found = {i + 1: su.printed_page_number(t) for i, t in enumerate(texts)}
        off = su.page_offset({k: v for k, v in found.items() if v})
        printed = {p: su.printed_page(p, found[p], off) for p in found}
        digital = sum(len(t) for t in texts[:8]) / max(1, min(8, len(texts))) > 600
        (out / f"{stem}.md").write_text(asm.assemble(papers, stem, root, len(doc), None, printed, digital),
                                        encoding="utf-8")
        print(f"{stem}: {out / (stem + '.md')}")
    return 0


def cmd_map(a, papers: Path) -> int:
    """!
    @brief The `map` command: the map of what is converted and what the theory still needs (offline, no provider).
    @param a      Parsed arguments (`--root`).
    @param papers Papers folder.
    @return int Exit code.
    """
    from . import papermap
    root = Path(a.root) if a.root else papers.parent
    md, js = papermap.write_map(papers, root)
    print(f"{md}\n{js}")
    return 0


COMMANDS = {"map": cmd_map, "assemble": cmd_assemble, "transcribe": cmd_transcribe, "queue": cmd_queue, "suspects": cmd_suspects, "verify": cmd_verify,
            "providers": cmd_providers, "check-key": cmd_check_key, "decode": cmd_decode}


def main(argv: list[str] | None = None) -> int:
    """!
    @brief Entry point.
    @param argv Arguments (default sys.argv[1:]).
    @return int Exit code: 0 ok, 1 failure, 2 stopped by quota, 3 refused (confidential, key problem).
    """
    a = build_parser().parse_args(argv)
    handler = logging.StreamHandler()
    handler.addFilter(RedactFilter())
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, handlers=[handler],
                        format="%(levelname)s %(message)s", force=True)
    try:
        return COMMANDS[a.cmd](a, config.papers_dir(a.papers))
    except (ConfidentialError, KeyError_) as e:
        print(f"refused: {redact(e)}", file=sys.stderr)
        return 3
    except Exception as e:  # last resort: nothing with a key may reach the terminal
        print(f"error: {type(e).__name__}: {redact(e)}", file=sys.stderr)
        return 1
