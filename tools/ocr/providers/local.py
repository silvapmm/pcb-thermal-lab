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
from pathlib import Path

from tools.ocr.providers.base import Provider, ProviderError, Result

DEFAULT_FOLDER = "extractpdf"   # relative to the working directory; set PCBT_EXTRACTPDF (or pass folder) to the real project


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
        @param image_bytes PNG bytes of the page.
        @param prompt      Ignored (the converter has its own prompts).
        @param options     "model" (default "ovis").
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
                r = subprocess.run(self.command(pdf, out, options.get("model") or self.default_model),
                                   capture_output=True, text=True, timeout=self.timeout, cwd=str(self.folder),
                                   env=scrubbed_environment())
            except subprocess.TimeoutExpired as e:
                raise ProviderError("local converter timed out", retryable=False) from e
            if r.returncode != 0 or not out.is_file():
                raise ProviderError(f"local converter failed (rc={r.returncode}): {r.stderr[-300:]}")
            text = re.sub(r"^<!-- page \d+ -->\s*", "", out.read_text(encoding="utf-8"))
        return Result(text=text, model=options.get("model") or self.default_model, seconds=round(time.time() - t0, 1))
