# Integration: a policy for paper notes (a proposal; nothing is adopted)

Folder of the investigation `research/paper-notes-policy` (reviewed: README 6, GO). If the maintainer adopts it, the rules go to a `docs/` branch (CLAUDE.md, the papers library rules) and the notes to roadmap item F10 (the Thermal Sources Atlas); this folder is the record of the reasoning. No change to `pcbthermal/`, `tests/`, `docs/` or `CLAUDE.md` was made here. Research, not legal advice.

## 1. Decision in one line

Keep in git **own-words notes** (facts, equations with equation and page numbers, numeric cases, limits, program use, reading status); keep **everything that reproduces expression** (PDF, OCR text, transcriptions, figures, whole tables, close paraphrase) local in `papers/`. It is already the practice of `BIBLIOGRAPHY.md`; the proposal makes it explicit, per key, and checkable.

## 2. Rules by class (what a note may keep)

| Class | Summary in own words | Equations and numbers as facts with refs | Table values | Figures, text, OCR |
| :-- | :-- | :-- | :-- | :-- |
| Open licence (CC BY, CC BY-SA, CC0, public domain), licence READ on the paper's page | yes | yes | the numbers we test, with the table id | no by default (a later `sources-open/` folder only with a manifest, see the 2.7.0 opinion) |
| US government work (written by government employees; a report only hosted by NTRS, DTIC or OSTI does not qualify) | yes | yes | yes, the numbers we use | no |
| Journal, conference, thesis, arXiv (default licence), report | yes, at most 150 words | yes | only the numbers we test against, with the table id | no |
| Book, lecture notes | short account of what we use | references (equation, page) with the formula | same | no |
| Vendor note, datasheet | what we use | the value and its document id | the compared numbers | no |
| Standard (JEDEC, IPC, ISO, IEC, Gerber/Ucamco) | one sentence of scope | only what we test against, with the clause id | no | no |
| Confidential | nothing beyond the guard's bibliographic entry | no | no | no |

Never: a quotation over 25 words (house rule, not law), more than one per note, a paragraph in the paper's order, an OCR marker, an image, a sentence-by-sentence condensation.

## 3. Template (a file `research/theory/notes/<key>.md`, one per key)

Fields (the prototype checker tests `Key`, `Reading status`, `Licence of the source`, `Summary` and `Used in the program`; the others are for the reviewer until a test covers them): `Key`, `Citation` (bibliographic data only), `Reading status` (R, R-, S, M, N, L with the pages), `Licence of the source` (SPDX or `all rights reserved` or `not checked`, with the URL read) and `Class`; sections `Summary` (one paragraph, at most 150 words, our account), `Equations used as facts` (our notation, symbols defined, equation and page), `Numerical cases we test against` (numbers, where printed, marked "plot" when read from a figure), `Limits and caveats`, `Used in the program` (module, theory section, study). Pilot examples: `docs/notes-pilot/`.

Where they live: `research/theory/notes/<key>.md` beside `BIBLIOGRAPHY.md`, which stays the index (one line per key, pointing to the note when it exists). The bibliography entry keeps the licence field (today `not checked` for 281 of 290 entries: filling it by reading each landing page is the first real cost of the policy).

## 4. Guard changes (`tests/test_third_party_text.py`)

Keep the existing tests (no path under `papers/`, no OCR markers, confidential titles and hashes, licence field present). Add, for the files of `research/theory/notes/`:

1. required fields and sections present; `Summary` at most 150 words; no quotation over 25 words, block or inline; at most one quotation; no image link and no `<img`; the citation line holds bibliographic data only (the prototype skips that line in the similarity test, so a test of its length is needed);
2. no line identical to a line of another note (catches a paste of the same paragraph);
3. the licence value of a note is one of the allowed values and, for `CC-BY*`, the note carries the attribution line.

Do NOT make CI compare notes with the papers: `papers/` is absent in a clean clone. Instead keep the **local similarity tool** (`scripts/check_note_similarity.py`, to be moved to `tools/` if adopted): run by the author and the reviewer before every commit of notes, against the text in `papers/`; flags: a run of 8 or more identical words outside a formula, more than 5 % of the 6-grams found in the paper. The thresholds are a first guess; on the three pilot notes an honest note gives a run of 3 to 4 words and 0 % of 6-grams, a pasted passage of 40 words a run of 40 and 12 to 17 % (README 4); calibrate on the first 20 notes with shorter pastes (target: no flag on honest notes, a flag on a deliberately copied sentence of 10 to 15 words). The class of a key comes from `scripts/study_classify_keys.py` only for the strict classes (standard, US government work, confidential: every key read by hand); for the others it is about 20 % wrong and the class is set by the author of the note from the source itself.

## 5. Who writes them

1. The **researcher** (or executor) writes the note from the verified findings of the study and the page images, **not** from a "summarise this paper" request to a model, and not from the transcription alone.
2. The author runs the similarity tool locally.
3. The **reviewer** reads each note against the template and the "own words" rule and signs it in `research/REVIEW.md`; a note without that is a draft and is not committed.
4. The maintainer commits (stage by path; `git ls-files papers` must stay empty).

## 6. Plan per key

1. Fill the licence by class on the landing pages for the keys with status R that the program's formulas rest on (about 140 entries mention Status R; the first set is those cited by `docs/theory.md` sections 1 to 11): about a week of reading pages, the main cost.
2. Notes first for: the convection laws (Lienhard, Yovanovich-Jafarpur, Jaffer, Goldstein-Lau), the spreading and via models (Muzychka, Culham-Yovanovich, Lee), the numerical methods that fix a number (Saad, SuperLU guide section used, Peaceman), the standards numbers (JESD51 family, TI/Rohm cases). A pilot of 20, review, then decide whether to continue.
3. Standards and vendor notes last and shortest.
4. Do not start the conversion of full texts into git (the 2.7.0 opinion stands).

## 7. Decisions for the maintainer

1. **Adopt the principle?** (own-words notes in git, all else local). Recommended: yes, as a documented rule in CLAUDE.md "Licences" and "Papers library", because it is already the practice and makes the line explicit.
2. **Per-key note files or keep the BIBLIOGRAPHY entries as they are?** The entries already hold the same facts. Files add structure and a place for the checker; they add the risk of more text. Recommended: pilot 20 files, then decide.
3. **Who signs** "own words": the reviewer (recommended).
4. **Quotation limit:** 25 words and one per note (house rule), or none. Recommended: 25 words and one per note (no text read gives a number; the pilot needed none).
5. **Licence column:** read the landing pages for the keys of the pilot (recommended) before any claim of an open licence.
6. **A lawyer** before a commercial version or a bundle that ships notes.
7. **Machine drafts:** forbid a model draft that was given the full paper text; allow a model to help format a note written from our findings (recommended).
