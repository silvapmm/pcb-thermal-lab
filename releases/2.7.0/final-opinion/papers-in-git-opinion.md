# Reviewer opinion: may the papers/ conversions or summaries go into git?

Read-only opinion. I am an engineer reviewing practice, **not a lawyer**; this is not legal advice. Where a
clause of a law or of a provider's terms is quoted from memory and was not re-read for this opinion, it says so.

## 0. What was looked at (not the papers themselves)

- `papers/README.md`, `papers/notes/INDEX.md`, `papers/arxiv/INDEX.md`, the file list of `papers/pdf/` (117 PDFs),
  sizes and counts: `papers/ocr/` 1031 page files (10 MB), `papers/md-final/` 69 assembled files (8 MB),
  `papers/md/` older local conversions (6.5 MB), `papers/arxiv/` 12 LaTeX sources, `papers/notes/` 0.9 MB.
- `papers/` is ignored by `.gitignore:30`; `git ls-files` holds no file under `papers/` and no tracked Markdown carries
  the OCR markers (`<!-- page N -->`, `reading_status: machine`) except `tools/ocr/README.md`, which only describes them.
- The repository is **public** on GitHub (`gh repo view`: `PUBLIC`).
- No licence was checked per paper: none of the indexes records a licence. The classes below come from file names, the
  hosts in `INDEX.md` and general knowledge of the publishers; every "possibly open" entry must be verified on its
  landing page before anything is done with it.

## 1. Approximate licence classes of the 117 PDFs (estimate, not verified)

| Class | About | Examples | Redistribution of the full text |
| :-- | --: | :-- | :-- |
| Waterloo MHTL group papers (IEEE, ASME, AIAA, ITherm prints, archive copies) | 47 | Culham*, Yovanovich*, Lee*, Teertstra*, Muzychka*, Negus* | No: publisher or author copyright; an author's archive copy is permission to read, not to republish |
| Other journal articles (Elsevier, SIAM, AMS, Springer, ...) | 15 to 17 | CalhounLeVeque2000, Crockett2011, Helzel (3-43028), Trans. AMS 1954, Mondragon2025, Rodero2025, ShenWang2019, IIETA | No by default; a few may be gold open access under CC BY (Rodero, Mondragon, IIETA: **check**) |
| arXiv | 12 | DorflerBullo, Gjerde, Koch, Jaffer x2, Ibragimov x2, FastDirect, OPM, Kron, ArXiv2307, EymardGallouetHerbin | Depends on the licence chosen at submission. The arXiv default (non-exclusive licence to distribute) gives **arXiv** the right, not us. Only those marked CC BY / CC BY-SA / CC0 qualify: **check each** |
| LBNL / University of California reports and eScholarship copies | about 9 | Johansen x2, McCorquodale, qt0fp606kk, FourthOrder EB, LiSuperLU, ASHRAE2005 LBNL, ebchombo | No: contractor work, copyright UC (US government keeps a licence, we do not); some eScholarship items carry CC: **check** |
| US government works | 3 | NISTIR 7648, Ostrach NACA TN 2635 and Report 1111 | Public domain in the US (17 USC 105, from memory); outside the US the position is less clear but the practical risk is low |
| Theses | 3 to 4 | Razavi2016, Fish2017, SoleymaniKoohbanani2016 | Author's copyright; repository licences vary (some CC BY-NC-ND): **check** |
| Books, lecture notes, slides | about 7 | Saad (two books), Lienhard 2024, Milton, Khouider, Davis slides | No: free to download is not a licence to redistribute (Lienhard's textbook is free to download, copyright kept, from memory) |
| Standards, manuals, application notes | about 20 | Gerber 2016/2024/2026, Gerber Job, XNC, KiCad manual, TI, Infineon, ROHM, Isola, Bittele, SuperLU and UMFPACK guides | No, except the KiCad documentation (GPL-3.0-or-later or CC BY 3.0-or-later, from memory: check) |
| **Confidential** | 1 | OdbppSpec81U4 | **Never**: not committed, not converted, not summarised beyond what the guard already allows |

So: about 95 % of the library is all-rights-reserved material. The candidate set for redistribution is small: the 3 US
government reports, perhaps 3 to 8 arXiv / gold open-access items, and the KiCad manual, each only after its licence is
read on the landing page.

## 2. (a) A full transcription is a reproduction

A Markdown conversion of a whole paper or book chapter (machine OCR, cleaned and assembled) is a **reproduction** of
the work (and, where cleaned and restructured, an adaptation), not a transformative use. It keeps the expression: the
running text, the selection and arrangement of the tables and figures captions, the order of the derivation. Publishing
it in a public repository is a communication to the public. In the EU and Portugal (Código do Direito de Autor e dos
Direitos Conexos, art. 75, and the InfoSoc Directive 2001/29, art. 5, from memory) the exceptions that matter are
private copy, quotation "for criticism, review or teaching" to the extent justified, and the text-and-data-mining
exception of the DSM Directive 2019/790 (arts. 3 and 4, transposed in Portugal in 2023, from memory); **none of them
allows republishing a full text**. US fair use is not the governing law for a Portuguese maintainer and would not cover
a verbatim full text either. The local folder as it is (open copies, read and converted for our own study, never
distributed) sits within private and research use; publishing it would not.

Equations and tables: a formula, a physical law, a correlation and its constants are **facts / ideas**, not protected
as such (Berne / TRIPS principle: ideas, methods and mathematical concepts are not protected). Their typeset form in a
paper and a whole table copied as a block can be part of the protected expression, and a systematic copy of many tables
of one source is closer to reproduction. Writing `Nu = 0.475 Ra^(1/5)`, "eq. 25, p. 8" in our own text is safe; pasting
the paper's table 3 entire is not, unless short and needed for the comparison, quoted with the source.

## 3. (b) What is safe to commit

- **Bibliographic data**: authors, title, venue, year, DOI, source URL, page counts, our reading status (R/S/M/N),
  the SHA-256 of our copy. Facts, not expression.
- **Formulas, constants, published numerical cases, with equation and page numbers**, written in our notation and our
  sentences (what `docs/theory.md` and `research/theory/BIBLIOGRAPHY.md` already do). Numbers read from plots marked
  "plot".
- **Our own summaries and notes in our own words**: what the paper does, what it supports in the program, where it
  disagrees, its limits. A summary must not be a close paraphrase that follows the paper sentence by sentence; a
  summary generated from the OCR text is fine only if it is written as our account, not a condensed rewrite.
- **Short quotations** (a sentence, a defining line, one small table where the comparison needs it) with the full
  citation and page, justified by the review or the teaching purpose (CDADC art. 75(2)(g), from memory). Keep them
  rare and short; "short" is not a number of words in law, so be conservative.
- **Our reproduction code and its outputs** (independent solvers in `research/<topic>/lib/`), which re-derive the
  published case rather than copy it.

## 4. (c) What depends on the licence of each source

A converted full text may be committed **only** when its licence allows redistribution and (because OCR cleaning is a
modification) adaptation:

- **Allowed**: public domain (US government works; state the jurisdiction), CC0, CC BY, CC BY-SA. With CC BY, keep
  the attribution, the licence name and link, and say that it was modified (machine conversion, possibly with errors).
  With CC BY-SA the converted file stays CC BY-SA.
- **Not committed**: CC BY-ND (a cleaned OCR text is a modification; CC 4.0 says mere format shifting is not an
  adaptation, but our cleaning and assembling go beyond it, and OCR errors misrepresent the work), CC BY-NC and NC-SA
  (compatible with a non-commercial repository today, but the maintainer has left a commercial version open, and NC
  text inside the repository would bind it), the arXiv default licence, "free to read" archive copies, and anything
  without a licence statement.

In practice this is fewer than about 10 files. I do not think the gain (a better search copy in git) justifies the
work and the risk now: the arXiv LaTeX source, which is better than any OCR, is one `curl` away for exactly the items
that might qualify.

## 5. (d) MIT repository, public repository

- The repository statement is "everything of ours is MIT". Third-party text in it must be marked as not ours: its own
  folder, a `LICENSE`/`NOTICE` or a manifest entry per file with the SPDX identifier, the attribution and the source
  URL; `README.md` "Author and license" and `LICENSE` would have to name that exception (the rule in CLAUDE.md
  'Licences' requires the four statements to change together).
- CC BY-SA files may sit beside MIT code as separate works; they do not relicense the code and the code does not
  relicense them.
- **Public repository and this project's history rule**: the repository is public and published history is never
  rewritten (no force push). A copyrighted full text committed by mistake and pushed stays in the history for ever unless
  the rule is broken; a DMCA notice to GitHub would take the repository (or the file) down and would force exactly the
  history rewrite the project forbids. This alone argues for keeping every conversion out of git by default and for a
  test that blocks it before a commit is made.
- Volume: 10 to 25 MB of text per pass would also bloat a code repository that has to stay small.

## 6. (e) Provider terms

The pages went to Google (Gemini, free tier) and Anthropic. From memory, not re-read for this opinion: both sets of
terms leave the output to the user (Google does not claim ownership of generated content; Anthropic's commercial terms
assign outputs to the customer) and both forbid using the service to infringe third-party rights. **Owning the output of
a transcription gives no right over the transcribed work**: the copyright question is the one of section 2, the
provider terms add no permission. Two practical points: (1) the free Gemini tier may use the inputs to improve Google's
products (recorded in CLAUDE.md), so only open copies should go online, as the rule already says; (2) the RECITATION
refusals of Gemini on some pages are the provider's own signal that the output reproduces protected text.

## 7. (f) ODB++ and confidential files

Never: not committed, not converted, not sent online, not summarised in a committed file beyond the bibliographic entry
(and only if the maintainer wants that entry). The SHA-256 guard of `tools/ocr` already refuses it; the commit side
should have the same guard (section 9).

## 8. Recommendation

1. **Keep local only** (as today): the PDFs, `papers/ocr/`, `papers/md-final/`, `papers/md/`, `papers/arxiv/`,
   `papers/verify/`, the ledger and the OCR working notes in `papers/notes/` (they quote pages and text of the papers).
2. **Commit** (already the practice, keep it): our summaries and notes in our words, formulas and cases with
   equation and page numbers, short quotations with citation, inside `research/theory/BIBLIOGRAPHY.md`, the research
   READMEs and `docs/theory.md`.
3. **Add a licence column to the bibliography** (worth doing): for every source, `licence` (SPDX id, `PD-US`,
   `all-rights-reserved`, `unknown`, `confidential`) and `source_url`, checked on the landing page. This is useful in any
   case: it says which sources a later study may quote at length.
4. **Converted full text in git: not now.** If the maintainer wants it later, only for sources with `PD-US`, `CC0`,
   `CC-BY-*` or `CC-BY-SA-*`, in one folder (for example `research/sources-open/`) with a `MANIFEST.json` (file, key,
   licence, attribution, source URL, SHA-256 of the source PDF, "machine conversion, modified, may contain errors"),
   the folder excluded from the MIT statement in `LICENSE` and `README.md`. Prefer the arXiv LaTeX source over OCR.
5. Let a lawyer look before any commercial version or any bundle that ships third-party text.

## 9. Minimal enforcement (a test in the battery)

`tests/test_third_party_text.py`, over `git ls-files`:

- fails if any tracked path starts with `papers/`, or any tracked file outside the allowed folder contains the OCR
  markers (`<!-- page N`, `reading_status: machine`, the assemble YAML header), `tools/ocr/README.md` and the tool's
  own tests excepted by name;
- for the allowed folder (if ever created): fails if a file has no `MANIFEST.json` entry, or its licence is not in the
  allow list (`PD-US`, `CC0-1.0`, `CC-BY-*`, `CC-BY-SA-*`), or the entry lacks attribution or source URL;
- fails if any tracked file has the SHA-256 of a confidential file of the `tools/ocr` guard or contains the
  confidential title strings (ODB++).

It is about 60 lines, runs in under a second and catches the accident (a `git add -A` in a worktree, as happened with
the `.venv` symlink) before it reaches the public history.
