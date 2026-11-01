# tools/ocr

PDF pages to Markdown (equations in LaTeX, tables, page markers) through pluggable providers. It is a developer tool,
not part of the `pcbthermal` package (the program never imports it). MIT, like the rest of the repository.

Run from the repository root with a Python that has PyMuPDF (the markitdown environment has it; the project `.venv` does not):

```sh
PY=/Volumes/SSD/PROJETOS/markitdown/.venv/bin/python
$PY -W ignore -m tools.ocr providers                       # providers, models, key variables
$PY -W ignore -m tools.ocr check-key --pdf ArXiv2307.08354 # one tiny request; prints only OK or FAIL
$PY -W ignore -m tools.ocr transcribe ShenWang2019Vias --pages 1   # a stem in papers/pdf or a path; --pages '3,5-6', '10-', 'all'
$PY -W ignore -m tools.ocr queue --limit 20                # next pending lines of papers/gemini/QUEUE.md
$PY -W ignore -m tools.ocr queue --status                  # what is pending, requests today
$PY -W ignore -m tools.ocr suspects                        # suspect pages + printed/PDF page numbers
$PY -W ignore -m tools.ocr verify Lemczyk1992 --page 1     # HTML with the page image beside the transcription
$PY -W ignore -m tools.ocr decode FILE.md                  # base-36 font cipher post-processor
```

Page numbers are PDF pages, 1-based (the `<!-- page N -->` markers use the same number). Exit codes: 0 ok, 1 failure,
2 stopped by the daily quota or `--daily-limit` (the rest stays pending for tomorrow), 3 refused (confidential file, key problem).

## The papers folder

`--papers`, else the environment variable `PCBT_PAPERS`, else `papers/` of the main checkout. It is ignored by version control
and holds third-party material that is never committed. Layout: `pdf/` the PDFs, `gemini/` per-page outputs `<stem>_p<N>.md`
(each starts with `<!-- page N -->`), the ledger `gemini/usage.json` and the queue `gemini/QUEUE.md`, `md/` local conversions,
`notes/SUSPECT_PAGES.md`, `verify/` the comparison pages.

## What it does

* **Providers** (`providers/`): `transcribe(image_bytes, prompt, options) -> Result`. `gemini` (online; default model
  `gemini-3.1-flash-lite`; models and fallbacks in `data/models.json`), `local` (offline; the maintainer's `extractpdf`
  MLX converter with the model `ovis`, a stub that was not run by the tests: set `PCBT_EXTRACTPDF` and
  `PCBT_EXTRACTPDF_PYTHON`). A new provider is a class in `providers/` registered in `providers/__init__.py`.
* **Retry and quota**: HTTP 429 (per minute), 500 and 503 are retried with a pause that doubles; a 429 that names the daily
  quota stops the run at once and records the page as pending. Three failures in a row also stop it. Concurrency is 1, with a
  pause (`--pause`, 4 s) between requests.
* **RECITATION**: a page refused by the copyright filter (empty answer with `finishReason` RECITATION) is retried as two
  half-page crops (top and bottom, 10 % overlap), then once with each fallback model. The output says which was used.
* **Resume**: a page whose output file exists is skipped unless `--force`. `--out FILE` also writes the pages of the run joined.
* **Ledger** (`usage.json`): one entry per attempt (date, provider, model, file, page, ok, seconds, words, requests, note).
  `--daily-limit N` stops after N requests today.
* **Queue**: the `| # | file | page | why |` table of `QUEUE.md`, or lines `file.pdf:page`.
* **Suspect pages**: low word count, undecoded equations, base-36 cipher, broken-font tokens, a garbage PDF text layer; each
  page is reported as `PDF N / printed M` and the file's usual offset (a paper quoted at "page 418" is a different PDF page).
* **Verify**: one HTML file, page image left and transcription right. A transcription counts as read only after a reviewer
  has compared it with the page image.
* **Cipher decoder** (`cipher.py`): in some old PDFs the converter output is pairs of base-36 digits; each pair is a
  character code plus 360 (`D4D6CTD7` is `pres`; `AD` is the `fl` ligature). Only what the converter kept can be decoded:
  capital letters that it dropped are not recoverable (use a Gemini transcription for those pages).

## The key

Looked up in this order: the environment variable the provider declares (`GEMINI_API_KEY`, then `GOOGLE_API_KEY`), then the
file `.ocr_keys` in the project root (also in the main checkout when the tool runs from a worktree, found with
`git rev-parse --git-common-dir`). Format: one `provider=KEY` per line, `#` for comments. The file must be mode 600; a file
that group or others can read is refused with a message that does not contain the key. `.ocr_keys` and `*.key` are in
`.gitignore`, and `tests/test_no_secrets.py` fails if a key-like string is tracked.

The key is sent in a request header only. It is never printed, logged, passed on a command line, put in a URL, or written
in an exception message, the ledger or an output: every error text goes through `keys.redact()`, and the logging handler
redacts every record. If a key was ever pasted in a chat or a file, create a new one and replace the line.

## Privacy

Pages sent to Gemini leave this machine and go to Google. On the free tier Google may use the content to improve its
products. By the maintainer's decision this is accepted for open papers, and **never** for the confidential ODB++
specification or any file marked confidential: the tool refuses a file whose name matches `data/confidential.json`, or whose
metadata or first page says "confidential", unless `--allow-confidential` is given (only the maintainer authorises it). The
local provider sends nothing anywhere and is not subject to the guard.

## Tests

`QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_ocr_tool.py tests/test_no_secrets.py` (no network, no PDF:
fake providers, a scripted HTTP layer). `tests/test_docs.py` and `tests/test_license_header.py` cover `tools/`.
