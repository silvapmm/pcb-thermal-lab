# Paper notes in git: is it possible, and under what rules?

**Research, not legal advice.** The author is an engineering agent reading public pages; nothing here replaces a lawyer. This folder is TEMPORARY (branch `tmp/paper-notes-policy`, never pushed, not merged): nothing in it enters `development` until the maintainer decides. The three pilot notes and the checker are illustrations, not adopted work.

## 1. The answer

**Possible, under conditions: yes for our own notes, no for anything that reproduces the source.**

| What | Verdict |
| :-- | :-- |
| A note in our own words: the idea, the method, the equations as facts with equation and page numbers, the numbers of the cases we test against, limits, how the program uses it, reading status | **Possible for every class of source** except the confidential one. It is what `research/theory/BIBLIOGRAPHY.md` (286 entries, 240 distinct keys) and `docs/theory.md` already do today, so the practice is not new. |
| A summary that follows the source sentence by sentence (close paraphrase), a machine-condensed rewrite of the OCR text, long quotations | **Not possible** (a derivative of the expression) unless the source licence allows adaptation (CC BY, CC BY-SA, public domain). |
| Figures, a table copied whole, the OCR text, a transcription | **Not possible** for copyrighted sources; possible only for CC BY / CC BY-SA / CC0 / public-domain sources, with attribution and a marked-as-modified notice, and the earlier opinion (`releases/2.7.0/final-opinion/papers-in-git-opinion.md`) recommends against even that for now. |
| Standards (JEDEC, IPC, ISO, IEC, Gerber/Ucamco text) | **Possible only in a thin form**: the citation and the few numbers or formulas we test against, with the clause or table id; no restatement of the normative text. Publishers say plainly that reproducing any part needs permission (IEEE standards: even a small amount; JEDEC: "all rights reserved"). |
| Vendor datasheets and application notes (TI, Infineon, ROHM) | **Possible as facts**: the datasheet value we compare against, with the document id. Their terms allow personal or non-commercial copying unchanged, not republishing in modified form. |
| The confidential ODB++ specification | **Not possible**: nothing beyond the bibliographic entry the guard already allows. |

The risk is not the idea of notes; it is (a) a note that drifts into close paraphrase, (b) a note made by a model from the whole text without a human check of "own words", (c) the public, rewrite-forbidden history: a takedown would force either breaking the no-rewrite rule or losing the repository (README 5). The rules of `INTEGRATION.md` answer these.

## 2. Evidence

### 2.1 Law (statuses: R read on the official or primary page, S search snippet or summary, M memory, N not obtained)

| Point | Finding | Status |
| :-- | :-- | :-- |
| Ideas, methods, mathematical concepts are not protected, whatever the form in which they are described | 17 USC 102(b): no protection "to any idea, procedure, process, system, method of operation, concept, principle, or discovery", regardless of the form in which it is described, explained, illustrated or embodied (copyright.gov, first 100 000 characters of the chapter) | R |
| Facts are free, the arrangement of a compilation is protected thinly | Feist v. Rural (US 1991): facts not original; a compilation is protected only in original selection and arrangement ("thin"), not the facts; sweat of the brow rejected (the opinion's own page was blocked, 403; read through search summaries of Cornell LII / govinfo texts) | S |
| Berne | Art. 9(1) authors' exclusive right of reproduction "in any manner or form"; Art. 9(2) exceptions only in special cases not conflicting with normal exploitation; Art. 10(1) quotation from a lawfully published work, "compatible with fair practice", extent not beyond the purpose (WIPO Lex text). The idea/expression principle itself is WCT Art. 2 / TRIPS Art. 9(2), **not opened** | R for the Berne articles, M for WCT and TRIPS |
| EU quotation | Directive 2001/29 Art. 5(3)(d): "quotations for purposes such as criticism or review", the work already lawfully made available, source and author named unless impossible, fair practice, not beyond the specific purpose; Art. 5(5) three-step test (consolidated text on legislation.gov.uk). EUR-Lex itself was not reachable. CJEU Spiegel Online (C-516/17) read only through summaries | R (text), S (case) |
| EU text and data mining | Directive 2019/790 Art. 4: any user with lawful access may copy and extract for TDM, kept as long as needed, **unless rightholders expressly reserved their rights in an appropriate manner (machine-readable for online content)**; Art. 3 is the research-organisation exception. The opt-out is unsettled in practice (commentary) | R (text), S (commentary) |
| Portugal | CDADC art. 75 lists free uses incl. quotation; a consumer guide (DECO) says quotations and summaries of protected works are allowed when they support the doctrines defended in the work or serve criticism, discussion or teaching. The wording of art. 75 itself was not reached | S |
| US fair use | 17 USC 107: four factors (purpose and commercial nature; nature of the work; amount and substantiality; market effect) (copyright.gov). Not the governing law for a Portuguese maintainer, but a US-hosted public repository can meet a DMCA notice | R |
| US government works | 17 USC 105(a): no copyright in a work of the US Government (the Government may hold assigned copyrights) | R |
| CC BY 4.0 | Allows reproduction and sharing in whole or in part and adaptation, with attribution, licence reference, indication of changes; moral rights not licensed; where fair use or an exception applies the licence is not needed | R |

**Consequence.** A summary in our own words of ideas and facts is generally on the free side of the line; the line is crossed by expression: wording, structure that tracks the source, figures, whole tables. How short a quotation must be is not a number in any of these texts ("extent not beyond the purpose", "fair practice"); the proposal uses 25 words as a conservative house rule, not as law.

### 2.2 Publisher and licence pages read (the terms of the classes we cite)

| Source | What the page says | Status |
| :-- | :-- | :-- |
| arXiv, licence help page | Authors choose CC BY 4.0, CC BY-SA, CC BY-NC-SA, CC BY-NC-ND, the arXiv non-exclusive licence, or CC0; the default arXiv licence gives arXiv the right to distribute and "limits re-use of any type from other entities or individuals" | R |
| arXiv abstract page of Jaffer 2201.02612 | links to the arXiv non-exclusive licence (so the preprint is NOT CC BY, although the journal version in Thermo (MDPI) is open access: the version matters) | R |
| Creative Commons BY 4.0 legal code | see 2.1 | R |
| Frontiers | all articles CC BY ("unrestricted use, distribution, and reproduction in any medium" with credit) | R |
| Springer Nature, open science page | OA articles carry Creative Commons licences; subscription articles do not (authors may archive the accepted manuscript after an embargo) | R |
| Elsevier, text and data mining policy | subscribers may text mine for non-commercial research; others by permission helpdesk; the page says nothing on CC BY articles or on redistributing extracted text | R |
| IEEE rights page (short summary content returned) | reuse of portions of an IEEE article generally needs permission; open-access articles are CC BY; "brief excerpts" are named as a permitted form | S |
| ASME rights and permissions | ASME holds copyright; including a paper "or some or all of its elements" in another work needs ASME permission via CCC; authors keep rights to ideas and processes | R |
| TI website terms of use | services protected; without written consent not to be copied, modified or redistributed; personal or non-commercial download, copy and share allowed **unmodified with notices kept**; classroom use credited; no statement about datasheets as such | R |
| Infineon (website terms copy and 2026 documentation notice, via search) | personal or non-commercial reproduction without modification and with notices; documents reserve commercial text and data mining (German Copyright Act s. 44b); "All Rights Reserved" | S |
| ROHM (website terms and datasheet notices via search) | content protected; datasheet notice: no reproduction in part or whole without ROHM's consent; no licence granted | S |
| JEDEC copyright information (via search) | JEDEC owns the copyright; files may be downloaded free; distributing them otherwise needs purchase or written permission; downloaders agree not to charge for or resell | S |
| IPC (via search) | no IPC-specific page found; Techstreet says IPC protects its publications; IEEE and ISO/IEC pages say that even small reproductions from a standard need permission | S |
| Lienhard, *A Heat Transfer Textbook* (MIT page, via search) | free to download from the authors, copyright 2000-2024 kept; no Creative Commons licence found: free to read is not a licence | S |
| Wiley and Springer Nature text and data mining (library guides, via search) | non-commercial TDM for subscribers, through an API and agreement; nothing found on publishing results or snippets; UChicago guide: derived information may be public, the source documents may not be redistributed | S |
| Elmer Models Manual and OpenFOAM User Guide licences (via search) | Elmer Models Manual 2023: CC BY-ND 3.0; OpenFOAM User Guide recent versions: CC BY-NC-ND 3.0 (older OpenFOAM guides GNU FDL): open-source software, yet **documentation that forbids derivatives** | S |

Not obtained (N): MDPI open-access page (403), Springer Nature TDM page (404), EUR-Lex (page blocked), Justia's Feist (403), JEDEC terms page (404), Infineon legal notice (404), ROHM terms (404), SIAM (403), AIAA (404), the IIETA licence, the OpenFOAM guide page (404), the Elmer site (403). The licences of Thermo (MDPI), IIETA, and the PDFs we hold are therefore **M or unchecked**; all 282 non-confidential entries of the bibliography still say `Licence: not checked` (only 3 `public domain`, 1 `confidential`).

### 2.3 What open-source scientific projects do (three examples, 3.3 below)

1. **SciPy** (`scipy.sparse.linalg.splu`, read): one sentence naming the library used and a numbered references list with a link; parameters point to the section of the SuperLU users' guide; no text of the guide is reproduced (R).
2. **Elmer** and 3. **OpenFOAM** (licences only, via search): the manuals describe the models with their formulas and cite the literature, and are themselves CC BY-ND / CC BY-NC-ND; nobody can adapt them, which is the position our notes would be in with respect to the papers if we copied expression (S). The practice shared by all three: **name the source and the clause, give the formula, say what the code does; do not carry the source's prose**.

### 2.4 Machine-made notes: provider terms

Anthropic commercial terms (read): the customer owns the outputs, **but must have all rights and permissions to submit the inputs** (section L.1), and defends Anthropic against claims tied to its inputs (K.2); the paid-use indemnity excludes the customer's own inputs (K.3). Google Gemini API terms (read): Google does not claim ownership of generated content; the free tier uses submitted content and responses to improve its products and humans may read them; "do not submit confidential information". So: **owning the output of a model gives no right over the work it was fed**; the copyright question is that of 2.1, and the provider adds the responsibility for feeding it only material we may use (open copies for the free tier, as CLAUDE.md already says). EU Art. 4 TDM is a defence for the copying done in the process only where no opt-out was reserved (Infineon says it reserves one); that concerns the analysis, not the publication of the result.

## 3. Classification of the keys (`scripts/study_classify_keys.py`)

Heuristic from the citation text, with 40 keys classified by hand: an **estimate to plan the work**, not a licence finding (the licence of an entry is not checked). 240 distinct keys:

| Class | Keys | May keep (rule of INTEGRATION.md 2) |
| :-- | --: | :-- |
| Journal or conference article (IEEE, ASME, AIAA, Elsevier, SIAM, Springer, ...) | 81 | own-words summary; formulas and numbers with equation and page |
| Vendor note, datasheet, software documentation, magazine of a vendor | 50 | facts with the document id; summary of what we use |
| Standard or specification (JEDEC, IPC, ASTM, ASHRAE, Gerber/Ucamco) | 38 | citation plus the numbers we test against with the clause; no restatement |
| Book, lecture notes, reference work | 33 | references only (equation, page) plus our own account |
| arXiv or open preprint | 14 | as a journal article; more only if the paper's own licence is CC BY / CC BY-SA / CC0 (read it on the abstract page; the preprint and the journal version can differ) |
| Thesis | 10 | as a journal article |
| US government report (NIST, NACA, NASA, DTIC, OSTI) | 12 | public domain in the US (17 USC 105), still written in our words; formulas and numbers freely |
| Confidential (ODB++) | 2 | nothing beyond the citation |

Open-licence candidates (CC BY / public domain): 3 entries already marked `public domain` plus perhaps 5 to 10 gold-open-access items (Frontiers, MDPI-type journals) whose licences have **not** been read per paper: M until checked. A class never makes an exception to the "own words" rule; an open licence only relaxes it.

## 4. Pilot: three notes (`notes_pilot/`, illustration only)

| Note | Class | Check by `check_note_similarity.py` against the local text |
| :-- | :-- | :-- |
| `Jaffer2023.md` | open-access journal article (CC BY, M) with an arXiv preprint (arXiv licence, R) | no flag |
| `YovanovichJafarpur1993.md` | institutional report (copyrighted) | no flag (after the checker excluded the citation line: it first flagged 12 words, the title) |
| `Lienhard2024.md` | book (copyrighted, free to read) | no flag |

Each is 310 to 360 words with its header fields, has no figure, no quotation (none was needed), the equations as facts with their numbers, and the program use. The checker is a prototype with first-guess thresholds (run of 8 identical words, 5 % shared 6-grams), tested on synthetic text only (`tests/test_similarity.py`, 3 passed); **it cannot decide close paraphrase, only copied words**, so the reviewer's "own words" reading stays. The facts of the notes were taken from `research/theory/BIBLIOGRAPHY.md` and re-checked against the local text for the equation numbers and the Jaffer bias values; the pages of Yovanovich and Lienhard rest on the earlier image checks recorded there (not re-done here).

![what crosses the line](figures/fig_01_paper_to_note_line.png)

*Figure 1, fig_01_paper_to_note_line.png: the paper and its verified transcription stay on the local side; only the own-words note crosses into git, checked by a local similarity tool and a repository test.*

## 5. Risks and what a takedown would look like

- **Close paraphrase.** The failure mode: a note written by condensing the OCR text. Counter: template limits, the similarity tool, a human (reviewer) reading for "own words".
- **Machine notes.** Provider terms add no right over the source (2.4); a model that sees the whole paper tends to follow its order and phrases. Counter: the note is written from our verified findings (formulas, cases, page ids), not from a request "summarise this paper", and is reviewed.
- **Public history.** The repository is public; published history is never rewritten (CLAUDE.md). A rightholder notice to GitHub would ask to remove a file or the repository; removing a file from history would require the forbidden rewrite, so a mistaken copy is costly for ever. This is the reason for a conservative template and a test that blocks the accident before the commit.
- **Standards and vendors** are the strictest classes: JEDEC, IEEE, ISO/IEC say even small reproductions need permission; keep these notes to facts and ids.
- **Not checked.** Per-paper licences, Portuguese art. 75 wording, EU quotation case law beyond summaries. A lawyer should look before any commercial version or distribution of a bundle.

## 6. What was read and what was not verified

- Read (R): the pages marked R in 2.1 and 2.2; the existing opinion `releases/2.7.0/final-opinion/papers-in-git-opinion.md`; `tests/test_third_party_text.py`; `research/theory/BIBLIOGRAPHY.md` structure; the local text of Jaffer (equation 2 and the vertical conformance biases) and the headings of the Yovanovich report and Lienhard text, to write the pilot notes (nothing copied).
- Snippet or summary (S): Feist, Portuguese art. 75, CJEU case, JEDEC, IPC, Infineon, ROHM, Lienhard licence, Wiley/Springer TDM, Elmer and OpenFOAM licences, the IEEE rights page.
- Memory (M): WCT and TRIPS idea/expression, the licence of Thermo (MDPI), the classification of individual keys by publisher (heuristic).
- Not obtained (N): the pages listed at the end of 2.2.
- Not verified: the class counts are heuristic; the similarity thresholds are not calibrated; the pilot notes were not reviewed by the reviewer agent; no lawyer.
