# tools/ocr

PDF pages to Markdown (equations in LaTeX, tables, page markers) through pluggable providers. It is a developer tool,
not part of the `pcbthermal` package (the program never imports it). MIT, like the rest of the repository.

Run from the repository root with a Python that has pypdfium2 and Pillow (`pip install pypdfium2`; the project `.venv` has Pillow through Matplotlib but not pypdfium2, which is not in `requirements.txt`):

```sh
PY=python   # any Python that has pypdfium2; the local provider also needs PCBT_EXTRACTPDF (folder of the extractpdf project)
$PY -W ignore -m tools.ocr providers                       # providers, models, key variables
$PY -W ignore -m tools.ocr check-key --pdf ArXiv2307.08354 # one tiny request, no retry, 60 s timeout; prints OK or FAIL, model, time
$PY -W ignore -m tools.ocr transcribe ShenWang2019Vias --pages 1   # a stem in papers/pdf or a path; --pages '3,5-6', '10-', 'all'
$PY -W ignore -m tools.ocr queue --limit 20                # next pending lines of papers/ocr/QUEUE.md
$PY -W ignore -m tools.ocr queue --status                  # what is pending, requests today
$PY -W ignore -m tools.ocr suspects                        # suspect pages + printed/PDF page numbers
$PY -W ignore -m tools.ocr verify Lemczyk1992 --page 1     # HTML with the page image beside the transcription
$PY -W ignore -m tools.ocr decode FILE.md [--force]        # base-36 font cipher post-processor (ciphered pages only)
$PY -W ignore -m tools.ocr assemble Yovanovich2003    # one final Markdown in papers/md-final/<stem>.md (header, contents, cleaned and joined pages)
$PY -W ignore -m tools.ocr status show [STEM]           # reading status per page (papers/ocr/reading_status.json)
$PY -W ignore -m tools.ocr status set STEM 3,5-6 verified|corrected|machine --note "eqs 3-5 match the image"   # the reviewer's record
$PY -W ignore -m tools.ocr status seed                  # once: fill the file from the headers/markers of md-final and OCR_TO_VERIFY.md
$PY -W ignore -m tools.ocr transcribe STEM --pages 3 --provider anthropic --whole-page --max-tokens 16000 --subdir whole   # one request per page, no crops
$PY -W ignore -m tools.ocr firstline [--stem S] [--pages 1-5]   # offline: first line of each machine page against the PDF text layer -> notes/FIRSTLINE_REPORT.md
$PY -W ignore -m tools.ocr eqcheck [--stem S]           # offline: $ spans and \tag numbers against the text layer and the Gemini page -> notes/EQCHECK_REPORT.md
$PY -W ignore -m tools.ocr audit                        # offline: integrity of the assembled library -> notes/AUDIT_REPORT.md (exit 1 on an error)
$PY -W ignore -m tools.ocr transcribe STEM --pages 3 --prompt-variant NAME   # another phrasing of the prompt (data/prompt_variants.json; `default` is data/prompt.txt): the refusal filter is stochastic and sensitive to the wording
$PY -W ignore -m tools.ocr transcribe STEM --pages 3 --provider anthropic [--no-refusal-retry]   # on by default (`--refusal-retry` still accepted): a page refused whole and as two halves is tried as three strips (40 % tall, 10 % overlap) and joined at the overlap; worked for Lienhard2024 p17 and CulhamFourier2000 p1 where halves, all prompt variants and fallback models failed; a page that still fails goes to `--provider local` (no filter)
$PY -W ignore -m tools.ocr map                          # offline, no provider: papers/notes/OCR_MAP.md + ocr_map.json (what is done, what the theory still needs, tokens to finish)
```

Page numbers are PDF pages, 1-based (the `<!-- page N -->` markers use the same number). Exit codes: 0 ok, 1 failure,
2 stopped by the daily quota or `--daily-limit` (the rest stays pending for tomorrow), 3 refused (confidential file, key problem).

## Reading status of the pages (never overwritten)

`papers/ocr/reading_status.json` is `{stem: {page: {state, by, note, src_sha}}}`, `state` being `verified` (compared with the
image or the text layer, nothing to change), `corrected` (the reviewer changed the text) or `machine` (default, not compared).
`status set ... corrected` keeps the page text in `papers/ocr/corrected/<stem>_p<N>.md` (taken from `md-final` when the file
does not exist); `assemble` uses that file before any provider, does not clean or join it, and writes the state in the
header (`reading_status: {verified, corrected, machine}`, page ranges) and in the marker
(`<!-- page N | printed M | verified (image) -->`, `| corrected and verified (image)`, `| verified (text layer)`). A `verified`
page whose provider text changed since the check (`src_sha`) is written as `machine`. `status seed` fills the file once
from the hand-written headers and markers of `md-final` and from the `R` pages of `OCR_TO_VERIFY.md` (those only where the
page in use is a Gemini page, since that first pass compared Gemini pages) and never replaces an entry. A corrected page
that began with a word glued to the previous page by the old hyphen join is kept as the reviewer left it.

`--whole-page` sends one request per page (no half-page crops, no fallback model; a page cut at the token limit is kept
with a note), `--max-tokens` raises the output budget (Claude default 8192) and `--subdir` writes the pages into a
subfolder of the provider's output folder, so that a page already reviewed is not replaced. Claude refuses some pages
at random (a prose refusal or a content filter): the same page may pass on another attempt.

## The papers folder

`--papers`, else the environment variable `PCBT_PAPERS`, else `papers/` of the main checkout. It is ignored by version control
and holds third-party material that is never committed. Layout: `pdf/` the PDFs, `ocr/` per-page outputs `<stem>_p<N>.md` (converted from PDF to Markdown by online OCR; other providers write to `ocr/<provider>/`; an older library with `gemini/` and no `ocr/` keeps using `gemini/`)
(each starts with `<!-- page N -->`), the ledger `ocr/usage.json` and the queue `ocr/QUEUE.md`, `md/` local conversions,
`notes/SUSPECT_PAGES.md`, `verify/` the comparison pages.

## What it does

* **Providers** (`providers/`): `transcribe(image_bytes, prompt, options) -> Result`. `gemini` (online; default model
  `gemini-3.1-flash-lite`; models and fallbacks in `data/models.json`), `anthropic` (online; Claude through the Messages API, default model `claude-sonnet-5-5`, fallback `claude-opus-5-5`, `--model claude-haiku-5-5` for bulk pages; use `--provider anthropic` on `transcribe`, `queue` and `check-key`; outputs in `ocr/anthropic/`), `local` (offline; the maintainer's `extractpdf`
  MLX converter with the model `ovis`, a stub that was not run by the tests: set `PCBT_EXTRACTPDF` and
  `PCBT_EXTRACTPDF_PYTHON`; an output guard (`check_output`) refuses a page with the same line repeated more than 8 times
  in a row or longer than 1.6 times the expected length (`expected_chars`, default 7500 characters) and the page is
  converted again with the fallback model `unlimited` of `data/models.json`; a page cut short is not detected). A new provider is a class in `providers/` registered in `providers/__init__.py`.
* **Retry and quota**: HTTP 429 (per minute), 500 and 503 and network errors are retried (4 attempts) with the pause the
  server asks for (`RetryInfo.retryDelay`, at most 120 s) or else a pause that doubles (20, 40, 80 s); every retry is logged
  with its status. The error body is parsed as JSON in full: a 429 whose `QuotaFailure` has a `quotaId` with `PerDay` stops
  the run at once and records the page as pending (the quota id is about 900 characters into the body, after the long
  message). The ledger counts every HTTP attempt as a request. Three failures in a row also stop the run. Concurrency is 1,
  with a pause (`--pause`, 4 s) between requests. `check-key` makes a single attempt with a 60 s timeout (a silent
  20 + 40 + 80 s of pauses on a 503 or 429 was why an earlier key check seemed to take more than two minutes; the measured
  check takes about 1.5 s). An answer with text but a finish reason other than STOP (`MAX_TOKENS`, ...) is kept with the note
  "the text may be incomplete"; a blocked prompt is reported as `NO_CANDIDATE:<blockReason>`.
* **Anthropic provider**: the page is a base64 PNG image block plus the same prompt; headers `x-api-key` and
  `anthropic-version`, never the URL. 429 waits the `retry-after` header, 500/502/503/529 (overloaded) and network
  errors back off (20, 40, 80 s); an error that names the credit balance, a usage limit or a spend limit stops the run at
  once (exit 2, the page stays pending); 401/403 are not retried. `stop_reason` `max_tokens` (8192) is asked again as two
  half-page crops, `refusal` takes the RECITATION path (crops, then the fallback model). The response `usage` is kept
  in the ledger as `input_tokens` and `output_tokens` per page (`Ledger.tokens_today`); no price is stored (the field is
  `unverified` in `data/models.json`: read the current price list before estimating a cost).
* **OpenRouter provider** (`--provider openrouter`, key `OPENROUTER_API_KEY` or the line `openrouter=KEY` in `.ocr_keys`;
  outputs in `ocr/openrouter/`, every page file carries `<!-- model: openrouter:<id> -->`): the OpenAI-compatible chat
  API with `Authorization: Bearer` (never in the URL) and the page as an `image_url` data URL. The default model `auto`
  is resolved by one `GET /models`: ids ending in `:free`, with image input and zero prices, classifiers (`safety`,
  `guard`) left out, ranked (`dots`/OCR models, Qwen-VL, Gemma, Pixtral, Llama vision, ...) then by context; the best
  four are a chain tried in order when a model fails for a reason of its own (404, no image input, upstream 429, 5xx),
  within 3 requests per page. The free plan (about 20 requests per minute, 50 per day without credits) is respected
  client side: 3.2 s between requests, and the runner stops cleanly (exit 2, pages stay pending) at `daily_limit` 45 of
  `data/models.json` (counted in the ledger as provider `openrouter`) or at an error that names the daily limit or the
  credits. `Retry-After` is honoured. Priority of the sources in `assemble` and `map`: Claude, then OpenRouter, then
  Gemini, then the text layer (`assemble --order claude,openrouter,gemini` changes it); the header of the assembled
  file lists `disagrees_with_claude` (digits, equation count, word similarity, `compare.py`): Claude wins.
* **RECITATION**: a page refused by the copyright filter (empty answer with `finishReason` RECITATION) is retried as two
  half-page crops (top and bottom, 10 % overlap), then once with each fallback model. The output says which was used.
* **Assemble** (`assemble.py`, command `assemble <stem>...`): one Markdown file per PDF in `papers/md-final/`, deterministic from the
  per-page outputs. The page text is Claude's, else Gemini's, else `[missing]`; lines that repeat at the top or bottom of three
  or more pages and lone page numbers are removed; a word hyphenated across a page break and a sentence cut by a break are
  joined; every page keeps the marker `<!-- page N | printed M -->`; the YAML header holds the citation (from `notes/INDEX.md`),
  page counts, the pages of each provider, the files that cite the paper and `reading_status: machine`; a table of
  contents is built from the headings. Not done by the tool (it needs a reader): renumbering equations as in the paper,
  the reference list as a numbered list, figure descriptions and the section "Equations used by the program".
* **Resume**: a page whose output file exists is skipped unless `--force`. `--out FILE` also writes the pages of the run joined.
* **Ledger** (`usage.json`): one entry per attempt (date, provider, model, file, page, ok, seconds, words, requests, note).
  `--daily-limit N` stops after N requests today.
* **Queue**: the `| # | file | page | why |` table of `QUEUE.md`, or lines `file.pdf:page`.
* **Suspect pages**: low word count, undecoded equations, base-36 cipher, broken-font tokens, a garbage PDF text layer; each
  page is reported as `PDF N / printed M` and the file's usual offset (a paper quoted at "page 418" is a different PDF page).
  The printed number is read from a line that is only a number (or "Page N") at the top or bottom of the page, or from a
  journal line such as `JUNE 2003, Vol. 125 / 179`, or from a header that the pdfium text layer joined to the number on one line (`86 Chapter 2: Heat conduction`, `Problems 87`, `5.3. Moduli 77`; only the first and last two lines, and `suspects.printed_numbers` keeps such a reading only when it agrees with the file's offset, which is the mode of pdf - number over both kinds of reading; ligatures are expanded first, `suspects.normalise_layer`); when the file has an offset (the most common pdf - printed, at least two
  pages), every page's printed number is `pdf - offset`, because a single reading can be a table entry or a contents line
  (Lienhard2024: offset 14 on 753 of 765 readings, PDF 323 to 325 are printed 309 to 311; Muzychka2003: offset -177).
* **Verify**: one HTML file, page image left and transcription right. A transcription counts as read only after a reviewer
  has compared it with the page image. The transcription is untrusted text: it is HTML-escaped and a Content-Security-Policy
  forbids scripts, remote loads and forms.
* **Cipher decoder** (`cipher.py`): in some old PDFs the converter output is pairs of base-36 digits; each pair is a
  character code plus 360 (`D4D6CTD7` is `pres`; `AD` is the `fl` ligature). Only pages that look ciphered are decoded
  (`decode --force` decodes every page): decoding every token turned `AC` into `fi` and `DC` into `x`
  in ordinary text (24 tokens in TI-AN2020, 32 in SuperLUGuide). On a ciphered page digits and punctuation are decoded too,
  so equation numbers come back (`B4BKB5` is `(8)`). Muzychka2003Part1: 2942 tokens on 8 of its 9 pages; on pages 3 to 5,
  79 to 84 % of the decoded words are in the Gemini transcription (the rest are hyphenated splits such as `ther- mal`
  and words whose capital the converter dropped, `ne` for `One`). Capital letters that the converter dropped are not
  recoverable (use a Gemini transcription for those pages).

## The key

Looked up in this order: the environment variable the provider declares (Gemini: `GEMINI_API_KEY`, then `GOOGLE_API_KEY`; Anthropic: `ANTHROPIC_API_KEY`; OpenRouter: `OPENROUTER_API_KEY`), then the
file `.ocr_keys` in the project root (also in the main checkout when the tool runs from a worktree, found with
`git rev-parse --git-common-dir`). Format: one `provider=KEY` per line, `#` for comments. The file must be mode 600; a file
that group or others can read is refused with a message that does not contain the key. `.ocr_keys` and `*.key` are in
`.gitignore` (on branches older than this tool add `.ocr_keys` to `.git/info/exclude` too, which holds for every branch), and
`tests/test_no_secrets.py` fails if a key-like string is tracked (`AIza...`, `AQ.` keys with or without further dots, `sk-ant-` followed by 20 or more characters of any family (`sk-ant-api03-`, `sk-ant-usr-`),
`api_key = "..."`). `PCBT_SCAN_KEY_VALUES=1` also searches the tracked files for the exact values of `.ocr_keys` (opt-in, so
that routine test runs never read the key; the values never reach a message). The local converter is started without the
key variables in its environment.

The key is sent in a request header only. It is never printed, logged, passed on a command line, put in a URL, or written
in an exception message, the ledger or an output: every error text goes through `keys.redact()`, and the logging handler
redacts every record. If a key was ever pasted in a chat or a file, create a new one and replace the line.

## Privacy

Pages sent to Gemini leave this machine and go to Google; pages sent with `--provider anthropic` go to Anthropic (the maintainer decided online OCR is acceptable for open papers; check Anthropic's current retention and training terms for the key's plan before sending anything else). On the free tier Google may use the content to improve its
products. By the maintainer's decision this is accepted for open papers, and **never** for the confidential ODB++
specification or any file marked confidential: the tool refuses a file whose SHA-256 is listed in `data/confidential.json`
(a renamed copy of the ODB++ specification is refused although its name and its first page carry no mark: its word
"confidential" is on page 2), whose name or metadata matches a name pattern (the ODB++ title matches `odb\+\+.*spec`), or whose
metadata or first three pages say "confidential", unless `--allow-confidential` is given (only the maintainer authorises it).
A PDF that cannot be read for the check is not sent either. `check-key --pdf` passes the same guard. On the 110 PDFs of the
library the guard refuses only the ODB++ specification. The local provider sends nothing anywhere and is not subject to the guard.

PDFs are hostile input for pypdfium2 (PDFium, C++ code): pages are rendered one at a time and an oversized page is rendered at a
lower resolution (at most 40 million pixels); there is no time limit on a page, so open only files from known sources.

## Tests

`QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_ocr_tool.py tests/test_no_secrets.py` (no network, no PDF:
fake providers, a scripted HTTP layer). `tests/test_docs.py` and `tests/test_license_header.py` cover `tools/`.

* **Map** (`papermap.py`, command `map [--root DIR]`): offline and read-only (no provider, no key, no network). For every PDF in
  `papers/pdf` it writes the pages, born-digital or scan, the kind, whether an exact arXiv text exists, the pages done by Claude,
  by Gemini and by the local conversion only, the text-layer quality of every page (clean, formula-heavy by the density of equals
  signs and mathematical glyphs, garbage or empty) and the **essential pages**: those that the documents (`docs/theory.md`,
  `models.md`, `validation.md`, `calculators.md`, the bibliography) and the program quote by key with a page, table or equation
  number, plus the reviewer's list `OCR_TO_VERIFY.md`. Tiers: E1 essential and not verified against the image, E2 verified, O not
  cited; the tokens to finish use 7.5k per page. The page detection is a heuristic (printed pages shifted by the file's offset),
  stated as such in the output.

## Offline checks (`checks.py`; no provider, no key, no network)

* **`firstline`**: a typical Claude error is a sentence invented at the top of a page. For each page file of `ocr/anthropic`,
  `ocr/anthropic/whole`, `ocr/retry` and `ocr/corrected` (`--sources` changes the folders) the first text line of the machine
  page (figure descriptions skipped, `*(note)*` annotations and math removed) is compared with the first 12 lines of the PDF text
  layer of the same page: share of its tokens (NFKC, lower case, ligatures expanded) found there, at least 0.6 to pass. A token
  of four or more characters also matches the layer squeezed without spaces (old PDFs break words into fragments). Verdicts: `ok`;
  `moved` (the line is on the page but not at the top: running head, reading order); `FLAG` (not found: the reviewer looks at
  the image); `not checkable` (a scan or a layer with fewer than 25 words, a garbage layer, a page that starts with a formula or
  only a figure). Only born-digital pages with a usable layer are checkable, and a passed check proves nothing about the rest of the page.
* **`eqcheck`**: per page, the number of `$$..$$` and `$..$` spans and the equation numbers (`\tag{n}`, or a trailing
  `\qquad (n)`), against the formula density and the lone `(n)` lines of the text layer, and against the Gemini page when it
  exists (display count differing by more than a third; tag sets compared only when both sides have numbers, since Gemini often
  leaves them out). `(weak)` marks the case of equations drawn as images, where the layer has almost no formula glyphs.
* **`audit`**: `md-final` against `ocr/`, `pdf/` and `reading_status.json`: YAML header fields, page markers 1..N in order
  without a gap, `[missing]` where a Claude, OpenRouter, Gemini or corrected page exists (error: run `assemble`), the marker state
  against the sidecar (stale file), corrected pages used as they are, `corrected` entries without a file, page files beyond the
  PDF, stems without a PDF, key-like text (the patterns of `keys.KEY_PATTERNS`; only file and line are reported, never the text),
  and confidential files (name patterns or the SHA-256 of the PDF with the same stem) in `ocr/` or `md-final/`. The exit code is 1
  when an error is found. All reports are deterministic (no dates).
* `status set STEM PAGES verified` now refuses a page that has no provider text, no corrected text and no `md-final` chunk
  (it used to record a page that does not exist as compared with its image).
