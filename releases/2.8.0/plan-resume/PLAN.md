# Resuming 2.8.0: the ordered plan

What is left of 2.8.0 after the fine-comb audit, its fix branches and the final code-against-theory review, in the order to do it. Planning only: nothing here was run. The state is `development` at 8d18bb74 (2.7.1 plus every 2.8.0 branch merged so far). Sources: `docs/versions.md` 'Planned: 2.8.0', `research/ROADMAP.md`, `releases/2.8.0/audit/FINAL.md` (sections 4 and 4.5), `releases/2.8.0/audit/DECISIONS_2.md` 31, `releases/2.8.0/final-review/PART_*.md` and `REMEASURE.md`, the Decisions Log of `CLAUDE.md`.

The aim of 2.8.0 is **confidence, not features** (`docs/versions.md`): the version's claim is 'measured, bounded and warned errors, not corrected ones' (`releases/2.8.0/opinions/2026-11-15-open-questions.md`). The order below follows that: first what makes the quoted numbers true and reproducible, then the release gate, and features only if the maintainer wants them in this version.

## 1. Done

* **Wave 1** (cheap and safe) was released as **2.7.1**: the Profiles tab in a narrow window, the Properties focus after Enter, Duplicate, the disclaimer in every report, the third-party text guard, the JEDEC numbers, the OCR environment, the version notes, `tests/test_calculator_dialog.py` (`docs/versions.md`, chapter 2.7.1).
* **Wave 2 investigations closed and merged** (each reviewed GO): FEM extensions A43, studies 1 to 5 (`research/independent-fem-extensions`; the finer levels wait); the transient reference (`research/transient-reference-boards`); the Lumped dense via group, the zone placement (A46, stated limits), the block warning re-measure, the Lumped first link near a side (`research/lumped-edge-link`), drawn-copper faces (`research/drawn-copper-faces`), the Muzychka case 2 (`research/muzychka-case2-analytic`), the market FEM desk study (A47 deferred).
* **Model and program corrections merged** (each executor, reviewer, maintainer, whole battery): Lumped part read-out, Analytic transient hot point (A48), thick-plate warning bound, Board dock write-back, drawn-copper faces and the mixed board (5a), Lumped first link with the side images (A27), exact block cover, the film through the half copper layer (A50), the horizontal-face laws, the convection warnings, the calculator items, the published cases in the battery, typical-value marks, the via and edge warning texts, the element-tree filter (the only feature). Four pending files hold the moved frozen records: `block-exact-cover`, `drawn-copper-faces`, `face-film-half-slab`, `lumped-first-link-edge`.
* **The audit**: claims register (1482 claims), formula assignments (100 rows), the A1 to A5, L1 to L12, S1 reviews, decisions 1 to 36, the final review parts 1a to 2c, the Lumped re-measure (`REMEASURE.md`), the closing document `FINAL.md`. The decision on a live FDM warning for a small outer pad is closed: no warning (the error fell to 3.7 % at 1 mm and the guide states it).
* Last recorded battery: 3748 passed, 11 skipped, 2 xfailed (after `fix/face-film-half-slab`); the final whole battery on the tip is running.

## 2. What remains

Order column: the wave of section 3 (R0 leftovers, T trust studies, G release gate, F features only on the maintainer's word, L later than 2.8.0). Who: R researcher, E executor, V reviewer, M maintainer, T tester.

### 2.1 Leftovers of the audit (texts, tests, scripts; no number moves)

| item | kind | why it matters | depends on | frozen | size | who | order |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| Stale docstrings and test texts: `tests/test_analytic_perlayer.py` (-4.07 to +0.06 % where the shipped FVM gives -4.91 %), `tests/test_maximum_principle.py` ('8 to 14 K', the test prints 5.49 and 12.80 K), the `memory.VIA_CELLS_REF` comment against theory 2.7, the `gerber/parts.py` docstring ('0402 to 1206', the table starts at 0201) | fix (text) | a test or docstring that quotes a wrong number is the error pattern the audit found | - | no | S | E, V | R0-1 |
| Documents: the -4.91 % note at the head of validation 4.1 (the 48 boards on the shipped FVM; today it is inside a long parenthesis), `docs/models.md` 2.3 'thin heaters +9.5 %' (validation 2 now +8.4 %), the copper-fill gain sentence of the user guide (validation 18.1), the prose under validation 12 A and B, validation 29.2 body columns | texts | the same | - | no | S | M, V for the numbers | R0-1 |
| Warning and label wording: the bottom-face Rayleigh warning says 'turned down' also for a board colder than the air; the calculator point label 'Board temperature 1 mm around the part (ring)' (T6; the help says 0.5 to 1.5 mm); the coarse-cell time to 63 % (+28 % from a source with edges at mid-cell) added to the 'only N cells wide' warning | fix (text) | user-facing texts must match the measurements | - | no | S | E, V | R0-1 |
| Cut slider of Profiles at 900 x 700 with both docks (a minimum width or its own line) | fix (GUI) | the last interface item of wave 1 | - | no | S | E, V | R0-1 |
| Split the 3D-solid columns of `research/models-comparison/scripts/validation_study.py` from the program columns, so the program columns can be re-run on a busy machine (8 GB with the 3D solid) | investigation tooling | lets the reproduction pass re-run validation 1 to 3 without a quiet machine | - | no | S | E, V | R0-2 |
| Commit the scripts of the 29 + 17 via boards (validation 18.1) and the 54 unlike-layer boards (validation 4.1), on the folders that own them (A4 S2) | investigation tooling | two tables with no script that rebuilds them cannot be reproduced; a number no script reproduces is a finding | - | no | M | E, V | R0-2 |
| Study-script defects on their research branches: `research/fdm-inset-edge` (`os.makedirs` before writing, 4.5 GB peak in the header), `research/analytic-edge-and-transient` (`lib/calib_variants.py` reads `analytic._calibrated_dynamics`, removed in 2.6.0), `laminate-slabs-and-local-rule/scripts/study_solid_slices.py` counts the 3D face term twice (H8), `point-via-convergence/tests/test_program_patch.py` fails 3 tests (A44) | fix (studies) | otherwise the reproduction pass reports them as failures | - | no | S each | E, V | R0-2 |
| Stale READMEs of `point-via-convergence`, `effective-conductivity`, `solid3d-verification`, `gap-subdivision`, `block-and-fins`, `via-edge-image` (wave 1 row; one branch per folder) | texts (research) | check first whether the audit already corrected them; what is left is folded into the reproduction pass | - | no | M | V | G-1 (with the pass) |
| `CLAUDE.md` 'Where to continue (2.8.0)' still says 'wave 2 is next' | texts | a new session must start from the true state | this plan | no | S | M | R0-1 |
| Stale pictures: the editor screenshots without the Filter box, `results_summary*.png`, figure 22 of theory 11, figure 41 of theory 7.1 | texts (pictures) | regenerated and looked at once, after the last text change | the last code change | no | S | M | G-4 (doc review 6b) |

### 2.2 Investigations that raise trust most

A comparison with a measured board is **not possible now** (G1 needs a purpose-built board, `research/ROADMAP.md` section 5). The best substitutes, in order of value per effort:

| item | kind | why it matters | depends on | frozen | size | who | order |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| Install the finite-element scratch environment once (scikit-fem, pyamg in the folder's git-ignored environment) and re-run the finite-element references read but not re-run: validation 3, 3.1, 28, 36, 40, 43, 44, 46, 47 and the two FEM folders (`PART_2B.md` 5) | investigation (re-run) | every 'against finite elements' number of the documents is then reproduced on the final tree, not quoted | R0 done; quiet machine | no | M, heavy | T, V | T-1 |
| The copper-corner run (A30 first step, `REVIEW_A3.md` 4, T2): settle the sign of the FDM error and which of the two resolved references (25 to 39 % apart) is right | investigation | the only place where the documents cannot say on which side the error is | T-1 | no | M, heavy | R/E, V | T-2 |
| A43 finer levels (study 1b and 2 at 0.05 mm, masks at 45 degrees; about 2.9 GB) | investigation | closes A43; the reference grid of the via and stripe numbers | T-1 | no | M, heavy | E, V | T-3 |
| E13: the converged reference of small imported parts (refinement around the powered part, checked against an independent solver), then the reduced-model warning re-measured against it | investigation then texts | every 0402-size number is today a lower bound; the largest user-visible error of the reduced models | T-1 | no (text) | M, memory-heavy, alone | R, E, V | T-4 |
| The Lumped tables against an independent reference: the 1/16 mm layered reference of validation 18.2 and the via boards of 18.1 once their scripts exist (`REMEASURE.md` 5) | investigation (re-run) | the Lumped is 'medium' trust because most of its tables are against the FVM it was fitted to | R0-2 scripts | no | M, hours of solves | T, V | T-5 |
| The 3D solid columns of validation 1, 2, 2.1, 3 and the memory law at 8 to 16 slabs (H7), the end-to-end real imported four-layer board | validation | the 3D columns were not re-run (8 to 11 GB); the eight-layer 3D estimate was never compared with a peak | R0-2 split | no | S to M, heavy | T | T-6 |
| `research/reduced-models-edge-laminate` (decision 15): the laminate in the edge film of the Analytic and the Lumped, research only | investigation | the reduced models read up to 15 % cool at 200 W/m2K; 2.8.0 ships it as a warned limit, a correction is 2.9 | - | no (research) | M | R, E, V | T-7 or L |
| A47 second independent FEM (DOLFINx alone on the stripes-and-pad board, then the hollow barrel) | investigation | the reference stops being one program | A43 finer levels closed | no | M | R, E, V | L (or T-8 if time) |
| More published cases into the battery (the JEDEC 2s2p board once JESD51-7/-5 are read; a published fast-wave or transient case; the fin-channel originals when fetched) | investigation then tests | one-sided tests against printed numbers are the strongest substitute for a measurement | maintainer: registration, papers | no | S to M each | R, V | T-9 (when the sources exist) |

Investigations that may become model corrections (A18, A30 as a sector well, A32/A40, A51, A2 P2) are **not 2.8.0 work** unless a review gives GO in time (`DECISIONS_2.md` 31, step 3d): they ship as stated limits and move to 2.9.

### 2.3 Features still wanted (from `docs/versions.md` wave 3)

None is needed for the 2.8.0 goal; each is the maintainer's call (section 5). Sizes from `docs/versions.md`.

| item | size | frozen | depends on | order |
| :-- | :-- | :-- | :-- | :-- |
| Thermal-capacity inventory in the transient summary (makes a missing mass visible: a confidence feature) | S to M | no | - | F (candidate for 2.8.0) |
| Component role: 'top of the case' read-out; TO-263 thick-film resistor family (theta to be sourced) | S | no | a source for the theta | F (candidate) |
| Via fill library: a solder entry (conductivity to be sourced) | S | no | a source | F (candidate) |
| B5: plated component holes as vias (option, default off) and vias with a layer span | study M + code M | span: check the harness; option off: none | A43 | L |
| Paint and erase of the imported copper mask | M | no | - | L |
| Heater modes for the user and the part's openings kept for the re-import | M | no | - | L |
| Metal blocks: adiabatic face option and an emissivity per block | S to M | yes (block boards, one pending file) | a study of ours | L |
| Heat source inside a block; an intermediate piece as a layer | M | yes (boards that use it) | its investigation | L |

Any feature in 2.8.0 must merge **before** the refreeze (one refreeze per version).

### 2.4 The release gate (steps left)

| step | what | who | notes |
| :-- | :-- | :-- | :-- |
| G-0 | the final whole battery on the current tip read to its last line | T | running now |
| G-1 | **Reproduction pass** of the research folders that import the program (66 folders, section 2.5), branch `release/2.8.0-reproduction`, up to 4 testers in detached worktrees, part reports cherry-picked into one README with the totals; every shift linked to an item of 2.8.0 | T (x4), main session | after R0 and the T wave; light folders in parallel, heavy ones one at a time |
| G-2 | the reviewer's **final opinion** (go or no-go) on the whole diff v2.7.1..tip, the program, the documents and the investigations, in `releases/2.8.0/final-opinion/README.md`; it includes the review of `docs/theory.md` against the code (already done by parts 1a and 1b: the final opinion only checks what moved since) | V | after G-1 |
| G-3 | the whole battery on the final tree, with `PCBT_COMPAT_V245=1`, `PCBT_SCAN_KEY_VALUES=1` and `PCBT_PUBLISHED_FULL=1` | T | after G-2 fixes |
| G-4 | **documentation review 6b**: README, user guide and calculator help, the screenshots regenerated with `examples/make_screenshots.py` and looked at, theory, models, validation, calculators, tooltips, keys, About, CHANGELOG, research index; checklist in `releases/2.8.0/doc-review/README.md` | M with V | after G-3 |
| G-5 | **maintainer's word** (section 5) | maintainer | nothing below starts before it |
| G-6 | version bump to 2.8.0, CHANGELOG heading with the date, README badges and versions list | M | - |
| G-7 | **refreeze** on `release/2.8.0-refreeze`: `study_baseline_release.py --tag v2.7.1`, `study_run_suite.py --label final`, `study_diff.py --strict` with `reference/expected_shifts_2.8.0.json` (0 alarms), `study_freeze_reference.py ... --version 2.8.0`, `v2.8.0.json` into `tests/regression/data/`, the four pending files deleted in the same commit, the map hashes of `tests/test_results_views.py` rebaselined if the example board moved, `tests/regression` at 2, 1 and 0.5 mm, `docs/version-comparison.md` regenerated (`regen_version_comparison.sh`) | T, V | **`also_moved_by`**: `face-film-half-slab.json` holds the final numbers of the records that the three older pending files also moved, and its key `also_moved_by` names those files; `make_expected_shifts.py` reads only the file that holds a record (and is still written for 2.7.0: baseline v2.6.0, its own item map), so it must be adapted and taught to attribute such a record to every item it names (73 records and times) before the diff is run. The harness now has 20 boards (`drawn_inset_square`, `drawn_stripes_pad`, `drawn_ell` were added), so the record count is no longer 317 and the baseline on v2.7.1 includes them |
| G-8 | the whole battery on the refrozen tree; merge `development` into `main` with `--no-ff` ('Release 2.8.0'), annotated tag `v2.8.0`, push, **GitHub release** from the `[2.8.0]` section of `CHANGELOG.md` | M (or T) | `gh release list` checked before calling it closed |
| G-9 | housekeeping: the `worktree-agent-*` worktrees and branches; the next version's studies opened | main session | - |

### 2.5 The reproduction pass: folders, grouped for four testers

66 folders under `research/` import the program (`git grep 'pcbthermal'`); most have `tests/`. Each tester runs its folder tests and the studies that take under about ten minutes, one job at a time; heavy studies wait for a quiet machine.

| tester | theme | folders |
| :-- | :-- | :-- |
| A | Lumped, Analytic, transient, published cases | analytic-edge-and-transient, analytic-edge-spatial, analytic-partial-copper, block-warning-remeasure, fast-wave-oscillation, lumped-analytic-vias, lumped-dense-via-group, lumped-edge-link, lumped-near-edge, lumped-ring-uniform-deficit, lumped-via-groups, lumped-zone-placement, lumped-zones-adoption, muzychka-case2-analytic, paper-case-studies, published-cases-followup, reduced-models-imported-passives, transient-reference-boards (18) |
| B | vias, laminate, edge, cut cells, FDM | bare-spot-under-source, cut-cell-links, fdm-inset-edge, gap-subdivision, imported-via-rim, laminate-edge-band, laminate-nodes, laminate-slabs-and-local-rule, point-via-convergence, rotated-square-3d, small-model-defects, sor-with-via-couplings, strong-edge-laminate, via-contact-geometry, via-edge-image, via-partial-copper, via-real-board, via-well-sheet-order, young-omega-tiles (19) |
| C | Gerber, imported and drawn copper, outline, memory (needs `pcb-library/scripts/link_env.sh`) | bom-role-and-close-hook, drawn-copper-faces, gerber-cad-profiles, gerber-import, gerber-models, gerber-nets, gerber-real-boards, imported-copper-edge-film, memory-guard, outline, zone-union (11) |
| D | convection, blocks, parts, stack-up, calculator, theory, the heavy 3D and FEM folders | block-and-fins, component-heatsink, convection-laws, effective-conductivity, face-down-convection, fin-channel, fin-channel-sources, horizontal-plate-h, independent-fem-edge, independent-fem-extensions, models-comparison, plate-h-level, power-calculator, solid3d-verification, stackup, theory, theory-sources, via-fill (18) |

Heavy items in the pass: `models-comparison` (`validation_study.py`, about 8 GB with the 3D solid), `solid3d-verification`, `memory-guard`, the two FEM folders (scratch environment), `gerber-real-boards`, `rotated-square-3d`. Folders whose Lumped numbers moved with the side images and the part read-out (component-heatsink, lumped-near-edge, published-cases-followup, paper-case-studies) are expected to shift; the shift is linked to `fix/lumped-edge-first-link` or `fix/lumped-part-readout`. Known before the pass: A44 (3 failing tests of `point-via-convergence`), the removed function read by `analytic-edge-and-transient/lib` (both fixed in R0-2 if done first).

### 2.6 The Thermal Sources Atlas (F10)

Documents only, light on the machine, but it takes reviewer slots (one reviewer per 10 to 15 sources, two at a time). Its gate in `research/ROADMAP.md` (audit, final review and the 2.8.0 fixes closed) is now met. Recommendation: it is **not** a release item; open `research/thermal-sources-atlas` after the final opinion (G-2) has freed the reviewer slots, with a pilot of about five sources run beside the documentation review, and the rest after the release. It may start earlier only with the extra OCR-reviewer slot if the maintainer extends that rule to it.

## 3. Order in waves

Machine rule (`CLAUDE.md`, 'How the main session orchestrates'): heavy jobs in series by default, up to three only while load is below 5, swap below 2.5 GB with growth below 1.5 GB and free plus inactive memory above 6 GB plus the job's declared peak; one `pytest` battery at a time; at most two reviewers plus the one OCR reviewer. Branches that touch `fvm.py`, `fdm.py`, `lumped.py`, `analytic.py`, `checks.py`, `laminate.py`, `viawell.py` or `docs/theory.md` merge one after another.

| wave | content | parallel or series |
| :-- | :-- | :-- |
| **R0** (now, after the running battery) | R0-1: one `fix/audit-leftovers` branch (docstrings, test texts, warnings and label, Cut slider, the document notes) and the `CLAUDE.md` 'Where to continue' line; R0-2: the script work (split of `validation_study.py`, the via-board and unlike-layer scripts, the four study-script defects, each on the branch of its folder) | R0-1 and R0-2 written in parallel (light); R0-1 touches `checks.py`: merged alone with its whole battery; the research branches merged after their reviewer without a battery (research tests only) |
| **T** (trust, heavy) | T-1 FEM environment and the FEM re-runs; T-2 copper corner; T-3 A43 finer levels; T-4 E13; T-5 Lumped tables against the independent reference; T-6 3D columns and H7; T-7 reduced-model edge laminate (research only) | **series**, one heavy job at a time on a quiet machine; the writing of each study and its README can overlap with the previous run; each closed by the reviewer (two at most) |
| **T-texts** | the warning and document numbers that T-2, T-4 and T-5 move, on one text branch (no frozen number) | after T; alone, whole battery |
| **F** (only with the maintainer's word) | the S features of 2.3 (capacity inventory, top-of-case read-out, solder fill) | in series with any text branch that shares `checks.py` or the guide; before the refreeze |
| **G** | G-0 to G-9 of 2.4: reproduction pass (4 testers, light folders in parallel, heavy ones in series), final opinion, battery, doc review, then the maintainer's word, bump, refreeze, battery, main, tag, GitHub release | strictly in this order |
| **L** (after 2.8.0) | A18, A30 sector well, A32/A40, A51, A2 P2, the reduced-model edge-laminate correction, B5, paint/erase mask, heater modes, block options, A47, the Atlas in full, G1 when the board exists | - |

If time is short, T-2, T-5 and T-6 are the ones that can slip to the reproduction pass as 'not re-run, stated'; T-1 and T-4 should not, because the documents quote their numbers as the main independent evidence.

## 4. Risks

1. **The refreeze attribution**: `make_expected_shifts.py` is written for 2.7.0 (baseline `v2.6.0.json`, the item map of the four 2.7.0 pending files hard-coded) and reads only the pending file that holds a record; `also_moved_by` of `face-film-half-slab.json` names 73 records and times also moved by older items (56 `lumped-first-link-edge`, 14 `drawn-copper-faces`, 3 `block-exact-cover`). Run as is, those would carry only the film-term item. Adapt the script (baseline v2.7.1, the four 2.8.0 items, the key read) on the refreeze branch first and check one record of each older file by hand.
2. **The record count changes**: three new harness boards, so the frozen test count, the baseline on v2.7.1 and every place that quotes '317' must follow.
3. **A trust study moves a quoted number again** (the copper corner, E13, the Lumped against an independent reference): every such number goes through the T-texts branch and the documentation review; nothing is quoted from a study that the reviewer has not closed.
4. **The FEM environment** (scratch installs, about 3 GB per solve, killed runs under load): one job at a time, notes written as it goes, retried after a cut-off.
5. **The reproduction pass finds failures that are old** (A44, removed functions, studies that depend on `pcb-library`): R0-2 removes the known ones; the rest are classified (explained, defect, not run) and not fixed inside the pass unless small.
6. **Battery time and timing flakes** (about 50 minutes; two known timing tests fail under load): one battery at a time, the flakes re-run alone and recorded.
7. **Scope creep**: features or model corrections added late push the refreeze and the whole gate; one refreeze per version, so a late number-moving change restarts G-7.
8. **Real-screen behaviour**: the GUI is tested offscreen only; the real-screen checklist (about one hour) needs the maintainer's hands before the release.
9. **Stale state documents**: `CLAUDE.md` 'Where to continue' and the test-count line drift unless updated at each merge.

## 5. Questions for the maintainer (one block, at G-5 or before if he wants)

1. **Release date** of 2.8.0, and whether the trust wave T is complete before it (or T-2, T-5, T-6 may ship as 'not re-run, stated').
2. **Features in 2.8.0**: none (pure confidence release), or the small ones (thermal-capacity inventory, top-of-case read-out, solder via fill)?
3. **JESD51 registration** (free, in his name, at jedec.org) for JESD51-7 and JESD51-5 (and -3, -6, -8): it turns the JEDEC calculator row from an indication into a one-sided test.
4. **Papers to download**: the sources not in the library (`FINAL.md` 4.1); which of them have open copies to fetch, and whether he fetches the paywalled ones (the fin-channel originals block C3).
5. **The three `tmp/*` branches**: `tmp/article-1319202` (1 commit only on it: a literature note, to be checked against the third-party text guard before anything of it is kept), `tmp/merge-280d` (3 commits only on it: merge resolutions; confirm their content is in `development`, then delete), `tmp/paper-notes-policy` (1 commit: the temporary study of paper notes; its answer feeds F10). Keep, fold or delete each.
6. **`feature/via-star-coupling`** (no-go in the 2.6.0 review, unmerged, on `origin`): keep as the record unmerged, or merge with `--no-ff` as a record of a rejected design (the code would have to be reverted in the same merge).
7. The decisions still open in `FINAL.md` 4.5: copper 385 or 398 W/mK (recommended: keep 385), the 10 / 15 / 10 W/m2K default films (keep), the policy 'independent reference first, superseded tables marked' (confirm), the reduced-model edge laminate as a stated limit in 2.8.0 with a research branch (confirm), and the Atlas timing of 2.6.
8. The real-screen checklist (about one hour of his time) before the release.
