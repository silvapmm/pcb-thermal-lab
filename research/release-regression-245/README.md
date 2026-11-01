# Release regression 2.4.5: the reference numbers

Status: **shake-down run done and reviewed** (quick and full set, tag v2.4.4 against the tree at develop 9e890be; the program version is still 2.4.4, so `reference/v2.4.5.json` is not generated: the generator refuses before the version bump). The first run showed that seven hypotheses of the table were wrong or had no size, and the table was corrected (section 6.3). The review (section 7) found that the harness could not fail on a covered board: an out-of-range shift was not an alarm, the bounds were up to 60 times wider than the shifts measured, and bounds in K were compared with checksums and counts (8 SOR numbers out of range went unreported); the classification, the table (measured limits per board, model and cell) and the frozen comparison were corrected, and the FDM shift of the part across the outline was checked against an independent solver (a correction, not a defect). Sections 1 to 5 are the text written before the run; section 6 holds the results of the first run (corrected where the review found them wrong); section 7 the review.

## 1. Purpose

2.4.5 changes the answers of the models on several kinds of board (laminate nodes, the point via, the constriction of the heat on a via, the part across the outline, the board cover) and leaves others untouched. This folder answers two questions with numbers instead of with the test counts:

1. **What moved between v2.4.4 and the release candidate, and is every shift explained by an item of the release?** The same harness runs both revisions; every shifted number is classified against a table written from the documents of the release.
2. **How far is each model from an independent reference, before and after?** On the boards that an independent layered 3D solver can represent.

The final numbers of the release are then **frozen** in a small committed file, which a pytest module compares with a run of the program in every later version (`INTEGRATION.md`).

![flow of the regression](figures/fig_01_regression_flow.png)

*Figure 1 (`figures/fig_01_regression_flow.png`): one harness runs both trees; the diff is classified against the table; the reference solver gives the error of each model; the numbers are frozen once the diff has no alarm.*

### 1.1 The boards

The three example files of the program, one derived example and thirteen small canonical boards (`lib/regress_boards.py`, built with the public builder API that exists in v2.4.4 and in the candidate). The four marked R have an independent reference (square source on cell edges at 2, 1 and 0.5 mm, laminate of one conductivity, insulated sides).

| Board | What it exercises | R |
| :-- | :-- | :-- |
| `example_board` | 4 layers, partial top copper, 9 vias, two parts, a bottom heatsink | |
| `profile_board` | the example with a square-wave profile (steady state at the average power; the harness strips the profile so that no time simulation starts) | |
| `reference_board` | 2 layers full copper, one 20 mm part: nothing in 2.4.5 may move it | |
| `example_cut_to_T` | the example board cut to an inverted T (outline, parts and vias on the board) | |
| `plate_uniform` | 60 x 60 mm, 2 layers full copper, 8 mm source | R |
| `plate_pad` | the same with a 20 mm copper window on both layers, bare laminate around | R |
| `plate_vias` | `plate_uniform` with a 4 x 4 array of 0.3 mm vias | |
| `plate_lone_via` | `plate_uniform` with one 0.3 mm via (the point via) | |
| `round_outline` | round board of 56 mm in a 60 mm box | |
| `t_outline` | 80 x 60 mm T, a part in the stem | |
| `two_layer_partial` | 80 x 60 mm, top copper window, bottom at 70 % fill | |
| `one_layer_full`, `one_layer_pad` | 60 x 60 mm, one layer, full copper or a 20 mm pad | R, R |
| `finned_block` | 3 mm aluminium block with plate fins on the bottom face under a part | |
| `part_top_path` | a component with theta, theta_jc_top and a heatsink on the package, on a 14 mm pad | |
| `hatched_copper` | both layers hatched (fill 0.5 and 0.7) | |
| `part_across_outline` | outline edge at x = 37.3 mm (between cell edges at 2, 1, 0.5 mm), a part across it | |

Sources and pads of the R boards lie on multiples of 2 mm so that the heated area is the same at every cell size (a source edge between cell edges changes the heated area; `round()` rounds halves to even). The example files are read from the current tree for both revisions, so both see the same input (`git diff v2.4.4 develop --stat -- examples` is empty).

### 1.2 What a result set holds

For every board, model (`fvm`, `fdm`, `lumped`, `analytic`, `solid3d`) and cell (2, 1, 0.5 mm), direct solver: the unknowns as the program counts them, `t_max`, `t_mean`, `t_min`, the mean temperature of every layer, a checksum of the whole field (sum and sum of squares, so a change anywhere is seen), the hottest point, mean and junction temperature under every part, the metal-block temperatures, the power in, the heat balance, the warnings, and the solve time (information only, never compared). Also, per board and model, the time to 63 % of the steady resistance of every part (the unit-step response of `api.step_response`; the FVM and FDM use at least 2 mm there), and the FVM with the SOR solver at 2 mm on five boards (sweeps, omega, temperature).

Memory is kept light: FVM and FDM above 400 000 unknowns and the 3D solid above 150 000 are recorded as *skipped* with the reason (`--max-unknowns`, `--solid-cap`). The Lumped and Analytic cell is clamped to 0.5 to 1 mm by the API in v2.4.4 as well, so their 2 mm and 1 mm runs are the same run (a check in the diff).

### 1.3 The classes

| Class | Meaning |
| :-- | :-- |
| identical | every number equal as floats (bit for bit) |
| `expected` | a rule of the table covers the board, model, cell and metric, and the direction and size are inside the bounds |
| `expected_out_of_range` | a rule covers it but the shift is outside the range the study gave (or, since the review, outside the measured limit or the other way): an alarm since the review (7.1) |
| `to_be_explained` | the item is a plausible cause and no study gives the size (left so on purpose) |
| `unexplained` | no rule covers it: an alarm |
| `must_not_move` | the board and model that no item of the release may change moved: an alarm that wins over every rule |
| warnings only | the texts changed, no number: listed, not a shift |

`reference/expected_shifts.json` holds nine items (I1 part across the outline, I2 board cover 8 x 8, I3 laminate nodes, I4 point via and block SOR, I5 via constriction in Lumped and Analytic, I6 Young omega (sweeps only), I7 warnings only, I8 documents and theory, I9 the Power Calculator row), 22 rules, 6 must-not-move entries, the rules for the times to 63 %, and a matrix of what each board should show (printed at the end of the diff). Each rule says whether its bound is *quantified* (a number printed by a study), *derived* (worked out from a printed number or an engineering margin) or *to be explained*. Examples: a 2-layer board with a copper window and the laminate rule: the FVM rise goes up by at most 45 % of the rise (the largest in the studies, +38 %, a 6 mm window over 3.2 mm laminate); the example board cut to a T: the hottest point of the FVM goes down by at most 20 K (4 K on the example, 16 K in the edge sweep of a small T); Lumped and Analytic on any board without vias: no shift at all.

## 2. How to run (in this order)

All from the repository root, with `.venv/bin/python`. The runs are long and use memory (the 0.5 mm cells on the example board); run them when the machine is free, and use `--quick` (2 mm only) for a first look (`study_baseline_release.py ... -- --quick`: the arguments after `--` go to `study_run_suite.py`). Times and memory of a full run have **not** been measured.

```sh
R=research/release-regression-245/scripts
# 1. the baseline: v2.4.4 extracted with git archive into a scratch folder outside the repository, run in a separate process
.venv/bin/python $R/study_baseline_release.py --tag v2.4.4          # -> out/v2.4.4.json   (--dest DIR to choose the scratch folder)
# 2. the same harness on the release candidate (the tree you are in)
.venv/bin/python $R/study_run_suite.py --label rc                    # -> out/rc.json
# 3. the independent references (once; they do not depend on the revision)
.venv/bin/python $R/study_references.py --cells 2 1                  # -> out/references.json   (0.5 is slow)
# 4. diff and classify
.venv/bin/python $R/study_diff.py out/v2.4.4.json out/rc.json        # -> out/diff_v2.4.4_vs_rc.{json,md}; --strict exits 1 on an alarm
# 4b. once, on the reviewed candidate (full sets): measured limits per board, model and cell into the table (review, section 7.2)
.venv/bin/python $R/study_tighten_table.py out/v2.4.4-full.json out/rc-full.json --out research/release-regression-245/reference/expected_shifts.json
# 5. the error of each model against the independent solver, before and after
.venv/bin/python $R/study_error_vs_reference.py out/v2.4.4.json out/rc.json
# 6. when the candidate is final, with the version bumped in the tree: freeze
.venv/bin/python $R/study_run_suite.py --label final                 # the numbers that are frozen
.venv/bin/python $R/study_freeze_reference.py out/v2.4.4.json out/final.json --version 2.4.5   # -> reference/v2.4.5.json (committed)
# 7. figures (optional)
.venv/bin/python $R/make_figures.py out/v2.4.4.json out/final.json
```

(`out/` is git-ignored. The freeze refuses while the diff has an alarm, when the program version of the run is not the one asked for, and when the file exists.) The tests of the folder: `tests/test_classify_logic.py` (pure logic, no program) and `tests/test_frozen_numbers.py` (skipped until `reference/v2.4.5.json` exists):

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q research/release-regression-245/tests
PCBT_FROZEN_CELLS=2,1 .venv/bin/python -m pytest -q research/release-regression-245/tests/test_frozen_numbers.py     # more of the frozen file
```

## 3. What is left

* Run everything (nothing was run), read the diff, and turn every `unexplained` and `expected_out_of_range` into an explanation or a defect report; decide the `to_be_explained` rows that need a number (the table lists them with their item).
* The table was written from the documents and **is a hypothesis until the first diff**: a rule that is wrong (a direction, a bound) shows as an alarm and is corrected in the table, with a note.
* The must-not-move entries (for example "Lumped and Analytic bit-identical on every board without vias", "FDM hottest point bit-identical on a full-copper outline board") rest on the sentences of `CHANGELOG.md` and `docs/validation.md`; if the first diff contradicts one, either the program or the sentence is wrong.
* The reference solver is isolated from the program but is the same one the tests use (`layered3d.py`); a second independent reference for the boards with vias and outlines does not exist in this folder (the 3D solid of the program is a comparison model, not independent).
* The solve times are stored for information; no time limit or performance claim is made.

## 4. Files

| Path | Content |
| :-- | :-- |
| `lib/regress_boards.py` | the boards and the specifications of the four reference boards |
| `lib/regress_harness.py` | runs one revision: `use_program`, `run_one`, `t63`, `run_suite` |
| `lib/regress_classify.py` | diff, classification, internal checks, Markdown |
| `lib/regress_refsolve.py` | the independent references and the error tables |
| `lib/regress_frozen.py` | the format of the frozen file, `build`, `compare` |
| `reference/expected_shifts.json` | the table of expected shifts |
| `reference/v2.4.5.json` | the frozen numbers (generated by the tester; absent now) |
| `scripts/study_*.py`, `make_diagrams.py`, `make_figures.py` | what to run (section 2); `study_tighten_table.py` writes the measured limits of the table (review, 7.2) |
| `tests/` | `test_classify_logic.py`, `test_frozen_numbers.py` |

## 5. What was read and what was not verified

* **Read in full**: `CHANGELOG.md` (Unreleased and 2.4.4 to 2.4.2), `docs/versions.md` 2.4.5 and its Planned chapter, `docs/validation.md` 18.1, 21.2 and 23, the public builder API of `pcbthermal/model.py`, `pcbthermal/api.py` (`simulate`, `step_response`, options), `pcbthermal/results.py`, `analysis.heater_stats`, `tests/test_layered_vs_3d.py` and the header of `tests/helpers/layered3d.py`.
* **From a summary or a search, not read**: the research folders' READMEs beyond what `research/README.md` and `REVIEW.md` say about them (the quantities in the table come from the project documents, not from re-reading the studies).
* **Written but never run**: every file of the harness except the pure-logic functions of `regress_classify.py` and `regress_frozen.py`, which were exercised by hand on synthetic records (the seven functions of `tests/test_classify_logic.py` pass when called directly; pytest was not run). `make_diagrams.py` was run once to draw figure 1 (matplotlib only). The harness has never imported the program, so a wrong attribute name or a signature that differs between v2.4.4 and the candidate (`fvm.unknowns`, `solid3d.unknowns`, `analysis.block_stats`, `api.step_response`, `Problem.add_heater(role=...)`) will show on the first run; the calls were checked against the v2.4.4 source with `git show` only for `step_response`, `simulate`, `SolverOptions` and `fvm.unknowns` and `solid3d.unknowns` (`fdm.unknowns` and `analysis.block_stats` in v2.4.4 were not looked at; the harness wraps both in try/except).
* **Not verified**: that the boards build and validate without a warning that stops them (an outline with the heatsink of the example, a block on the bottom face, the component on a 14 mm pad); that the 3D solid fits under 150 000 unknowns on the small boards at 0.5 mm; that exact equality of floats ("bit") survives a second machine (it is expected to on the same machine; `PCBT_FROZEN_BIT_TOL` relaxes it); how long the full suite takes. (Items answered by the first run, section 6: the boards build and validate, the 3D solid fits under 150 000 unknowns except the four 0.5 mm cases listed there, the full suite takes about two minutes; the bit equality across machines and the frozen-file comparison remain unverified.)

## 6. Results of the first run (shake-down)

Commands (from the repository root, `nice -n 10`, one job at a time, `QT_QPA_PLATFORM=offscreen`): `study_baseline_release.py --tag v2.4.4` (full set; `--quick` first), `study_run_suite.py --label rc-full`, `study_references.py --cells 2 1 0.5`, `study_diff.py`, `study_error_vs_reference.py`, `study_freeze_reference.py` (dry run). Tree: develop at `9e890be` merged into this branch. The program version of the tree is 2.4.4 (no bump yet).

Cost: the quick run takes 15 s (v2.4.4) and 25 s (tree); the full run (17 boards, 5 models, 2, 1 and 0.5 mm, transients, SOR) takes 61 s and 105 s with the machine shared with two other long jobs (load average 5 to 6 on 10 cores); the references 42 s; no swap growth was seen (the largest FVM run is the example board at 0.5 mm, 147 000 unknowns). 255 runs per revision, 251 ok, 4 skipped (the 3D solid above 150 000 unknowns: example board, profile board, example cut to a T at 0.5 mm, reference board at 0.5 mm 240 000); none failed. Peak memory was not recorded.

### 6.1 The classification, tree against v2.4.4 (full set)

1422 shifted numbers, all `expected`; 0 unexplained, 0 must-not-move, 0 out of range, 0 to be explained (after the table was corrected, 6.3); 113 records bit-identical (the SOR runs, a separate count, had 8 numbers `expected_out_of_range`, not reported here: checksums and unknown counts compared with bounds in K; corrected by the review, 7.1); 14 warning texts changed; 41 of 68 times to 63 % changed, 27 identical (rules T3 to T5, no tight bound). The internal checks of each set (188 per set: heat balance below 1e-3 W, Lumped and Analytic 2 mm equal to 1 mm, SOR equal to the direct solver within 1e-3 K) all pass.

Shifts of the hottest point at 2 mm, with the item that causes it (6.2):

| Board | Model | v2.4.4 | tree | Shift [K] | Item (commit) |
| :-- | :-- | --: | --: | --: | :-- |
| plate_pad | FVM / FDM | 345.13 / 289.98 | 362.61 / 291.29 | +17.48 / +1.32 | laminate rule (`e9f4df2`) |
| two_layer_partial | FVM / FDM | 161.26 / 159.06 | 162.62 / 159.61 | +1.36 / +0.55 | laminate rule |
| hatched_copper | FVM / FDM | 111.42 / 111.43 | 112.01 / 112.01 | +0.58 / +0.58 | laminate rule |
| one_layer_pad | FVM / FDM | 94.31 / 81.07 | 95.56 / 81.19 | +1.25 / +0.12 | laminate rule |
| one_layer_full | FVM / FDM | 55.361 | 55.355 | -0.006 | laminate rule (one node per cell less, 2700 to 1800 unknowns) |
| part_top_path | FVM / FDM | 73.82 / 71.35 | 74.71 / 71.59 | +0.89 / +0.24 | laminate rule |
| example_board | FVM / FDM | 85.34 / 84.66 | 85.07 / 84.27 | -0.27 / -0.40 | point via (`5e93182`) |
| plate_vias | FVM / FDM | 136.77 / 132.61 | 137.72 / 133.43 | +0.96 / +0.82 | point via |
| plate_lone_via | FVM / FDM | 152.78 / 147.96 | 151.52 / 148.69 | -1.26 / +0.72 | point via |
| example_board | Lumped / Analytic | 84.66 / 84.65 | 86.63 / 85.10 | +1.97 / +0.45 | via constriction (`f671868`) |
| plate_vias | Lumped / Analytic | 138.06 / 142.21 | 140.36 / 137.64 | +2.30 / -4.57 | via constriction |
| plate_lone_via | Lumped / Analytic | 153.80 / 155.48 | 154.48 / 152.11 | +0.68 / -3.37 | via constriction |
| part_across_outline | FVM / 3D solid | 231.65 / 232.64 | 229.95 / 230.92 | -1.70 / -1.73 | part weights (`62afbb8`) and cover 8 x 8 (`7a5b0ee`); at 1 mm 243.72 / 245.21 to 230.04 / 231.15 (-13.68 / -14.06) |
| part_across_outline | FDM | 246.76 | 230.52 | -16.24 | part weights (`62afbb8`); at 1 mm 252.03 to 230.23 (-21.8) |
| round_outline | FVM / 3D solid | 174.97 / 175.70 | 174.99 / 175.75 | +0.02 / +0.05 | cover 8 x 8 |
| reference_board, plate_uniform, finned_block | direct models | | | 0 | bit-identical (the SOR of the plain plate moves 4e-8 K: Young omega) |

Other effects: the 3D solid moves only on the boards with an outline and, at 0.5 mm, on the two plates with vias (hottest point -0.14 and -0.15 K); example board at 0.5 mm FVM 85.87 to 85.18, Lumped 83.54 to 85.45. The SOR needs 364 sweeps against 1149 on the example board (298 against 1109 on the plate with vias; omega 1.88 to 1.94); the SOR temperatures equal the direct ones in both versions on these five boards (the 19 to 22 K difference of the old SOR with vias quoted in the table was measured on a 3 x 3 board and was not seen on them).

### 6.2 Which item moves what (archives of the commits)

`git archive` copies of `62afbb8`, `7a5b0ee`, `5e93182`, `d9216c4`, `f671868`, `e9f4df2` and `0dd08ad` were run at 2 mm and compared board by board (hottest point and mean under the first part); each copy contains the earlier items.

* `62afbb8` part weights: only `part_across_outline` (FVM 231.65 to 227.24, 3D 232.64 to 228.16, FDM 246.76 to 230.52) and the mean under that part (FVM 189.0 to 210.7, FDM 216.8 to 212.6, Analytic 203.4 to 201.5).
* `7a5b0ee` cover 8 x 8: the outline boards (`round_outline` FVM +0.02 K, 3D +0.05 K; `part_across_outline` FVM and 3D +2.7 K back up from the weights) and the Analytic mean under a part (round 170.73 to 170.01, T 136.31 to 136.42).
* `5e93182` point via: FVM and FDM on boards with vias.
* `d9216c4` Young omega: no temperature moves (sweeps only).
* `f671868` via constriction: Lumped and Analytic on boards with vias only.
* `e9f4df2` laminate rule: FVM and FDM on every board with copper absent or partial, and the one-layer boards.
* `0dd08ad` (vias without a board under them): no number of this suite moves.

Every shift of the tree belongs to one of these items.

### 6.3 What the first run corrected in the table (hypotheses that were wrong)

1. **M5** (FDM hottest point on outline boards bit-identical): true for `round_outline` and `t_outline`, false for `part_across_outline`: the FDM hottest point falls 16.2 K at 2 mm and 21.8 K at 1 mm with the part weights. R1a now covers the FDM, bound 30 K.
2. **M2** (Lumped and Analytic bit-identical without vias): true for the field and the hottest point, false for the mean under a part on an outline board (read on the real outline): Analytic moves 0.1 to 1.9 K (`round_outline` -0.71, `t_outline` +0.11, `part_across_outline` -1.37 at 2 mm and -1.92 at 0.5 mm; the first version said 1.4 K, the 2 mm value); Lumped on the T by 1e-14 (noise). Rule R1e. The CHANGELOG sentence "Lumped and Analytic unchanged" holds for the field, not for this read-out.
3. **R5a** (via constriction raises the hottest point in Lumped and Analytic): true for the Lumped and for the Analytic on the example board, false in direction for the Analytic on the plates (plate_vias -4.57 K, plate_lone_via -3.37 K). The 3D solid (136.87, 153.37) is closer to the new values (137.64, 152.11) than to the old (142.21, 155.48): an improvement. Rule R5c. The Lumped layer means move by -0.115 to +0.17 K in either direction (R5d).
4. **M1** applied to the SOR of the plain plate, which moves by 4e-8 K because the relaxation factor changed (R6a); M1 now lists the five direct models. R3g and R4d include the unknown count of the SOR runs.
5. **R3h** (new): a one-layer board with full copper loses one of its two laminate nodes per cell (2700 to 1800 unknowns at 2 mm), hottest point -0.006 K; the CHANGELOG says boards with copper everywhere are unchanged "except one-layer boards".
6. Sizes measured and filled in (they were "to be explained"): R1c and R2b (board mean, minimum and layer means on outline boards: up to 0.7 K at 2 mm, 0.16 K at 0.5 mm; `round_outline` minimum -0.26 K), R4c (3D solid with vias: -0.15 K at 0.5 mm only), the times to 63 % (T3 to T5: part on a 14 mm pad -12.4 % FVM, Lumped -13.1 % and Analytic +12.9 % with vias, FDM +25.2 % for the part across the edge). The bounds of R4a, R3a and R5a (Lumped) held.

The corrected table describes this run (sizes measured, not predicted).

### 6.4 Error against the independent solver (rise, v2.4.4 / tree, %)

Reference rise from `study_references.py` (solver cell equal to the model cell). Selected rows:

| Board | Cell | FVM | FDM | Lumped | Analytic | 3D solid |
| :-- | --: | :-- | :-- | :-- | :-- | :-- |
| plate_uniform | 1 | -0.15 / -0.15 | -0.15 / -0.15 | +0.50 / +0.50 | -0.47 / -0.47 | 0.00 |
| one_layer_full | 1 | -0.01 / -0.03 | -0.01 / -0.03 | +0.60 / +0.60 | -0.56 / -0.56 | 0.00 |
| plate_pad (20 mm window) | 2 | -7.94 / -2.92 | -23.80 / -23.43 | -18.78 / -18.78 | -58.02 / -58.02 | +0.07 |
| plate_pad | 1 | -5.57 / -2.12 | -14.38 / -13.49 | -15.81 / -15.81 | -56.48 / -56.48 | +0.14 |
| plate_pad | 0.5 | -4.35 / -1.66 | -9.00 / -7.49 | -15.63 / -15.63 | -55.60 / -55.60 | +0.22 |
| one_layer_pad | 1 | -3.11 / -1.73 | -13.23 / -12.90 | -11.13 / -11.13 | -34.41 / -34.41 | +0.13 |
| one_layer_pad | 0.5 | -2.61 / -1.48 | -7.79 / -7.22 | -11.85 / -11.85 | -33.19 / -33.19 | +0.21 |

Only the FVM and, less, the FDM improve (laminate rule); Lumped and Analytic do not change on these boards and stay far from the solver on a bare pad (documented limit; the input check warns). Boards with vias have no independent reference here; against the 3D solid at 2 mm: plate_vias (136.87) FVM 136.77 to 137.72, Analytic 142.21 to 137.64, Lumped 138.06 to 140.36; plate_lone_via (153.37) FVM 152.78 to 151.52, FDM 147.96 to 148.69, Lumped 153.80 to 154.48, Analytic 155.48 to 152.11.

### 6.5 The freeze (dry run) and the permanent test

`study_freeze_reference.py ... --version 2.4.5` refuses on this tree ("the run is of program version 2.4.4, not 2.4.5"). With `--version 2.4.4 --out <scratch>` it writes 251 records (127 bit, 124 moved), 58 transients and 4 skipped, 0 alarms; that file is not kept. `tests/test_frozen_numbers.py` is skipped with "the frozen numbers v2.4.5.json do not exist yet". `tests/test_classify_logic.py`: 8 passed (a test of the table corrections was added). The comparison of a live run with a frozen file was not exercised.

### 6.6 What was not done

No `reference/v2.4.5.json`; peak memory not measured; frozen-file comparison not run; FVM/FDM above 400 000 and the 3D solid above 150 000 unknowns not run; transients only as the time to 63 %; boards with vias have no independent reference. No program defect found; one point for the maintainer: the sentence "Lumped and Analytic unchanged" (commit messages, CHANGELOG) is true for the field but not for the mean under a part on an outline board (0.1 to 1.9 K; the sentence proposed is in 7.4).

## 7. Review

Status: **reviewed; go for the 2.4.5 freeze** once the version is bumped, with the corrections below (all in this folder; nothing in the program). Every command was re-run on the tree at develop `9e890be` with `nice -n 10`, one job at a time, on the shared machine.

### 7.1 The quick set re-run, and can the harness fail?

`study_baseline_release.py --tag v2.4.4 -- --quick` (14.8 s) and `study_run_suite.py --quick` (19.7 s): 85 runs each, all ok, and every number **bit-identical** to the tester's quick sets (`out/v2.4.4.json`, `out/rc.json`); `study_diff.py --strict`: 470 shifted numbers, all `expected`, 39 records identical, 0 alarms. The full sets were not re-run (the quick sets are their 2 mm part and match to the bit); every number of 6.1, 6.2 and 6.4 was re-read from `out/diff_v2.4.4-full_vs_rc-full.json` and `study_error_vs_reference.py` (reproduced to the printed digit). During the review `develop` moved to `4021cd7` (cleanups of `fix/point-via`: warnings, comments); its quick set (`git archive`, `--program-root`) equals the reviewed candidate in every number (0 differences against a file frozen from it) and the diff against v2.4.4 has 0 alarms.

Faults were injected into a copy of the full result set (one number changed, the rest the reviewed candidate):

| Fault injected (2 mm unless said) | Table of the first run | Corrected table |
| :-- | :-- | :-- |
| reference_board FVM hottest point +1e-12 K | must_not_move (alarm) | must_not_move (alarm) |
| plate_pad Lumped +0.5 K | must_not_move (alarm) | must_not_move (alarm) |
| plate_pad FVM -30 K (the laminate rule goes up) | out of range, **not an alarm**: `--strict` exits 0 | alarm |
| example_board FVM +5 K and +20 K (reviewed shift -0.27 K) | **expected** (R3a allows 45 % of a 60 K rise, 27 K) | alarm |
| plate_vias Analytic +10 K (reviewed shift -4.77 K, so +5.2 K) | **expected** (R5c allows 25 % of the rise) | alarm (the sign of the reviewed shift) |
| part_across_outline FDM 8 K further down at 1 mm | **expected** (R1a 30 K) | alarm |
| round_outline FDM part mean +0.3 K | unexplained (alarm) | unexplained (alarm) |
| plate_pad FVM minimum +0.1 K | **expected** (R3c 45 % of the rise) | alarm |
| example_board FVM balance error +0.01 W, power in +0.5 W | **expected** (no bound on the balance) | alarm |

And a fault in a copy of the program (the via well conductance `viawell.well_conductance` times 0.9; quick set, `--program-root`): the hottest points of the ten FVM and FDM records with vias move by 0.07 to 0.13 K. The classified diff against v2.4.4 cannot see a fault that small on a board that a release item already moves by 0.3 to 1.5 K (only one time to 63 % went out of range, by chance); the **frozen comparison** sees it on all ten records (126 differences). The two tools do different jobs: the classified diff attributes the release's shifts and stops gross errors; the frozen file holds every later version to the reviewed numbers.

Defects of the harness found and corrected:

1. **An out-of-range shift was not an alarm** (`regress_classify.ALARMS` had only `unexplained` and `must_not_move`): a shift on a board that an item reaches, in the wrong direction or ten times too large, passed `--strict` and the freeze. Now `expected_out_of_range` is an alarm in the diff, `--strict` and the freeze.
2. **Bounds in K were compared with checksums and counts**: R4d, R3g and R6a gave `abs_k` and `rel_rise` to the field sums and the unknowns of the SOR runs, so 8 SOR numbers were `expected_out_of_range` (example_board, plate_vias, plate_lone_via, plate_uniform, two_layer_partial: `t_sumsq`, `t_sum`, `unknowns`); the README said "0 out of range" because only the steady records were counted. Each bound now applies to its unit only (`abs_k`, `rel_rise`: temperatures; `rel`: counts; new `abs_w`: the heat balance in W; the checksums are not bounded).
3. **The freeze ignored the SOR runs and the times to 63 %** when it checked for alarms; it now counts them like `study_diff.py --strict`.
4. **The times to 63 % had no bound** (every change on a may_move board was `to_be_explained`, never an alarm); each entry now has `rel_change` and limits per board and model.
5. **`PCBT_FROZEN_BIT_TOL` did not work on the heat balance**: the tolerance of a `bit` balance error was relative to the error itself (round-off, 1e-14 W), so it was 1e-23 W; with NumPy 2.3.5 / SciPy 1.16.3 against 2.5.4 / 1.18.1, 8 records failed on `balance_error` alone at `PCBT_FROZEN_BIT_TOL=1e-9` (7.5). Now relative to max(|value|, 1 W).
6. The documented `study_baseline_release.py ... --quick` fails (argparse): the arguments for the suite go after `--`; docstring and section 2 corrected. `study_diff.py` now warns when the two sets come from different environments (exact equality is then meaningless: 79 false alarms between the two library versions on the same machine).

Regression tests: six new tests in `tests/test_classify_logic.py` (out of range is an alarm; units of the bounds; per-cell limits; every bounded rule has a limit for each board, model and cell of its scope; bounded times to 63 %; the bit tolerance on the balance); 14 pass.

### 7.2 Are the bounds honest? (`reference/expected_shifts.json`)

No: they were written as hypotheses from the documents and kept after the run. Measured on the full sets against the bounds (largest shift of the rule on that board, all cells):

| Rule | Bound | Largest measured | Ratio |
| :-- | :-- | :-- | --: |
| R3a laminate, hottest point | 45 % of the rise | plate_pad 5.5 % (17.5 K); example board 1.3 % (0.79 K); hatched 2.1 % | 8 to 35 |
| R4a point via | 10 % of the rise | 1.1 % (plate_lone_via 1.45 K) | 9 |
| R5a, R5c via constriction | 25 % of the rise | 3.3 % (Lumped, example), 4.1 % (Analytic, plate_vias) | 6 to 8 |
| R4d SOR with vias | 30 K | 1.26 K | 24 |
| R1a part across the outline | 30 K | FDM 21.8 K at 1 mm, 5.7 K at 0.5 mm; FVM 13.7 K | 1.4 to 5 |
| R1b, R2d part means | 60 K | 34 K (FVM, 3D solid), 22.5 K (FDM) | 1.8 to 2.7 |
| balance rules (R3d, R4b, ...) | none | 1e-12 W (power in moves only with the top path: -0.031 W) | unbounded |

The **30 K of R1a** was set just above the largest FDM shift (21.8 K at 1 mm) for every board and cell of the rule, so a 25 K error at 0.5 mm (reviewed 5.7 K) or on the example cut to a T (reviewed 1.2 K) would have passed. The shift itself is right (7.3).

`scripts/study_tighten_table.py` now writes `limits` into every quantified or derived rule: per board, model **and cell**, 1.25 x the shift measured on the reviewed full run (floors 0.05 K, 0.1 % of a count, 1e-9 W), and the sign of every temperature that moved by more than 0.05 K (a later shift of more than 0.05 K the other way is out of range); the may_move entries of the times to 63 % get 1.25 x their measured change (floor 1 %). R1a becomes 21 / 28 / 7.2 K for the FDM at 2 / 1 / 0.5 mm (FVM 2.2 / 18 / 4.7 K) and 0.05 to 1.5 K on the example cut to a T. The general bounds stay in the table as the hypotheses of the documents. On the reviewed sets: full 1422 expected, 59 SOR expected, 41 times expected, 0 alarms; quick 0 alarms. The cost: the table now describes this candidate (any later commit of 2.4.5 that moves a number by more than a quarter of the reviewed shift alarms and must be explained, which is the purpose before the freeze); after the freeze the frozen file is the guard.

### 7.3 The FDM hot spot of `part_across_outline`: a correction, checked independently

The FDM falls 16.2 / 21.8 / 5.7 K at 2 / 1 / 0.5 mm, the FVM 1.7 / 13.7 / 3.7 K and the 3D solid 1.7 / 14.1 / 3.8 K (the tester's "the FVM moves only -1.7 K" was the 2 mm value). Before, the three models scattered with the cell (FVM 231.7 / 243.7 / 232.9, FDM 246.8 / 252.0 / 234.9, 3D solid 232.6 / 245.2 / 233.9 degC); after, they agree within 1.4 K at every cell (229.2 to 231.2 degC) and move by at most 0.9 K with the cell.

Independent reference: the board is a 37.3 x 40 mm rectangle with the part on its last 6.3 mm, which the layered solver (`research/solid3d-verification/lib/layered3d.py`) can represent with the edge on a cell edge. Same board on both sides (laminate 0.3 W/mK in every direction, copper 385 W/mK, 35 um, h 10 / 15 W/m2K, film under the source, insulated sides, 4 W on the board part of the part); 0.2 mm cells, 8 laminate slabs, edges at 37.2 and 37.4 mm (rise 215.62 and 213.66 K), so 214.64 K at 37.3 mm by interpolation, and 196.1 K for the mean over the source. Program with the same materials (scratch script, not kept):

| Rise [K] (mean under the part) | 2 mm | 1 mm | 0.5 mm |
| :-- | :-- | :-- | :-- |
| FVM v2.4.4 | 216.85 (172.3) | 229.68 (175.5) | 218.25 (160.4) |
| FDM v2.4.4 | 232.87 (201.5) | 238.02 (200.2) | 220.32 (171.9) |
| FVM tree | 215.21 (197.3) | 215.47 (197.1) | 214.36 (196.0) |
| FDM tree | 216.02 (197.1) | 215.46 (196.2) | 214.43 (195.5) |
| 3D solid tree | 215.44 (197.4) | 215.71 (197.2) | 214.60 (196.1) |

Before: FDM +8.5 / +10.9 / +2.6 %, FVM +1.0 / +7.0 / +1.7 %; the part mean of the FVM read 160 to 176 K against 196 K (cells off the board in the mean). After: every model within +0.6 % of the reference, the part means within 0.6 %. Attribution by `git archive` copies (2 / 1 mm): `62afbb8^` = v2.4.4; `62afbb8` moves the FDM to its final values (216.02 / 215.46) and the FVM to 212.28 / 215.47; `7a5b0ee^` = `62afbb8`; `7a5b0ee` (cover 8 x 8) moves the FVM and the 3D solid at 2 mm only (212.28 to 215.21) and leaves the FDM bit-identical (its node cover was already 8 x 8). The cause in 2.4.4: the FDM spread the footprint coverage of every sub-cell, including the 21 % of the part off the board, onto the four nodes of the cell, so the power of the part off the board was piled onto the edge nodes whose conductances carry only their board share; `62afbb8` gives a cell the share that is both in the part and on the board. The time to 63 % of the FDM (26.5 to 33.2 s, +25 %) now agrees with the FVM (33.5 s). Physical and consistent: **not a defect**; a correction of 10 % of the rise that the CHANGELOG states only as "up to 16 K in an edge-shift sweep" (7.4).

### 7.4 "Lumped and Analytic unchanged": the CHANGELOG sentence

Measured: the field, hottest point and junction temperatures of the Lumped and Analytic are bit-identical on every board without vias, also on the outline boards; the mean under a part on an outline board moves in the Analytic by -0.71 K (round), +0.11 K (T), -1.37 / -1.37 / -1.92 K (part across the outline at 2 / 1 / 0.5 mm), up to 1 % of the rise, and in the Lumped by 1e-14 K (round-off). The CHANGELOG (Unreleased, "Part across the board outline") says "The Lumped and Analytic models and boards without an outline are unchanged (bit-identical); the maximum and the junction temperatures do not move." Proposed replacement:

> In the Lumped and Analytic models the temperature field, the hottest point and the junction temperatures are unchanged (bit-identical); on a board with an outline the mean under a part is now read on the board only (8 x 8 cover) and moves by up to 2 K in the Analytic (1 % of the rise; -1.9 K for a part across the edge at 0.5 mm). Boards without an outline are unchanged in every model.

And, after "up to 16 K in an edge-shift sweep on a small T": "(on a 40 mm board with a 4 W part across the edge the FDM hottest point falls by 22 K at 1 mm and the FVM by 14 K; the three models now agree within 1.4 K and within 0.6 % of an independent layered solver)". The commit messages cannot be changed (published history); the CHANGELOG is the place.

### 7.5 The frozen numbers: robustness and tolerance

Measured on this machine (quick set, `regress_frozen.compare` of a run against a file frozen from the reviewed sets, `--version 2.4.4` into a scratch file, not kept):

* run again: identical (85 of 85 records, also against the tester's run);
* one thread (`OMP`, `OPENBLAS`, `VECLIB`, `MKL` = 1): identical;
* NumPy 2.3.5 / SciPy 1.16.3 (scratch environment) against 2.5.4 / 1.18.1: **8 of 44 bit records fail exact equality**; largest temperature difference 2.8e-11 K (finned block), field checksums 7e-13 relative, the rest the balance error (round-off); with `PCBT_FROZEN_BIT_TOL=1e-10` or `1e-9` (after correction 5) all pass; the moved records (1e-6 K) pass;
* the injected 10 % via fault: 126 differences on 10 records at any of these tolerances;
* the live test (`tests/test_frozen_numbers.py` with `PCBT_FROZEN_FILE` on the scratch file, 2 mm, `PCBT_FROZEN_TRANSIENTS=1`): **144 passed in 27 s** (the first time the comparison of a live run was exercised).

So the bit records would fail on another machine or after a library update, and the distinction bit / moved has no physical meaning for a later version (a number that 2.4.5 moved is no less a guard in 2.4.6). Recommended policy: one tolerance for every record, independent of the class (the class stays as information: what 2.4.5 did not touch): temperatures 1e-8 K absolute (300 times the library noise measured, far below any model change seen in this suite: the smallest real shift is 1e-4 K), field checksums 1e-10 relative, heat balance 1e-9 W, unknown counts and skipped status exact, times to 63 % 1e-6 relative; exact equality only as an option on the machine that froze the file. Not measured: another CPU architecture (x86-64, other BLAS); the 1e-8 K margin is expected to hold there (the solver is LU with the same ordering), not shown.

### 7.6 The decisions of `INTEGRATION.md`

1. **Where the frozen test lives**: in `tests/` (`tests/regression/` with the four library files and `v2.4.5.json`), so that it runs with the battery; the research folder stays as the record. When copied, its fixture must call `model.reload_libraries()` after setting `PCBTHERMAL_CONFIG` (the libraries are module lists refilled in place; a test that leaves them changed would make the frozen numbers depend on the test order) (not tested here).
2. **Exact equality or tolerance**: tolerance by default, the one of 7.5; `PCBT_FROZEN_BIT_TOL=0` for the exact check on the machine that froze the file.
3. **2 mm in the whole battery**: yes, 27 s with the times to 63 % (about 5 % of the battery); 2, 1 and 0.5 mm (about 2 minutes on a loaded machine, the full run took 105 s) in the release procedure only. For 2.5.0: copy the files, regenerate `v2.4.5.json` at the release of 2.4.5 with the version bumped, add the stress of a new model or board as a board of the suite and refreeze when 2.5.0 changes a number on purpose (`INTEGRATION.md` 2).
4. **The diff table of each release**: keep it. `out/` is git-ignored, so keep the table of expected shifts per release (`expected_shifts_<version>.json`, with its limits) and a short summary of the classified diff (counts, alarms explained, the shifts of the hottest point) in the research folder of the release and in the pull request; the full Markdown is regenerated by `study_diff.py` from two runs.

### 7.7 What was not verified

The full sets were not re-run by the review (the quick sets match the tester's to the bit; the full numbers were re-read from the tester's outputs). Another CPU architecture or operating system. The independent check of 7.3 uses the solver the battery uses (`layered3d.py`) and interpolates between two widths (37.2 and 37.4 mm; the two differ by 2 K, so the interpolation error is a fraction of 0.1 K); a converged reference in the cell (0.1 mm) was not run (memory: the 0.2 mm solve took 6.6 GB). The boards with vias still have no independent reference here. Peak memory of the suite was not measured.
