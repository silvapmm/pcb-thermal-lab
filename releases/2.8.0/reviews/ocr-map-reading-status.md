# Review of `fix/ocr-map-reading-status`

**Verdict: GO** for the merge into `development`, with the two corrections below (on the branch). Developer tool only: `pcbthermal` never imports `tools/ocr`; no number of the program moves.

## What the branch does

`python -m tools.ocr map` (`tools/ocr/papermap.py`, `build_map`) counted a page as verified (tier E2) only from the notes `OCR_TO_VERIFY.md`, so every verification plan re-listed pages that `status set` had already recorded in `papers/ocr/reading_status.json`. The branch reads the sidecar through `status.effective`: a page in the state `verified` or `corrected` counts as E2; `e2_from_status` per file, `e2_from_status_pages` in the summary and one output line say how many came from the sidecar.

## Checks

1. **Semantics of `status.effective`.** Right for the map: a `verified` mark with the hash of the provider page (`src_sha`, recorded by `status set` and `seed`) falls back to `machine` when the page in use changed since the check (a new transcription, or a provider with higher priority added); a `corrected` mark without its corrected file falls back to `machine`. On the real library this lowers one page (a page verified on its Gemini text before an OpenRouter page took its place): correct. A page edited by hand in `md-final` after its mark is not seen by `effective`, but `assemble` takes the page from the provider or corrected file, not from `md-final`, so the mark still describes the text in use.
2. **`ERROR` note against the status file (corrected).** The branch let any `verified` or `corrected` mark win over an `ERROR` of `OCR_TO_VERIFY.md`. That note judged the Gemini page (the first pass). It is stale when another page is in use now (Claude, OpenRouter) or the text was corrected; but a `verified` mark on the *same* Gemini page cannot be ordered against the note (the error may have been found after the mark), so such a page now stays E1, the safe side. On the real library 8 pages carry an `ERROR` note and a status mark: all 8 use a Claude page now (7 verified, 1 corrected), so the correction moves no page there. New test `test_papermap_error_note_against_the_status_file` (fails on the author's commit).
3. **Summary totals (corrected).** `essential_pages` leaves out the arXiv and confidential files but `e2_pages` did not, so E1 + E2 did not add up (612 essential, 524 E2, 91 E1). E2 and `e2_from_status_pages` are now summed over the same files: 521 + 91 = 612.
4. **The tests fail without the fix.** `test_papermap_reads_the_status_file` fails on the `development` copy of `papermap.py`; the new test fails on the author's commit.

## The map on the real library (offline, read-only: `build_map` called directly, nothing written into `papers/`)

| tree | essential | E2 | of them from the status file | E1 to run | E1 with a Claude page, not verified | E1 the text layer covers |
| :-- | --: | --: | --: | --: | --: | --: |
| `development` (tool without the fix) | 612 | 33 | - | 17 | 473 | 89 |
| this branch after the merge and the corrections | 612 | 521 | 488 | 6 | 1 | 84 |

The author's numbers (616 essential, 450 E2, 417 from the status file, 25 to run, 76 to verify, 68 text) were taken before the later verification batches and before the merge of `development` (whose documents cite other pages); they are not reproduced on today's library and are not quoted in the repository.

**Reconciliation with the progress notes of the reviewers** (`papers/notes/VERIFY_PROGRESS_2026-11-15.md`, batches 1 to 3 and 7 to 16; `VERIFY_PROGRESS_B_2026-11-15.md`, batches 4 to 6 and 17): the 276 pages these two files report as verified, corrected or already verified are all `verified` or `corrected` under `status.effective` (0 missing). The sidecar holds 516 verified, 54 corrected and 1 machine entries; the one `machine` is a page with an `ERROR` note that was never corrected (Muzychka 2004, page 6), and it is among the 6 pages to run. The 7 essential pages still needing the model are exactly pages that no batch covered (Ibragimov 2023 p13, Saad's book p485, Jafarpur-Yovanovich 1997 p2, Milton p657 and p708, Muzychka 2003 p7, Muzychka 2004 p6). The 84 E1 pages the text layer covers are prose pages of born-digital files cited by key; the plan did not include them.

## Tests

`tests/test_ocr_tool.py`, `tests/test_no_secrets.py`, `tests/test_docs.py`, `tests/test_license_header.py`, `tests/test_version.py`: 889 passed, 5 skipped (4 need `pypdfium2`, absent in `.venv`; with `.venv-research` `test_ocr_tool.py` gives 102 passed; 1 needs `PCBT_SCAN_KEY_VALUES=1`, which gives 4 passed). `development` was merged into the branch first (one conflict in `CHANGELOG.md` [Unreleased], both sides kept). No API was called; `papers/` is not tracked.

## Not verified

The whole battery (the tester's, before the merge). The map was not written to `papers/notes/` (read-only run); `python -m tools.ocr map` writes `OCR_MAP.md` and `ocr_map.json` the next time a reviewer runs it.
