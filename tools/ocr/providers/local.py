#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file local.py
@brief Local (offline) provider: wraps the maintainer's `extractpdf` converter (MLX model "ovis").

@details Stub that was ported from `papers/scripts/ocr/driver.sh`, not run by the tests (it needs the MLX
environment and loads a model of several GB). The page image is wrapped in a one-page PDF and converted with
`pdf2md_local.py --engine auto --mlx-model ovis --no-docling-formulas --no-scan-docling --page-markers --workers 1`.
The converter is a separate project and is run, never modified. Paths come from the environment:
`PCBT_EXTRACTPDF` (folder of the project, no default: set it) and `PCBT_EXTRACTPDF_PYTHON`
(its Python, default `<folder>/venv/bin/python`). One page at a time (concurrency 1) and do not run it while a
whole test battery runs (memory).
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import time
import itertools
from pathlib import Path

from tools.ocr.providers.base import Provider, ProviderError, Result

DEFAULT_FOLDER = "extractpdf"   # relative to the working directory; set PCBT_EXTRACTPDF (or pass folder) to the real project


MAX_REPEAT_LINES = 8          # more identical consecutive non-blank lines than this is a runaway (the ovis loop of '1' lines)
LENGTH_FACTOR = 1.6           # output longer than this times the expected length is refused
DEFAULT_PAGE_CHARS = 7500     # character budget of a page without a text layer (the densest good page of the 10 compared had 6733)


def check_output(text: str, expected_chars: int | None = None) -> str | None:
    """!
    @brief Guard against a runaway local conversion.
    @details Two signs: the same non-blank line repeated more than MAX_REPEAT_LINES times in a row (the ovis loop
             produced about 1500 lines '1' on one page; the longest run in the 29 good pages is 1), and an output longer
             than LENGTH_FACTOR times the expected length. A page cut short is not detected (a page may end mid-sentence).
    @param text           Converted Markdown of one page.
    @param expected_chars Expected length in characters (e.g. the PDF text layer of the page), or None for DEFAULT_PAGE_CHARS.
    @return str | None The reason the output is refused, or None when it passes.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    run = max((sum(1 for _ in g) for _, g in itertools.groupby(lines)), default=0)
    if run > MAX_REPEAT_LINES:
        return f"the same line is repeated {run} times in a row (runaway output)"
    limit = LENGTH_FACTOR * (expected_chars or DEFAULT_PAGE_CHARS)
    if len(text) > limit:
        return f"the output has {len(text)} characters, more than {LENGTH_FACTOR} times the expected {expected_chars or DEFAULT_PAGE_CHARS}"
    return None


def scrubbed_environment() -> dict[str, str]:
    """!
    @brief The environment for the converter process without the API keys of the online providers.
    @details The converter is a separate program and needs no key; an environment variable is visible to it and to
             everything it starts, so the variables that the providers declare are removed.
    @return dict[str, str] A copy of os.environ without those variables.
    """
    from tools.ocr.providers import REGISTRY
    names = {n for cls in REGISTRY.values() for n in cls.key_env}
    return {k: v for k, v in os.environ.items() if k not in names}


class LocalProvider(Provider):
    """!
    @brief Offline provider that runs the local MLX converter on a page image.
    """

    name = "local"
    online = False
    key_env = ()
    default_model = "ovis"

    def __init__(self, folder: str | None = None, python: str | None = None, timeout: float = 1800.0):
        """!
        @brief Create the provider.
        @param folder  Folder of the extractpdf project (default: the environment variable PCBT_EXTRACTPDF, else DEFAULT_FOLDER).
        @param python  Python of its environment (default env PCBT_EXTRACTPDF_PYTHON or <folder>/venv/bin/python).
        @param timeout Seconds allowed for one page.
        @return None
        """
        self.folder = Path(folder or os.environ.get("PCBT_EXTRACTPDF", DEFAULT_FOLDER))
        self.python = python or os.environ.get("PCBT_EXTRACTPDF_PYTHON", str(self.folder / "venv" / "bin" / "python"))
        self.timeout = timeout

    def command(self, pdf: Path, out: Path, model: str) -> list[str]:
        """!
        @brief The converter command line for one PDF.
        @param pdf   One-page PDF.
        @param out   Output Markdown path.
        @param model MLX model name for `--mlx-model`.
        @return list[str] Argument vector.
        """
        return [self.python, str(self.folder / "pdf2md_local.py"), str(pdf), "-o", str(out), "--engine", "auto",
                "--mlx-model", model, "--no-docling-formulas", "--no-scan-docling", "--page-markers",
                "--workers", "1"]

    def transcribe(self, image_bytes: bytes, prompt: str, options: dict) -> Result:
        """!
        @brief Convert one page image with the local converter (the prompt is not used by it).
        @details A converted page that fails `check_output` is retried with each fallback model of data/models.json
                 (only when no model was forced by the caller); if every model fails the last error is raised.
        @param image_bytes PNG bytes of the page.
        @param prompt      Ignored (the converter has its own prompts).
        @param options     "model" (default "ovis", forces that one model), "expected_chars" (expected length for the guard).
        @return Result The converted Markdown without the page marker.
        @throws ProviderError If the converter is missing, fails or times out, or every model fails the guard.
        """
        forced = options.get("model")
        models = [forced] if forced else [self.default_model] + [m for m in self._fallbacks() if m != self.default_model]
        err: ProviderError | None = None
        for model in models:
            try:
                res = self._convert(image_bytes, model)
            except ProviderError as e:
                if not e.retryable:
                    raise
                err = e
                continue
            why = check_output(res.text, options.get("expected_chars"))
            if why is None:
                return res
            err = ProviderError(f"local output refused ({model}): {why}", retryable=True)
        raise err

    @staticmethod
    def _fallbacks() -> list[str]:
        """!
        @brief The fallback models of the local provider from data/models.json.
        @return list[str] Model names in order (may be empty).
        """
        from tools.ocr import config
        return list(config.models().get("local", {}).get("fallbacks", []))

    def _convert(self, image_bytes: bytes, model: str) -> Result:
        """!
        @brief Run the converter once with one model.
        @param image_bytes PNG bytes of the page.
        @param model       MLX model name.
        @return Result The converted Markdown without the page marker.
        @throws ProviderError If the converter is missing, fails or times out.
        """
        try:
            from .. import render
        except ImportError as e:
            raise ProviderError("Pillow is needed to wrap the image in a PDF") from e
        if not (self.folder / "pdf2md_local.py").is_file():
            raise ProviderError(f"converter not found in {self.folder} (set PCBT_EXTRACTPDF)")
        t0 = time.time()
        with tempfile.TemporaryDirectory() as tmp:
            pdf, out = Path(tmp) / "page.pdf", Path(tmp) / "page.md"
            render.png_to_pdf(image_bytes, 200, pdf)     # the pages are rendered at 200 dpi
            try:
                r = subprocess.run(self.command(pdf, out, model),
                                   capture_output=True, text=True, timeout=self.timeout, cwd=str(self.folder),
                                   env=scrubbed_environment())
            except subprocess.TimeoutExpired as e:
                raise ProviderError("local converter timed out", retryable=False) from e
            if r.returncode != 0 or not out.is_file():
                raise ProviderError(f"local converter failed (rc={r.returncode}): {r.stderr[-300:]}")
            text = re.sub(r"^<!-- page \d+ -->\s*", "", out.read_text(encoding="utf-8"))
        return Result(text=text, model=model, seconds=round(time.time() - t0, 1))
