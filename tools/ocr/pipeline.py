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

import difflib
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


MIN_SEAM_WORDS = 5       # shortest run of equal words that is accepted as the overlap between two strips
SEAM_WINDOW = 160        # words at the end of one strip and at the start of the next in which the overlap is searched
SEAM_SLACK = 25          # words allowed after the matched run at the end of a strip (the cut line is partial)


def _words(text: str) -> list[tuple[str, int, int]]:
    """!
    @brief Words of a text with their character span, in a normalised form for comparing two transcriptions of the same lines.
    @param text Markdown text.
    @return list[tuple[str, int, int]] (lower-case alphanumeric form, start, end) of every word that has one.
    """
    out = []
    for m in re.finditer(r"\S+", text):
        w = re.sub(r"[^0-9a-z]+", "", m.group(0).lower())
        if w:
            out.append((w, m.start(), m.end()))
    return out


def merge_two(a: str, b: str) -> str:
    """!
    @brief Join the transcriptions of two overlapping strips of a page, dropping the lines both contain.
    @details The tail of `a` and the head of `b` show the same printed lines. The longest run of equal words
             between them (at least MIN_SEAM_WORDS) marks the seam: everything of `a` up to the end of the run and
             everything of `b` after it are kept. A cut line is partial in one of the two, so the run is searched
             in the words, not in the lines. With no such run the texts are joined with a comment that says so.
    @param a Text of the upper strip.
    @param b Text of the lower strip.
    @return str The joined text.
    """
    wa, wb = _words(a)[-SEAM_WINDOW:], _words(b)[:SEAM_WINDOW]
    sm = difflib.SequenceMatcher(None, [w[0] for w in wa], [w[0] for w in wb], autojunk=False)
    blk = sm.find_longest_match(0, len(wa), 0, len(wb))
    if blk.size >= MIN_SEAM_WORDS and len(wa) - (blk.a + blk.size) <= SEAM_SLACK:
        # Take `a` through the end of the run and `b` after it. When the run ends in the middle of a line of `b`
        # (the cut line was partial in `a`) the rest of that line continues `a`'s last line, so join with a space.
        head, rest = a[:wa[blk.a + blk.size - 1][2]].rstrip(), b[wb[blk.b + blk.size - 1][2]:]
        sep = "\n" if rest.startswith("\n") or not rest.strip() else " "
        if sep == " ":
            # A cut line closed an emphasis in the upper strip: its trailing '*' is a seam artefact, not printed text.
            head = head.rstrip("*").rstrip()
        return head + sep + rest.lstrip("\n ").rstrip()
    return a.rstrip() + "\n<!-- strip seam: no overlap found, a line may be repeated or missing -->\n" + b.lstrip()


def merge_strips(texts: list[str]) -> str:
    """!
    @brief Join the transcriptions of the horizontal strips of a page (top to bottom).
    @param texts Transcription of each strip.
    @return str One text.
    """
    out = texts[0]
    for t in texts[1:]:
        out = merge_two(out, t)
    return out


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
                 renderer=None, info=None, max_tokens: int | None = None, whole_page: bool = False,
                 strips: bool = True):
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
        @param renderer           Function (pdf, page, dpi, clip) -> PNG bytes (default render.render_page, looked up
                                  at call time; replaced in tests).
        @param info               Function pdf -> (text of the first pages, metadata) for the confidential check
                                  (default render.first_page_info, looked up at call time).
        @param max_tokens         Output token budget per request (None: the provider's default, 8192 for Claude).
        @param whole_page         One request per page, never half-page crops or fallback models: a refused page stays
                                  empty and a page cut at the token limit is kept with a note.
        @param strips             After the half-page crops, try three strips with 10 % overlap and join them
                                  (default: part of the refusal ladder, full page, halves, strips, fallback models;
                                  three more requests for a page that stays refused).
        @return None
        """
        self.max_tokens, self.whole_page, self.strips = max_tokens, whole_page, strips
        self.provider, self.out_dir, self.ledger = provider, Path(out_dir), ledger
        cfg = config.models().get(provider.name, {})
        self.model = model or cfg.get("default") or provider.default_model
        self.fallbacks = [m for m in cfg.get("fallbacks", []) if m != self.model]
        self.prompt = prompt or config.default_prompt()
        # A provider with a free daily cap (OpenRouter) carries its limit in data/models.json; --daily-limit overrides it.
        self.pause, self.dpi = pause, dpi
        self.daily_limit = daily_limit if daily_limit is not None else cfg.get("daily_limit")
        self.allow_confidential = allow_confidential
        # Defaults resolved at call time (a default argument would freeze the function when the module is imported).
        self._sleep = sleep
        self._render = renderer or (lambda pdf, page, dpi, clip: render.render_page(pdf, page, dpi, clip))
        self._info = info or (lambda pdf: render.first_page_info(pdf))
        self._requests = 0
        self._tokens = [0, 0]      # input and output tokens reported by the provider in this run

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
        try:
            text, meta = self._info(pdf)
        except Exception as e:  # fail closed: a file that cannot be checked is not sent
            raise ConfidentialError(f"{pdf.name} could not be read for the confidential check "
                                    f"({type(e).__name__}) and is not sent to '{self.provider.name}'.") from None
        why = config.is_confidential(pdf, text, meta)
        if why:
            raise ConfidentialError(f"{pdf.name} is treated as confidential ({why}) and is not sent to "
                                    f"'{self.provider.name}'. Use a local provider, or --allow-confidential "
                                    f"if the maintainer says so for this file.")

    # ------------------------------------------------------------------ calls
    def _call(self, png: bytes, model: str) -> Result:
        """!
        @brief One provider request (counted with its HTTP retries), with the pause before the next.
        @param png   Image bytes.
        @param model Model name.
        @return Result The provider's result.
        @throws ProviderError From the provider.
        """
        self._requests += 1
        try:
            opts = {"model": model}
            if self.max_tokens:
                opts["max_tokens"] = int(self.max_tokens)
            res = self.provider.transcribe(png, self.prompt, opts)
            # The retries inside the provider are requests too (the daily limit counts what was sent).
            self._requests += max(0, int((res.extra or {}).get("attempts", 1)) - 1)
            usage = (res.extra or {}).get("usage") or {}
            self._tokens[0] += int(usage.get("input_tokens") or 0)
            self._tokens[1] += int(usage.get("output_tokens") or 0)
            return res
        except ProviderError as e:
            self._requests += max(0, e.attempts - 1)
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
        if not (res.recitation or res.split):
            used = res.model or self.model       # a provider that walks a chain of models says which one answered
            if not res.text.strip():
                return res.text, used, f"empty answer (finish {res.finish_reason})"
            # Text with another finish reason (MAX_TOKENS, SAFETY, ...) may be cut: keep it, but say so.
            return res.text, used, ("" if res.finish_reason in ("STOP", "", "end_turn", "stop_sequence", "stop") else
                                          f"finish {res.finish_reason}: the text may be incomplete")
        if self.whole_page:
            # No crops (they repeat the overlap): keep a page cut at the token limit with a note, leave a refusal empty.
            if res.split and res.text.strip():
                return res.text, self.model, f"finish {res.finish_reason}: the text is cut at the token limit"
            said = " ".join(res.text.split())[:160]
            return "", self.model, (f"{res.finish_reason or 'RECITATION'} on the full page (whole-page mode: no crops, no fallback)"
                                    + (f"; the model said: {said}" if said else ""))
        # Refused by the copyright filter (or cut at the token limit): two half-page crops with the same model.
        log.info("%s p%d: %s, trying half-page crops", pdf.name, page, res.finish_reason or "RECITATION")
        halves = [self._call(self._render(pdf, page, self.dpi, clip), self.model) for clip in render.HALVES]
        if not any(h.recitation or h.split or not h.text.strip() for h in halves):
            return (f"<!-- half-page crops ({res.finish_reason or 'RECITATION'} on the full page) -->\n" + "\n\n".join(h.text for h in halves),
                    self.model, "half-page crops")
        if self.strips:
            log.info("%s p%d: crops refused, trying three strips", pdf.name, page)
            parts = [self._call(self._render(pdf, page, self.dpi, clip), self.model) for clip in render.STRIPS]
            if not any(h.recitation or h.split or not h.text.strip() for h in parts):
                return ("<!-- three strips joined (refused on the full page and on the half-page crops) -->\n"
                        + merge_strips([h.text for h in parts]), self.model, "strips")
        for alt in self.fallbacks:
            log.info("%s p%d: crops refused, trying %s", pdf.name, page, alt)
            res = self._call(self._render(pdf, page, self.dpi, None), alt)
            if not (res.recitation or res.split) and res.text.strip():
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
        before, t0, tok0 = self._requests, time.time(), list(self._tokens)
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
            # The model that answered is recorded in the page file when the provider can change it (OpenRouter).
            tag = f"<!-- model: {self.provider.name}:{model} -->\n" if getattr(self.provider, "header_model", False) else ""
            out.write_text(f"<!-- page {page} -->\n{tag}{text}", encoding="utf-8")
        self.ledger.add(provider=self.provider.name, model=model, file=stem, page=page, ok=status == "ok",
                        seconds=round(time.time() - t0, 1), words=len(text.split()) if status == "ok" else 0,
                        requests=self._requests - before, note=note[:300],
                        **({"input_tokens": self._tokens[0] - tok0[0], "output_tokens": self._tokens[1] - tok0[1]}
                           if self._tokens != tok0 else {}))
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
