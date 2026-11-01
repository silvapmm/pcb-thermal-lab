#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file pipeline.py
@brief Runs a provider over PDF pages: confidential guard, ledger, quota stop, resume, RECITATION handling.

@details One page at a time (concurrency 1) with a pause between requests. A page whose output file exists is
skipped (resume) unless `force`. A page refused with RECITATION is retried as two half-page crops (top and bottom,
10 % overlap) and then, if still refused, once with each fallback model of data/models.json. The daily quota
(an HTTP 429 that names it, or `daily_limit` reached) stops the run cleanly and the page is recorded as pending
for tomorrow. Every error text is redacted; no key reaches a log or the screen.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path

from tools.ocr import config, render
from tools.ocr.keys import redact
from tools.ocr.ledger import Ledger
from tools.ocr.providers.base import Provider, ProviderError, Result

log = logging.getLogger("tools.ocr")


class ConfidentialError(Exception):
    """!
    @brief A confidential file was given to an online provider without `--allow-confidential`.
    """


@dataclass
class Outcome:
    """!
    @brief The result of one page.
    @details status is "ok", "skipped" (output exists), "failed", "quota" (stop: try tomorrow) or "limit" (daily limit set by the user).
    """

    file: str
    page: int
    status: str
    path: Path | None = None
    text: str = ""
    note: str = ""


class Runner:
    """!
    @brief Transcribes pages of PDFs with one provider and keeps the ledger.
    """

    def __init__(self, provider: Provider, out_dir: Path, ledger: Ledger, model: str | None = None,
                 prompt: str | None = None, pause: float = 4.0, daily_limit: int | None = None,
                 allow_confidential: bool = False, dpi: int = render.DEFAULT_DPI, sleep=time.sleep,
                 renderer=render.render_page, info=render.first_page_info):
        """!
        @brief Create a runner.
        @param provider           The provider.
        @param out_dir            Folder of the per-page outputs `<stem>_p<N>.md`.
        @param ledger             The ledger (usage.json).
        @param model              Model name (default: the provider's default from data/models.json).
        @param prompt             Prompt (default: data/prompt.txt).
        @param pause              Seconds between two requests.
        @param daily_limit        Stop when this many requests were sent today to the provider (None: no limit).
        @param allow_confidential Allow a confidential file to go to an online provider (never by default).
        @param dpi                Rendering resolution.
        @param sleep              Function used to wait (replaced in tests).
        @param renderer           Function (pdf, page, dpi, clip) -> PNG bytes (replaced in tests).
        @param info               Function pdf -> (first page text, metadata) for the confidential check.
        @return None
        """
        self.provider, self.out_dir, self.ledger = provider, Path(out_dir), ledger
        cfg = config.models().get(provider.name, {})
        self.model = model or cfg.get("default") or provider.default_model
        self.fallbacks = [m for m in cfg.get("fallbacks", []) if m != self.model]
        self.prompt = prompt or config.default_prompt()
        self.pause, self.daily_limit, self.dpi = pause, daily_limit, dpi
        self.allow_confidential = allow_confidential
        self._sleep, self._render, self._info = sleep, renderer, info
        self._requests = 0

    # ------------------------------------------------------------------ guards
    def check_confidential(self, pdf: Path) -> None:
        """!
        @brief Refuse a confidential file for an online provider.
        @param pdf Path of the PDF.
        @return None
        @throws ConfidentialError If the file matches the confidential list and the flag is not set.
        """
        if not self.provider.online or self.allow_confidential:
            return
        text, meta = self._info(pdf)
        why = config.is_confidential(pdf, text, meta)
        if why:
            raise ConfidentialError(f"{pdf.name} is treated as confidential ({why}) and is not sent to "
                                    f"'{self.provider.name}'. Use a local provider, or --allow-confidential "
                                    f"if the maintainer says so for this file.")

    # ------------------------------------------------------------------ calls
    def _call(self, png: bytes, model: str) -> Result:
        """!
        @brief One provider request (counted), with the pause before the next.
        @param png   Image bytes.
        @param model Model name.
        @return Result The provider's result.
        @throws ProviderError From the provider.
        """
        self._requests += 1
        try:
            return self.provider.transcribe(png, self.prompt, {"model": model})
        except ProviderError:
            raise
        except Exception as e:  # a provider that raises something else: wrap it with a redacted message
            raise ProviderError(f"{type(e).__name__}: {e}") from None
        finally:
            self._sleep(self.pause)

    def _transcribe(self, pdf: Path, page: int) -> tuple[str, str, str]:
        """!
        @brief Transcribe a page with the RECITATION fallbacks.
        @param pdf  Path of the PDF.
        @param page 1-based page.
        @return tuple[str, str, str] (text, model used, note). Empty text means the page was refused.
        @throws ProviderError For a quota or a hard failure.
        """
        res = self._call(self._render(pdf, page, self.dpi, None), self.model)
        if not res.recitation:
            return res.text, self.model, "" if res.text.strip() else f"empty answer (finish {res.finish_reason})"
        # Refused by the copyright filter: two half-page crops with the same model.
        log.info("%s p%d: RECITATION, trying half-page crops", pdf.name, page)
        halves = [self._call(self._render(pdf, page, self.dpi, clip), self.model) for clip in render.HALVES]
        if not any(h.recitation or not h.text.strip() for h in halves):
            return ("<!-- half-page crops (RECITATION on the full page) -->\n" + "\n\n".join(h.text for h in halves),
                    self.model, "half-page crops")
        for alt in self.fallbacks:
            log.info("%s p%d: crops refused, trying %s", pdf.name, page, alt)
            res = self._call(self._render(pdf, page, self.dpi, None), alt)
            if not res.recitation and res.text.strip():
                return res.text, alt, f"fallback model {alt}"
        return "", self.model, "RECITATION on the full page, the crops and every fallback model"

    def run_page(self, pdf: Path, page: int, force: bool = False) -> Outcome:
        """!
        @brief Transcribe one page and record it.
        @param pdf   Path of the PDF.
        @param page  1-based page.
        @param force Transcribe again even if the output file exists.
        @return Outcome The result of the page.
        @throws ConfidentialError For a confidential file and an online provider.
        """
        stem = pdf.stem
        out = self.out_dir / f"{stem}_p{page}.md"
        if out.is_file() and not force:
            return Outcome(stem, page, "skipped", out, out.read_text(encoding="utf-8"), "output exists")
        self.check_confidential(pdf)
        if self.daily_limit is not None and self.ledger.requests_today(self.provider.name) >= self.daily_limit:
            return Outcome(stem, page, "limit", note=f"daily limit of {self.daily_limit} requests reached")
        before, t0 = self._requests, time.time()
        status, text, note, model = "failed", "", "", self.model
        try:
            text, model, note = self._transcribe(pdf, page)
            if text.strip():
                status = "ok"
        except ProviderError as e:
            note = redact(e)
            if e.quota_exhausted:
                status, note = "quota", "daily quota exhausted: " + note
        if status == "ok":
            self.out_dir.mkdir(parents=True, exist_ok=True)
            out.write_text(f"<!-- page {page} -->\n{text}", encoding="utf-8")
        self.ledger.add(provider=self.provider.name, model=model, file=stem, page=page, ok=status == "ok",
                        seconds=round(time.time() - t0, 1), words=len(text.split()) if status == "ok" else 0,
                        requests=self._requests - before, note=note[:300])
        return Outcome(stem, page, status, out if status == "ok" else None, text, note)

    def run_pages(self, pdf: Path, pages: list[int], force: bool = False, max_failures: int = 3) -> list[Outcome]:
        """!
        @brief Transcribe pages one after another; stop at a quota, the daily limit or repeated failures.
        @param pdf          Path of the PDF.
        @param pages        1-based pages.
        @param force        Transcribe again even if the output exists.
        @param max_failures Stop after this many failures in a row.
        @return list[Outcome] One per page tried (pages after a stop are not listed).
        """
        outcomes, fails = [], 0
        for p in pages:
            o = self.run_page(pdf, p, force)
            outcomes.append(o)
            log.info("%s p%d: %s %s", pdf.name, p, o.status, o.note)
            if o.status in ("quota", "limit"):
                break
            fails = fails + 1 if o.status == "failed" else 0
            if fails >= max_failures:
                log.error("stopping after %d failures in a row", fails)
                break
        return outcomes


def combine(outcomes: list[Outcome]) -> str:
    """!
    @brief Join the texts of the pages into one Markdown document with `<!-- page N -->` markers.
    @param outcomes Outcomes with text (ok or skipped).
    @return str The document.
    """
    parts = []
    for o in outcomes:
        if o.text:
            body = re.sub(r"^<!-- page \d+ -->\s*", "", o.text)
            parts.append(f"<!-- page {o.page} -->\n{body}")
    return "\n\n".join(parts)
