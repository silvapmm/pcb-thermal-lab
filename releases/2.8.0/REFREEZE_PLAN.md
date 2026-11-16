# Refreeze of 2.8.0: plan (prepared, not run)

Status: **written, nothing of the harness was run.** What exists: the item table as a script (`refreeze/scripts/make_expected_shifts_2_8_0.py`), a PROVISIONAL table made from committed JSON only (`releases/regression-harness/reference/expected_shifts_2.8.0.json`, key `"provisional": true`), its tests (`refreeze/tests/`, 3 passed, 0.07 s), and one change of a harness script (`study_run_suite.py` accepts `--models ... fem`; it was refused by the choices before). Procedure of record: `CLAUDE.md` section 6 'Frozen numbers', `releases/regression-harness/INTEGRATION.md` 2.

## 1. What is frozen against what

* **Baseline**: the tag `v2.7.1`. It moved no frozen number (`releases/2.7.1/final-opinion/README.md` 3: `tests/regression` untouched, frozen numbers pass), so its numbers are those of `tests/regression/data/v2.7.0.json`; the harness still RUNS the tag, because the three new boards (`drawn_inset_square`, `drawn_stripes_pad`, `drawn_ell`) are in no frozen file and only a run gives their baseline.
* **Target**: the tree after the version bump (`study_freeze_reference.py` refuses a run whose program version is not `--version`), run with the finite-element model (`--models fvm fdm lumped analytic solid3d fem`).
* **Pending files** (`tests/regression/data/pending/`, base version 2.7.0, six files): four hold shifts, two hold additions. All six are folded by the refreeze and deleted in the same commit (`test_pending_shifts_belong_to_the_frozen_release` fails on a pending file of an older base).

## 2. The item table (what may move, by how much)

Built by `make_expected_shifts_2_8_0.py`; ids in the table (`items`). Numbers below are measured from the pending files against `v2.7.0.json` (committed numbers, no new run); the final run replaces every limit by 1.25 x its own shift.

| Id | Item (branch, pending file) | Moves | Size seen in the pending files | Records |
| :-- | :-- | :-- | :-- | --: |
| M1 | Every face film of a copper node passes the half copper layer (`fix/face-film-half-slab`, `face-film-half-slab.json`) | FVM, FDM, Lumped, Analytic, every board, 2, 1, 0.5 mm; the 3D solid moves nowhere; Outside the frozen boards (reproduction pass, prose only, no stored tolerance): the shift is the film term itself, about q_f t / (2 k) with q_f = h theta the flux through the film and t / k of the outer layer or block, so it grows with t / k: a 10 mm plate of k 150 W/mK at 400 W/m2K and a 70 K rise moves +0.93 K (400 x 70 x 0.010 / (2 x 150) = 0.93 K, +1 %, FVM, FDM and Analytic alike), a 6 mm stainless block +0.7 K, an aluminium block +0.1 K, a via array resistance +0.34 % (`reproduction/PART-C.md` 1, finding 2) | all hotter; median 2e-5 K, at most 0.040 K (finned block); heat into the block 1.1e-3 W; top-path split 1e-7 W (Analytic, FDM, FVM) and 0.044 W (Lumped, with M3) | 204 records, 29 times |
| M2 | Drawn copper read as imported copper (`fix/drawn-copper-faces`, `drawn-copper-faces.json`) | FVM and FDM of `example_board`, `example_cut_to_T`, `profile_board`, `two_layer_partial` at 2 mm only; 8 times to 63 %; the three `drawn_*` boards; outside the frozen boards (reproduction pass, prose only, no stored tolerance): the calculator's JEDEC board without vias +12.0 % (74.6 to 83.5 K/W at 0.5 mm, the converged value; 74.6 was a grid error of the cut land), the other calculator rows +0.9 to +1.1 %; reproduction band: FVM where a drawn edge cuts a cell up to +12.5 % of a part's rise (`reproduction/LUMPED_SHIFTS_REVIEW.md` 2) | 4 boards x 2 models x 1 cell = 8 records (credited through `also_moved_by` of M1's file) | 8 records, 8 times |
| M3 | Lumped part rows read the own peak; first link sees the images of the sides (`fix/lumped-part-readout`, `fix/lumped-edge-first-link`, `lumped-first-link-edge.json`) | Lumped of every board at 2, 1, 0.5 mm: part rows up to 14.9 K (part peak of a lone part), board maximum -3.1 to +3.1 % of the rise with both changes (-0.5 to +3.1 % by the first link alone; `part_top_path` -2.7 to -3.1 % is the part read-out, `WHAT_MOVED.md` 3); 12 times to 63 % (up to 20 % on the example board's small part); outside the frozen boards (reproduction pass, prose only, no stored tolerance): an isolated part whose copper is only its footprint +7.1 % of the rise on the board maximum, pads of 20 to 80 mm +1.6 to +3.3 % (`copper_dissipation.py`, 1 mm); reproduction band: Lumped board maximum -0.5 to +7.5 % of the rise (`reproduction/LUMPED_SHIFTS_REVIEW.md` 1) | credited through `also_moved_by` of M1's file (56 keys) | 51 records, 12 times |
| M4 | Exact cover of a metal block (`fix/block-exact-cover`, `block-exact-cover.json`, empty) | Analytic `finned_block` at 1 and 0.5 mm (+0.09 K); FVM, FDM, 3D solid, Lumped do not move (block edges on cell lines) | credited through `also_moved_by` of M1's file (3 keys) | 3 records |
| A1 | Finite-element comparison model (`fem-records.json`, `new_models`) | nothing: 29 records that exist only in the new run | ADDITIONS | 29 |
| A2 | Surface read-out (`surface-records.json`, `new_readouts`) | nothing: new metrics `surface:*`, `part:*:t_max_surface`, `part:*:t_mean_surface` on FVM and FDM records (51 + 51), also on the SOR runs | ADDITIONS | 102 |
| A3 | FEM conjugate-gradient tolerance 1e-10 | nothing old: the FEM records are not bit-identical run to run above `FEM_DIRECT_MAX` (5e-10 K measured) | held under the tolerance, never `--exact` | - |
| M0 | Items with no frozen record (analytic transient hot point, warning texts, typical-value marks, calculator, GUI) | nothing; a shift attributed to them would be a defect | - | - |
| L8 | Round-off | at most 1e-8 K | R0 | - |

Rules written by the script (preview run): R1 M1 Analytic (16 boards), R2 M1 FDM (17), R3 M1 FVM (17), R4 M1+M2 FDM (4 boards, 2 mm), R5 M1+M2 FVM (4), R6 M1+M3 Lumped (17), R7 M1+M4 Analytic (`finned_block`), D8 to D11 the derived bounds of the `drawn_*` boards (preview only), R0 round-off; 38 `may_move` entries for the times to 63 % (M1, M2, M3 and their sums) plus four derived for `drawn_*` and T0 round-off. One `must_not_move` entry: N1, the 3D solid on every board and cell (no item reaches it; the pending files hold no `solid3d` record). One `added_metrics` scope: A2 for `fvm`, `fdm` and `fvm_sor` (the SOR runs carry the surface too).

**Checked by the tests of `refreeze/tests/` (reading only, no solver)**: every moved metric of the 204 + 8 + 51 pending records (more than 1000 numbers) is `expected` against the provisional table; no record has no item (`??`); the added scope names `surface:*` and the part surface metrics for the FVM, FDM and SOR run and not for the Lumped, and nothing else; the FEM keys are not in the baseline; the 3D solid is `must_not_move`; the two files of additions credit no item to a shift; the `drawn_*` boards get their items by model. This proves the table covers what the pending files say. It does NOT prove the tree still produces those numbers: that is `study_diff.py` after the run (section 4).

## 3. Differences from the 2.7.0 procedure (traps found by reading)

1. **`make_expected_shifts.py` (2.7.0) cannot be run as is**: its items, item map and file names (`v2.6.0.json`, `expected_shifts_2.7.0.json`) are written in, and a pending file of additions would be credited as an item of every shift. The 2.8.0 script reads the pending files, excludes the files with `new_models` or `new_readouts` from the attribution, credits the older items through `also_moved_by` (`attribute`, tested by `releases/regression-harness/tests/test_expected_shifts.py`) and takes the `drawn_*` boards by model.
2. **`study_run_suite.py --models` refused `fem`** (choices = the five default models): corrected in this branch (`OPTIONAL_MODELS` accepted, never default). The baseline run on `v2.7.1` is made WITHOUT `fem` (so the FEM records are only in the new set, `missing.only_in_new`, which is information and not an alarm); with `fem` the harness would record them as skipped ("model absent in this version") and the diff would see a status change.
3. **The surface metrics are present in one set only**: `regress_classify.diff_sets` calls them `expected` only where the table's `added_metrics` scope names them; without the scope each is an alarm (`present in one set only`). Do not cover them with a rule on `status` (it would excuse a failed run).
4. **The three new boards**: in `board_names()`, so both runs carry them; their records and times are in no frozen file, so they appear as `moved` or new in the refreeze; the frozen test count grows (not predicted here: it depends on which runs the caps accept; the 317 of the last release is the old figure). `docs/versions.md`, `CLAUDE.md` and the README quote the count and must follow.
5. **FEM records need `pyamg`** above `FEM_DIRECT_MAX` (30 000 unknowns): the harness environment must have it (`.venv/bin/python -c "from pcbthermal import femcore; print(femcore.available())"` must print `True`), or the final set lacks records that the pending file holds. The harness caps the FEM at `FEM_CAP = 130 000` unknowns (about 1 GB and 20 s with pyamg by the comment of the harness; **not measured here**).
6. **Environment**: both sets must be run in the same Python, NumPy and SciPy (`study_diff.py` prints a warning when `environment` differs: exact float equality of the `bit` records breaks across library versions, 2.8e-11 K measured in 2.4.5).
7. **`docs/version-comparison.md`** (`regen_version_comparison.sh`, `reference/version_notes.json`) is written for 2.7.0 (17 boards, labels up to `v2.7.0`); a v2.7.0 to v2.8.0 pair needs notes and the script's label list. It is a document, not a gate item of the refreeze: decide with the maintainer (open decision 3).

## 4. The commands, in order

All from the repository root, `.venv/bin/python`, `QT_QPA_PLATFORM=offscreen`, one job at a time, `nice -n 10`, on a quiet machine (the load rules of `RELEASE_GATE.md` 0). Branch `release/2.8.0-refreeze` from `development` (the record of 2.7.0: `release/2.7.0-refreeze`). `R=releases/regression-harness/scripts`.

```sh
# 0. after the bump commit (version 2.8.0 in pcbthermal/__init__.py, CHANGELOG [2.8.0], README); the harness reads the version of the tree
.venv/bin/python -c "import pcbthermal; print(pcbthermal.__version__)"            # 2.8.0
.venv/bin/python -c "from pcbthermal import femcore; print(femcore.available())" # True (pyamg)
# 1. baseline: the tag v2.7.1 extracted outside the repository, the same harness, no fem
.venv/bin/python $R/study_baseline_release.py --tag v2.7.1                        # -> releases/regression-harness/out/v2.7.1.json
# 2. the tree, with the finite-element model; label final
.venv/bin/python $R/study_run_suite.py --label final --models fvm fdm lumped analytic solid3d fem   # -> out/final.json
# 3. the table from the two sets (replaces the provisional one; measured limits, drawn_* included)
.venv/bin/python releases/2.8.0/refreeze/scripts/make_expected_shifts_2_8_0.py releases/regression-harness/out/v2.7.1.json releases/regression-harness/out/final.json
# 4. diff, classified against the table; must end with "alarms: 0; failed checks: 0"
.venv/bin/python $R/study_diff.py releases/regression-harness/out/v2.7.1.json releases/regression-harness/out/final.json \
    --table releases/regression-harness/reference/expected_shifts_2.8.0.json --strict
# 5. (optional, after the diff is read) sign and tighter limits on the full sets
.venv/bin/python $R/study_tighten_table.py releases/regression-harness/out/v2.7.1.json releases/regression-harness/out/final.json --out releases/regression-harness/reference/expected_shifts_2.8.0.json
# 6. freeze: refuses while there is an alarm, a wrong program version, or an existing file
.venv/bin/python $R/study_freeze_reference.py releases/regression-harness/out/v2.7.1.json releases/regression-harness/out/final.json --version 2.8.0 \
    --table releases/regression-harness/reference/expected_shifts_2.8.0.json          # -> releases/regression-harness/reference/v2.8.0.json
# 7. the same commit: copy the frozen file, delete the six pending files
cp releases/regression-harness/reference/v2.8.0.json tests/regression/data/v2.8.0.json
git rm tests/regression/data/pending/{block-exact-cover,drawn-copper-faces,face-film-half-slab,fem-records,lumped-first-link-edge,surface-records}.json
# 8. the frozen numbers at the three cells, against the NEW file (the test reads the newest), and the harness tests
PCBT_FROZEN_CELLS=2,1,0.5 .venv/bin/python -m pytest -q tests/regression
.venv/bin/python -m pytest -q releases/regression-harness/tests releases/2.8.0/refreeze/tests
```

The step-1 and step-2 runs write `releases/regression-harness/out/` (git-ignored, never added). `study_diff.py --strict` writes `out/diff_v2.7.1_vs_final.md`: keep it in the report of the gate (`releases/2.8.0/refreeze/` is the place; the JSON stays out of git). Stage by path: `tests/regression/data/v2.8.0.json`, the deleted pending files, `releases/regression-harness/reference/v2.8.0.json`, `releases/regression-harness/reference/expected_shifts_2.8.0.json`.

## 5. Expected result

* `study_diff.py --strict`: **0 alarms and 0 failed checks.** Shifts: all `expected` (items M1 to M4 and round-off); the surface metrics `expected` by A2; times to 63 %: all changed ones `expected`; the SOR runs equal the direct FVM within 1e-3 K (internal check). The FEM records and nothing else are listed under 'Records present in one set only'.
* The frozen file: `records` of the five models plus `fem`, `skipped` listing what the caps refused; `alarms_when_frozen` 0; each FEM record class `moved` (no baseline; the pending files call it `new`; the class is information only, section 6 risk 3).
* After the fold the test no longer applies a pending file; the record of the difference is the table, the diff Markdown and the CHANGELOG entry.

## 6. Risks

1. **A late number-moving change restarts the refreeze** (one refreeze per version). Open items that could move a number: the FEM transient (planned in the maintainer's order, no branch yet) does not touch the frozen steady records; `fix/gui-review-rest` and the GUI branches move no number by their plan (no pending files, `GUI_FIX_PLAN.md` 1), but they change the report text. Check `git diff v2.7.1..development -- pcbthermal/fvm.py fdm.py lumped.py analytic.py laminate.py viawell.py copper.py blocks.py` against the four items before the run.
2. **A record that moves with no item** shows as an alarm: it is a defect until proven otherwise (do not widen the table to silence it).
3. **FEM class**: the pending FEM records carry `class: new`; `regress_frozen.build` writes `moved` for a record absent from the baseline. The class is information only (one tolerance for every record, `INTEGRATION.md` 1; `regress_frozen.compare` reads no class); the point to check is that the gate never runs the FEM records with `PCBT_FROZEN_EXACT=1` (read in `regress_frozen.py`, not run).
4. **The FEM records of the final run may differ in number from the 29 of the pending file** (the new boards at 1 and 0.5 mm, a board near the cap): they are additions, the file simply has more; a pending record that the final run does not produce is a loss: compare `missing.only_in_new` and the 29 keys before the freeze.
5. **Memory and time of the final run**: the FEM at the cap and the 0.5 mm cells; the harness is written for a quiet machine; one job at a time. Times not measured here.
6. **Provisional limits**: the committed table is made from the pending files (measured by earlier runs of the tree at their merge). If the tree differs from those runs by more than 25 % in a shift, `study_diff.py` shows `expected_out_of_range`: read it, do not regenerate the table from the run that raised it before explaining the shift.
7. **Random-order or environment dependence**: the baseline and the final runs must come from the same environment (section 3, item 6).

## 7. Decisions left to the maintainer

1. Whether the FEM records enter the frozen file with `fem` in `settings.models` (recommended: yes, the comparison model is part of the program; the test then runs it in the battery at 2 mm; its cost is the memory of the frozen run, 3.6 to 4.1 GB resident measured by the review of the speed-up branch).
2. Whether the three new boards enter the frozen file (recommended: yes, they hold the drawn-copper change against a later regression; the cost is the record count).
3. Whether `docs/version-comparison.md` is regenerated for 2.8.0 (needs the labels, `version_notes.json` entry and the 20-board text) or left stale on purpose with a line in the documentation review.

## 8. What was not verified

The harness was not run (neither the v2.7.1 baseline nor the tree); no number of the provisional table was measured on the current tree; the `drawn_*` bounds are derived from validation 51.3 and 53, not measured; the FEM class handling of `test_frozen_numbers.py` was read in part; the time and memory of the refreeze runs are unknown; `study_tighten_table.py` and `study_freeze_reference.py` were read, not run.
