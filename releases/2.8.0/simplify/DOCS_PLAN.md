# Plan: simplify the theory and the documentation (2.8.0)

Reviewer's plan, made on `docs/simplify-docs-plan` from `development` e7dfb609. It is a plan: the only change made
now is the move of the four history sections of `docs/validation.md` (section 6 below, `DOC_MOVES.md`), because
the FEM branches and the surface read-out still edit `docs/theory.md`, `docs/models.md`, `docs/validation.md`,
the README, the CHANGELOG, `docs/versions.md` and the user guide, and a rewrite now would collide with them.
`CLAUDE.md` and `.claude/agents/` are out of scope (their own branch, `docs/simplify-claude-md`).

The numbers of sections 1 and 2 are printed by `scripts/analyse_docs.py` (run from the repository root) on e7dfb609,
before the move of section 6 (after it, `validation.md` prints 2849 lines and 502 KB).

## 1. Inventory

| Document | Lines | KB | Long sentences | Precise numbers | of them also in `validation.md` | 8-word runs found in another document | Lines with a version number | Lines with a history phrase | Lines over 2000 characters |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| `README.md` | 200 | 26 | 147 | 9 | 5 | 4.4 % | 20 | 2 | - |
| `CHANGELOG.md` | 648 | 206 | 1306 | 350 | 292 | 8.6 % | 55 | 92 | - |
| `docs/theory.md` | 1213 | 325 | 1999 | 501 | 341 | 3.9 % | 60 | 33 | 29 |
| `docs/models.md` | 521 | 148 | 904 | 152 | 128 | 9.2 % | 22 | 19 | 7 |
| `docs/validation.md` | 2967 | 520 | 3170 | 3049 | - | 2.3 % | 156 | 144 | 10 |
| `docs/versions.md` | 571 | 218 | 1365 | 329 | 274 | 6.9 % | 117 | 39 | 20 |
| `docs/calculators.md` | 215 | 38 | 244 | 202 | 109 | 5.2 % | 10 | 8 | 0 |
| `docs/research.md` | 4 | 0 | 2 | 0 | 0 | - | 0 | 0 | 0 |
| `docs/version-comparison.md` (generated) | 3091 | 471 | - | - | - | - | - | - | - |
| `pcbthermal/help/index.html` (user guide) | 459 | 144 | 829 | 59 | 47 | 5.7 % | 2 | 10 | 11 |
| `pcbthermal/help/calculator.html` | 109 | 11 | 59 | 9 | 6 | 19.8 % | 0 | 0 | - |
| `research/README.md` (index) | 121 | 41 | 229 | 32 | 28 | 0.7 % | 47 | 8 | - |
| 69 research folder READMEs | 22 183 | 3225 | | | | | | | |
| all `.md` of `research/` (339 files) | | 5346 | | | | | | | |
| all `.md` of `releases/` (77 files) | 7 567 | 1184 | | | | | | | |

The largest research READMEs: `gerber-models` 1038 lines (162 KB), `gerber-real-boards` 744 (158 KB),
`theory-sources` 674 (137 KB), `lumped-zones-adoption` 652, `independent-fem-edge` 616, `rotated-square-3d` 606.
The largest release files: `releases/2.4.5/reproduction/README.md` 108 KB, `releases/2.8.0/fem-model/DESIGN.md`
54 KB, `releases/2.8.0/audit/FINAL.md` 41 KB, `releases/regression-harness/README.md` 40 KB.

**Headline**: the eleven project documents hold 1.6 MB of text (2.1 MB with the generated version comparison).
Whole sentences are rarely copied (105 of 10 254 long sentences, 1.0 %, are in two documents; the most between
`models.md` and `theory.md`, 19, and `CHANGELOG.md` and `versions.md`, 15), but the **numbers are**: of the
precise numbers of `theory.md` 68 % (341 of 501) are also in `validation.md`, of `models.md` 84 %, of the
CHANGELOG 83 %, of `versions.md` 83 %, of the user guide 80 %. The duplication is the same result told again in
other words with its numbers, not copied paragraphs. The second problem is length per paragraph: 66 lines of
`theory.md`, `models.md`, `validation.md` and `versions.md` (77 with the user guide) are single paragraphs of more
than 2000 characters (the longest, theory 8 line 959, about 5700).

## 2. Each document: audience, duplication, history, stale text, length

| Document | Audience | Duplicated | History mixed with the present | Stale | Too long |
| :-- | :-- | :-- | :-- | :-- | :-- |
| `README.md` | user, first visit | the features list repeats `models.md` 2 in shorter words; fine | the Versions list (20 lines), meant | - | no |
| `CHANGELOG.md` | user, per version | every item is also in `versions.md` (same branch, numbers, often the review story) | the review stories ('the review found ...') inside released entries | - | yes: 2.5.0 alone is 50 KB; but released entries stay as released (decision of 2.5.2), so only the Unreleased section is shortened |
| `docs/theory.md` | model reviewer, maintainer | 341 numbers also in `validation.md`; the 'Limits' and 'Where it is checked' paragraphs repeat validation results with their percentages; 19 sentences shared with `models.md` | 60 lines carry a version or a branch name, 41 the word audit ('Re-measured by the audit of 2.8.0', 'since `fix/...` (2.8.0)', 'the old equal slabs had ...'); the rule says no history | to check line by line in its branch (a sentence 'since 2.4.5' on a rule changed later) | yes: 29 paragraphs over 2000 characters (1.2 laminate band 206, 1.8 heat-source shape 333, 2.2 maximum principle 392, 5 first ring 660 and near edge 755, 6 local transient 826/830, 7 thick plate 921, 8 convection 959/960) |
| `docs/models.md` | user of the API and the CLI, maintainer | 128 of 152 numbers are in `validation.md`; section 18 (orientation) repeats the correlations of theory 8 with 40 numbers; section 19 (Gerber, 36 KB) repeats theory 1.6 to 1.8 and the guide 13 and 14 | 22 version lines (the via 'since 2.4.5', the FDM 'before 2.7.0') | section 2 of the five models predates the comparison FEM model (its own branch adds 2.8) | yes: 2 is 30 KB, 19 is 36 KB; 4b, 4c, 8b, 12 to 18 are small sections that belong to 2, 5, 6, 8b and 9 |
| `docs/validation.md` | model reviewer | the number store; correct that the others point here | 156 version lines and 144 history phrases: the '*Now ...*' notes of section 7 give the old value and the new one side by side; sections 6, 20, 21 (body) and 21.1 were whole history (moved now); 25 'Numbers that theory.md used to quote' is carried-over text 'not re-run' | the intro list 'Which table is current' is the right idea but is one paragraph of eight bullets naming 50 sections | yes, but it is a record; the fix is an index, not cutting |
| `docs/versions.md` | maintainer | each version chapter repeats the CHANGELOG with more detail (meant) | it is history by design | 'Planned: 2.7.0' (356 to 381) for a released version, 'After 2.6.0' (476 to 498) still says 2.6.0 'is prepared on the integration branch', 'Documentation audit 2.5.0' (322 to 349) is release work that belongs in `releases/2.5.0/` | 'Planned' is 62 KB, the roadmap of several versions |
| `docs/calculators.md` | user of the calculators, reviewer | `calculator.html` shares 20 % of its 8-word runs with it (the user copy; meant) | 7 audit notes | - | no |
| `docs/research.md` | maintainer | - | - | empty template, as the rule says | - |
| `docs/version-comparison.md` | maintainer at a release | generated | - | its pairs from v2.5.0 have no hand notes ('Planned: 2.8.0') | generated, leave |
| user guide `index.html` | user | 47 of 59 numbers are in `validation.md` (limits table of chapter 18, chapter 20) | none to speak of | to check against the program after the FEM chapter lands | 11 paragraphs over 2000 characters |
| `research/README.md` and the folder READMEs | researcher, reviewer | each folder repeats its tables (meant: the research documents are the exception to 'few and good') | meant | the registers are kept by the reviews | not touched by this plan |
| `releases/` | maintainer at a release | records | records | records | not touched |

## 3. Target structure

The documents stay the same set ('few and good'), plus one history file for validation, each with one job.
Section numbers are kept everywhere (about 2500 tracked lines cite a section of the kind 'validation 32' or
'theory 2.6', 116 of them in `pcbthermal/` and `tests/`, the rest in the documents, research folders and release
records); a document gets shorter, not renumbered.

| Document | One job | What leaves | Where it goes |
| :-- | :-- | :-- | :-- |
| `docs/theory.md` | what is implemented now, explicit and self-contained: symbols, equations, assembly, solution, limits in words, where it is checked (a pointer), sources with the reading status, a picture per section | measured numbers (a limit says 'cool side, a few per cent, validation 35' and the table is in validation), the history ('was X', 'since branch Y', 'the audit re-measured') | numbers to `validation.md` (the section already named in 'Where it is checked'), history to `versions.md` (the version chapter of the change) |
| `docs/models.md` | how to use the models and what each one does: inputs, outputs, when to use it, its warnings, the API and the command line, with pointers to theory for every equation | equations repeated from theory, numbers, the small sections 4b, 4c, 12 to 18 folded into the sections they belong to; the Gerber section reduced to what the import does, the rules to theory 1.6 to 1.8 | theory (equations), validation (numbers), the user guide (step by step of the import) |
| `docs/validation.md` | the evidence: (A) a short part 'Current tables', one table per scenario group with the tree and the reference named; (B) the decided items in their numbered sections, as now | sections that describe an earlier program, the '*Now*' notes that keep the old value beside the new | `docs/validation-history.md` (byte for byte, the heading stays with a pointer) |
| `docs/validation-history.md` (new, this branch) | superseded validation sections, kept as the record | - | - |
| user guide | what a user needs: steps, controls, warnings in plain words, the limits table with one number per row and a pointer to validation | review stories, second and third numbers per limit | validation |
| `README.md` | features and quick start | - | - |
| `CHANGELOG.md` | per version, short user-facing bullets (from 2.8.0 on; released entries unchanged) | the review story and the numbers of an item | `versions.md` |
| `docs/versions.md` | per version detail (where in the code, how tested) and the chapter 'Planned' | the release audit of 2.5.0; planned chapters of released versions | `releases/2.5.0/doc-review/README.md`; the done items of 'Planned: 2.7.0' to the 2.7.0 chapter (each already has its line there), the rest of it and 'After 2.6.0' merged into 'Planned: 2.8.0' or 'Features' |
| `docs/calculators.md`, `docs/research.md`, `docs/version-comparison.md` | as now | - | - |

## 4. Move list

Line numbers are those of e7dfb609 (they shift when the FEM documents land: each branch re-reads them first).
Nothing is deleted without a destination; each branch proves it with `scripts/check_doc_moves.py`
(`MOVES` for a byte-for-byte move, `--numbers-kept` for a paragraph that is split).

### 4.1 Done now (`DOC_MOVES.md`)

| Source | Destination |
| :-- | :-- |
| `validation.md` 363-385 (section 6 body) | `validation-history.md` |
| `validation.md` 856-888 (section 20 body) | `validation-history.md` |
| `validation.md` 890-951 (section 21 body before 21.1) | `validation-history.md` |
| `validation.md` 953-964 (21.1 body) | `validation-history.md` |

### 4.2 `docs/validation.md` (branch 1)

| Block | Destination |
| :-- | :-- |
| 1263-1289, section 25 'Numbers that theory.md used to quote' (carried over, not re-run): each row whose statement is now measured in a current section | `validation-history.md` 25 (byte for byte), the heading stays with a pointer; rows still the only evidence stay |
| 386-400, section 7: the old values in the '*Now ...*' notes | the current value stays in the bullet, the old one to `validation-history.md` 7 |
| 3.1 finite-element column and 3D rows that the intro calls superseded | `validation-history.md` 3.1 |
| 11-17, the intro 'Which table is current' | becomes the part A table 'Current tables' (scenario group, section, tree, reference) |

### 4.3 `docs/theory.md` (branch 2; after branch 1, because its pointers name validation sections)

| Block (line) | What leaves | Destination |
| :-- | :-- | :-- |
| 1.2 default material constants 58 | branch and audit names | `versions.md` |
| 1.4 laminate band 206, sub-gap ratio 228 | the measured percentages (29 and 18 numbers) | validation 36, 21.2 |
| 1.5 via target ratio 269, lone via limit 271 | version names, the history of the ratio | `versions.md` 2.4.5 |
| 1.7 imported copper 313, 323 | version and branch names | `versions.md` 2.7.0 |
| 1.8 heat-source shape 333 | 19 numbers, 5 version names | validation 29, `versions.md` 2.5.0 |
| 2.1.1 cut cells 366, 374 | the history of the film rule (centroid, drawn and imported) | `versions.md` 2.6.0 and 2.7.0; numbers to validation 32, 39, 40 |
| 2.2 maximum principle 392 | 32 numbers, 15 version names, 14 history phrases (the cold spot story) | validation 30 and 34, `versions.md` |
| 2.3 SOR 408, accuracy 441 ('Re-measured by the audit') | the audit numbers | validation 5 |
| 2.6 image 487, barrel 493 | the measured percentages | validation 28, 34, 49 |
| 2.7 memory law 513, 519 | the fit numbers | validation 26 |
| 4 limits 593 | 19 numbers | validation 21.3, 33 |
| 5 first ring 660, symmetry 705, near edge 755, zones 765 | the measured percentages and the history of the cap | validation 31, 35, 42.6, 50, 53; `versions.md` 2.6.0 |
| 6 local transient 826, limits 830, checked 831 | 26 to 28 numbers each | validation 4.1, 52 |
| 7 thick plate 921 | 37 numbers, 13 history phrases | validation 22, 54, 55 |
| 8 convection 959, 960, 969, 970 | the comparison numbers against the sources (51, 36, 19, 23); the formulas, the ranges and the reading status stay | validation 5 and 8 |
| 10 the table of the profile limits 1104-1108 | the measured ratios | validation 37 |
| 11 verification summary 1116-1139 | the numbers of the table; the table becomes 'what is checked against what' with the validation section | validation 25 / current tables |

The strings that `tests/test_docs.py` requires stay (list in 4.8).

### 4.4 `docs/models.md` (branch 3)

| Block | Destination |
| :-- | :-- |
| 2, 21-149: lines 55, 56 (FDM, via; 'since 2.4.5'), 92 (Analytic equations, 11 numbers) | equations already in theory 2.6 and 6; the numbers to validation 2 and 4; one paragraph per model left, each with its pointer |
| 4b 184-187, 4c 188-197 | into 3 (input checks) and 2 (FVM), with pointers to theory 7 and 2.7 |
| 12 329-357, 17 414-422 | into 8b (stack-up) |
| 13 358-390, 16 407-413 | into 6 (parts) |
| 14 391-396 | into 9 (outline) |
| 15 397-406 | a 'metal block' paragraph of 2, pointer to theory 7 |
| 18 423-429 (line 426, 40 numbers of the correlations) | the correlations are theory 8; models keeps the choice the user makes (the strings of 4.8 stay) |
| 19 430-521 (36 KB) | the rules to theory 1.6 to 1.8, the numbers of 509 to validation 27, the steps to the guide 13 and 14; models keeps what the import produces and its limits |

Folding renumbers nothing: a folded section keeps its heading as a one-line pointer, as in 4.1.

### 4.5 User guide `pcbthermal/help/index.html` (branch 4)

Chapters 18 'Limits and good practice' and 20 'What is validated and what is not': one number per limit and a
pointer to the validation section; the 11 paragraphs over 2000 characters split into lists. Everything that
`tests/test_help.py` requires stays (4.8). After the FEM chapter 'Which model to use' has landed.

### 4.6 `docs/versions.md` (branch 5)

| Block | Destination |
| :-- | :-- |
| 322-349 'Documentation audit 2.5.0' | `releases/2.5.0/doc-review/README.md` (new; byte for byte) |
| 356-381 'Planned: 2.7.0' | done items: already in the 2.7.0 chapter (lines 73 to 77 point to them by item number, so the list moves byte for byte to `releases/2.7.0/planned-2.7.0.md` and the pointers name that file); open items to 'Planned: 2.8.0' or 'Features' |
| 476-498 'After 2.6.0' | open items to 'Features' or 'Deferred'; the stale sentence about the integration branch to `releases/2.6.0/` |

### 4.7 `CHANGELOG.md`, `README.md`, the index (branch 6)

The Unreleased section in short user-facing bullets (the story is in `versions.md`); released sections untouched.
README unchanged except a link to the index of section 7.

### 4.8 Strings and anchors that tests require (they stay, or the test moves with them in the same commit)

* `tests/test_docs.py`, `docs/theory.md`: the module names `fvm.py`, `fdm`, `solid3d.py`, `lumped.py`, `analytic`,
  `convection.py`; the headings `## 2. FVM`, `## 3. FDM`, `## 4. 3D solid`, `## 5. Lumped`, `## 6. Analytic`,
  `## 7. Metal blocks`, `## 8. Heat transfer coefficients`, `## 9. Parts`, `## 10. Power profiles`,
  `## 11. Verification summary`; the formulas `G_x = (2 S₁ S₂`, `(C/Δt + ϑK)`, `(I + G_mod C_loc) y = y₀`,
  `A_mn a_mn = q_mn`, `ΔT = P₀ R/(1 − α P₀ R)`, `Nu = 0.54 Ra`; the convection needles `Raithby-Hollands`,
  `Example 8.1`, `laminar** form 8.13a`, `Face turned down and its limit`, `exponent 1/5`, `No convection
  coefficient of the program has been compared with a measurement`, ``hot face down `Nu = 0.475 Ra^{1/5}` ``,
  `was NOT confirmed`; and the absent strings `the same forms are read in [Lienhard2024]`, `general form
  reproduces the worked example`, ``hot face down `Nu = 0.27``, and no `conservative side` in the 3000 characters
  after 'Face turned down and its limit'.
* `tests/test_docs.py`, `docs/models.md`: `face turned down`, `edge-circulation limit`, ``down: `0.475 Ra^(1/5)` ``,
  and no ``down: `0.27``.
* `tests/test_help.py`, the user guide: every `href="#..."` has its `id`; the anchors `start-gerber`, `import`,
  `imported`, `prefs`, `files`, `keys`, `limits`, `warnings`, `validity`; chapters numbered 1..N without letters
  and all in the table of contents; the word lists of the tests (models, part fields, `Quick start: import a
  Gerber board`, `Glossary of the warnings`, `What is validated and what is not`, the preference keys, the warning
  names, `No measured copper board`, `Orphan part`, ...) and the pictures named; the stale strings it forbids.
* `tests/test_version.py`: the version in `CHANGELOG.md` and `README.md`. `tests/test_no_fabricator_names.py`:
  README and guide. `tests/test_theme_coherence.py`: the link colours of the guide. `tests/test_third_party_text.py`:
  no OCR page markers in any tracked Markdown. `research/theory/tests/test_theory.py`: the links of
  `research/theory/README.md` and the topics (they point into `docs/` by section number, which stays).
* References by number from code and tests (docstrings such as 'docs/validation.md 32', 'docs/theory.md 2.5'): kept
  valid by keeping the numbering.

## 5. Order and who does what

**Start when** the FEM branches 4 to 8 (theory 4a and 4b, models 2.8, validation 56 and 57, the guide chapter
'Which model to use') and `fix/thick-plate-surface-estimate` (theory, models, validation 2965+, guide, README,
CHANGELOG) are merged into `development`, and no other open branch touches `docs/` (check with
`git diff development...<branch> --stat -- docs README.md CHANGELOG.md pcbthermal/help` for every open branch).

One document per branch, in series, each from the new `development`, each with: the maintainer agent doing the
edit, the reviewer checking that every number that left is in its destination (`--numbers-kept`) and that the
theory still states every equation of the code it describes, and the documentation tests after each
(`tests/test_docs.py`, `test_license_header.py`, `test_version.py`, `test_help.py`, `test_third_party_text.py`,
`test_no_fabricator_names.py`, `research/theory/tests`; the whole battery before each merge, by the rule).

1. `docs/simplify-validation`: part A 'Current tables', the history moves of 4.2. First, because the others point into it.
2. `docs/simplify-theory`: 4.3. The longest (about 30 paragraphs to split); the reviewer reads the whole theory against the code at the end (it is also step 3 of the release gate).
3. `docs/simplify-models`: 4.4.
4. `docs/simplify-guide`: 4.5, with `tests/test_help.py` and the screenshots unchanged.
5. `docs/simplify-versions`: 4.6.
6. `docs/simplify-changelog-index`: 4.7 and the index of section 7.

Branches 3 to 6 touch different files and could run in parallel after 2, but they share the pointers into theory
and validation; in series is safer and each is short.

## 6. What was done on this branch

* `docs/validation-history.md` (new) with the bodies of validation 6, 20, 21 (before 21.1) and 21.1, byte for byte;
  the headings stay in `docs/validation.md` with a pointer (`DOC_MOVES.md`).
* `scripts/check_doc_moves.py`: the move, its check (byte for byte, reconstruction of the base) and the number check
  for later rewrites; `scripts/analyse_docs.py`: the numbers of sections 1 and 2.
* The documentation tests listed in 5 pass on the branch (859 passed).
* Left for the maintainer when this branch is recorded: `CLAUDE.md` (project structure, the list of documents of
  'Maintaining This File') must name `docs/validation-history.md`; that file is out of scope here.

## 7. How a reader finds things: `docs/README.md` (proposal, not created)

A short index, one table; to be created by branch 6 if the maintainer agrees (it is one more file in `docs/`).

| Question | Document | Where |
| :-- | :-- | :-- |
| How do I use the program? | user guide (Help - User guide, F1) | chapters 1 to 17 |
| Which model should I use, and how far can I trust it? | user guide | 'Which model to use', 18 Limits, 20 Validated |
| What does each model compute, and how do I call it from Python or the command line? | `models.md` | 2, 7 |
| What are the equations, exactly? | `theory.md` | one section per model, symbols in 0, sources in 12 |
| How accurate is it, against what? | `validation.md` | part A 'Current tables'; then the numbered section named in theory |
| What did an earlier version give? | `validation-history.md`, `version-comparison.md` | by section number; by version |
| What changed in a version? | `CHANGELOG.md` (short), `versions.md` (detail) | by version |
| What is planned? | `versions.md` | 'Planned' |
| How do the calculators work? | `calculators.md` | 1, 2 |
| What is being investigated? | `research/README.md`, `research/ROADMAP.md` | index by folder |
| How is a release checked? | `releases/README.md` | by version |

## 8. Open decisions for the maintainer

1. Accept `docs/validation-history.md` as one more document (an exception to 'few and good', in exchange for
   about 120 lines of history out of `validation.md` now and more by branch 1).
2. Create `docs/README.md` (section 7), or put the same table at the top of `README.md`.
3. Keep the released CHANGELOG entries as released (the decision of 2.5.2), so only the Unreleased section is
   shortened; or allow a one-time shortening of the old entries (their detail is in `versions.md`).
4. Move the done 'Planned: 2.7.0' list out of `versions.md` to `releases/2.7.0/` (4.6).
