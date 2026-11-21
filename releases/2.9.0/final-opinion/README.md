# Final opinion of the reviewer: release 2.9.0

Release gate step 5 (`CLAUDE.md` 12, `docs/versions.md` A1/A7, `releases/2.9.0/PLAN.md` 5 item 5). Tree reviewed: `tmp/merge-batch14` at `a2a156a2`, against the tag `v2.8.0` (351 files, +34 357 / -960; 71 of them in `pcbthermal/`, `packaging/`, `.github/`, `README.md`, `CHANGELOG.md`, `LICENSE`, `requirements.txt`). The final whole battery of this tree was running in the tester's hands during the review; this opinion does not replace reading it.

## 1. Verdict

**GO WITH CONDITIONS.** No defect in the program blocks the release. The conditions are documentation edits at the version bump (section 4) and the final whole battery, read to the last line, green.

Conditions:

1. The final whole battery of `a2a156a2` (about 4555 tests, real-board environment proven loaded, about 11 to 12 skips) is green.
2. The bump commit carries the items of section 4, including the ones the documentation review left out (4.2).
3. Decision e33 (the two harness boards) is taken before the refreeze. Recommendation: add them in the refreeze. Without them the copper slabs of the 3D solid (all 20 harness boards have 35 µm copper) and the fixed interface pad over a top block have no frozen record. The pad fix is held only by `finned_block`, a bottom block, which moves by 0.002 K.

## 2. What was checked, and how

| Item | Check | Result |
| :-- | :-- | :-- |
| Pending files (`tests/regression/data/pending/`) | read the four files; compared `solid3d-pad-inplane.json` with `v2.8.0.json` record by record | `fem-thin-copper-source` 38 FEM records moved (fix of e20/e21); `fem-transient` 0 moved, 16 FEM times to 63 % added; `solid3d-pad-inplane` 3 `finned_block` 3D-solid records moved, largest metric shift +0.00206 K (`t_max`, 0.5 mm), t_sumsq -1.0e-5 relative; `surface-readout-models` 114 records with added surface metrics (Analytic 60, 3D solid 54), nothing moved. Each topic matches its CHANGELOG entry and its evidence file. No unexplained shift. |
| Pad in-plane claim of the reproduction pass ("held by the frozen numbers and its pending file only") | read `releases/2.9.0/reproduction/README.md` (line 54), the pending file and `tests/test_solid3d_pad_inplane.py`; ran the test (8 passed, 1.6 s) | Confirmed. The three block scripts are bit-identical because none of them runs the 3D solid with a top block. The fix rests on the test, which checks it against an independent stack solver and the FEM constant, and on the 0.002 K of `finned_block`. |
| FDM export positions (e44) | ran the example board at 2 mm (FVM + FDM) on this tree and saved it | `field_fdm.csv` first row `1,0.0,0.0,46.4519`, last row `4,100.0,80.0,43.6517`, as the CHANGELOG 'Fixed' entry says, with the before/after values. FVM keeps the cell centres (`1,1.0,1.0,...`). |
| Default stepping (Crank-Nicolson with Rannacher start, quarter steps) | re-ran `releases/2.9.0/transient-stepping/scripts/study_default_stepping.py` | The two-layer and disc rows of its README table reproduce to the printed digit (two-layer, command line: -5.01 % -> -0.17 %; disc, Animation: -12.51 % -> -0.39 %; disc, command line: -14.65 % -> -0.43 %). The change is in CHANGELOG 'Changed' with the before/after numbers and the way back (Scheme box, `--theta 1`). Projects store no scheme. `fem.solve_transient` defaults to `theta_scheme=0.5`. |
| FEM thin-copper source, NAFEMS T3, export positions, stepping tests | `tests/test_fem_thin_copper_source.py`, `test_fem_transient_closed_forms.py::test_the_one_dimensional_transient_benchmark`, `test_export_positions.py`, `test_transient_default_stepping.py` | 29 passed (10.5 s). |
| Campaign tree versus the two corrections | checked commit ancestry | Validation 56/57 name `7886ac42`. That tree already contains `fix/fem-thin-copper-source` (`b4985d9b`) and `fix/solid3d-pad-inplane` (`0642e46d`), so the campaign tables, and the 'usual agreement' ranges of the Difference view taken from them, include both corrections. |
| Status lines with '(column)' | grep in this tree | `main_window.py` 1867, `animation.py` 210 and `cli.py` 194 now say '(column)' (`fix/readout-names-status-lines`). |
| Licence statement | `LICENSE`, README 'Author and license', About box (`gui/help.py` 168-191), `CLAUDE.md` 5 | Consistent: MIT, (c) 2025-2026 Pedro Silva (PMS Labs). The library table matches `requirements.txt`, and `tests/test_help.py` holds it. reportlab (documentation only) and PyInstaller (build only) are in the table with their licences. `packaging/licenses/` holds Qt (LGPL-3.0, GPL-3.0), the pyamg fallback text and the `_system` texts (ICU, xcb-util, xkbcommon); `packaging/README.md` and `build.py` (`SYSTEM_NOTICES`) agree. |
| Packages | `gh run view 44906203155` | Green, on `b241b15e` (`build-test/release-builds-1`). Between `b241b15e` and this tree, `packaging/`, `.github/`, `selftest.py` and `bundle_info.py` are unchanged (only texts, pictures and records differ), so the trial run covers the release packaging. |
| What is not in 2.9.0 | `docs/versions.md` 'Planned: what the 2.9.0 plan leaves for later', `PLAN.md` after 1.2, doc review 3 | Explicit and honest in those three places. It is missing from the CHANGELOG and the README (condition 4.2-e). |

## 3. Findings, by severity

None of them blocks the release.

### Medium

**M1. No frozen record covers the 3D-solid copper slabs or a top block with a pad (e33).**
- Class: a limit to record, or a decision.
- Evidence: the CHANGELOG 'Copper slabs' entry ("every board of the harness has 35 µm copper, the 3D solid records are bit-identical"), `PLAN.md` row e33, and the pending file `solid3d-pad-inplane` (only `finned_block`, a bottom block).
- Impact: a later regression of the slab code or of the top-block pad would not be caught by the frozen numbers.
- Recommendation: add the two boards before the refreeze (condition 3).

**M2. The documentation review's bump list is incomplete.**
- Class: stale document.
- Evidence: section 4.2 below.
- Impact: without these edits the released manual would still say "development tree / next release / come with version 2.9.0", and `docs/version-comparison.md` would still say "stale until the refreeze of 2.8.0".

### Low

**L1. Three titles show 'Tmax' without '(column)'.**
- Class: display, a limit of the read-out naming rule.
- Where: `gui/results_view.py` 773-774 (results map), `gui/animation.py` 274 and `plots.py` 1606 (Animation map and GIF frame), `plots.py` 1336/1351/1353 (transient chart label and legend: 'Tmax', 'steady Tmax').
- Why it is low: each map's colour bar reads "Temperature, column mean (°C)", and the results map title has "column mean" on its first line.
- Linked pre-existing ambiguity (same lines, already in 2.8.0): the results map title "layer N, column mean / Tmax, Tmin, Tmean" gives the numbers of the whole board, not of the layer drawn. On the example board at 2 mm, the layer-4 map is titled "Tmax 85.3 °C" while that layer's maximum is 61.9 °C. The Animation title "Layer N ... Tmax" has the same issue.
- Decision on point (5): **acceptable for 2.9.0, not worth another battery before the release.** The change is text only, but it would need an executor, a review and a whole battery (about 60 min) for a label that the colour bar already qualifies.
- Fix in 2.10, one `fix/` branch: '(column)' on the three titles and the chart, and "board" or the layer's own extremes in the layer titles. Record it in 'Planned'.

**L2. A CHANGELOG sentence is stale.**
- Class: stale document.
- Where: `CHANGELOG.md` line 26 (FEM transient entry), "a published case is not yet reproduced".
- Why it is stale: line 37 (the campaign) reproduces NAFEMS T3 (36.6106 against the exact 36.6031 °C).
- Fix at the bump: add "(reproduced since by the campaign: NAFEMS T3, validation 57)".

**L3. The documentation review record is stale.**
- Class: stale document.
- Where: `releases/2.9.0/doc-review/README.md` 5.1 still lists the three status texts as open.
- Fact: they were fixed by `fix/readout-names-status-lines`, and section 2 above checked them.
- Fix: mark the item done in the commit that records this opinion.

**L4. The FEM default scheme is a literal.**
- Class: code consistency.
- Where: `fem.solve_transient(theta_scheme=0.5)`, while `fvm` and `fdm` use `fvm.DEFAULT_THETA`.
- Effect: the value is the same today, but a later change of the FVM default would not reach the FEM.
- Fix: 2.10, no number moves.

**L5. The help paragraph of the Animation omits the FEM.**
- Class: doc.
- Where: `pcbthermal/help/index.html` 343, "uses the FVM, FDM or analytic model".
- Context: the FEM in the Animation is described at line 255.
- Fix: 2.10, or at the bump if a help edit is made anyway.

**L6. Some new user texts write "W/m2K" instead of W/m²K.**
- Class: typography.
- Where: the warnings of `checks.py`, for example the drawn-L and thick-plate texts.
- Fix: cosmetic, 2.10.

**L7. Imprecise wording in a CHANGELOG entry.**
- Class: doc.
- Where: the 'Fixed' FEM thin-copper entry says "the 16 FEM times to 63 % ... move".
- Fact: those records are new in 2.9.0 (pending `fem-transient`, class `new`); they moved only between two branches of this version.
- Fix: optional, "were regenerated" at the bump.

### Risks for the user (point 2)

| Change | Assessment |
| :-- | :-- |
| Default stepping (Animation, `transient`, FEM) | The values of every animation and `transient` run change on purpose: first frame from -12 to -17 % to about -0.5 %. Documented in 'Changed', the help, the tooltip (`tips.py` "scheme") and the manual (1414, 1716, 1789). The old behaviour is one click or `--theta 1` away. |
| New CSV files | `hotspots_` (only when there is a hotspot), `zones_`, `parts_<model>.csv`, `parts_by_model.csv`, and `surface_<model>.csv` with three appended columns (the seven old ones first and unchanged). Old readers that read by column name keep working. |
| FDM CSV positions | Every `x_mm`/`y_mm` of `field_fdm.csv` and `surface_fdm.csv` is half a cell lower. The 'Fixed' entry gives the before/after rows and warns scripts that subtracted half a cell. |
| Warnings | The LPTN copper-window warning shares the Analytic criterion. Its text says it "also fires where the LPTN is within about 2 %". The drawn-L warning says "measured on one board". Honest and texts only (`tests/test_campaign_warnings.py`: fields bit-identical with the checks off). |

## 4. At the version bump

### 4.1 The list of the documentation review, section 4

The list is complete for:
- `__init__.py`
- the version badge
- CHANGELOG [2.9.0] with its short paragraph
- the README 'Versions' line
- `docs/versions.md` summary and chapter
- the 32 pictures after the bump
- the tests badge and `CLAUDE.md` 14
- the refreeze
- the manual PDF
- `CLAUDE.md` 15

### 4.2 What is missing or must be corrected in it

a. **Manual line numbers.** The `--version` row is **line 1687**, not 1686. Lines 3, 207 and 413 are correct.

b. **Three more manual sentences to reword at the bump:**
   - `docs/USER_MANUAL.md` 23: "Features marked 'since 2.9.0' are in the development tree and come with the next release." Delete it or reword it, for example "Features marked 'since 2.9.0' are new in this version."
   - `docs/USER_MANUAL.md` 139: "Ready-to-run packages ... come with version 2.9.0". Reword to the present tense.
   - Check line 1316 ("measured on its development tree"). It is true; keep it or name the commit `7886ac42`.

c. **`docs/version-comparison.md` header**: it says "stale on purpose until the refreeze of 2.8.0", which is itself stale. Reword it to "stale on purpose: ends at v2.7.0; its regeneration with every version is item e15 (2.10)".

d. **Refreeze, in the full A2 procedure** (after the bump):
   - `study_baseline_release.py --tag v2.8.0` and `study_run_suite.py --label final`.
   - `make_expected_shifts.py` writes `releases/regression-harness/reference/expected_shifts_2.9.0.json`, linking the four pending topics: `fem-thin-copper-source`, `fem-transient` (added times), `solid3d-pad-inplane` and `surface-readout-models` (added metrics).
   - `study_diff.py --strict` with 0 alarms.
   - `study_freeze_reference.py ... --version 2.9.0`.
   - Copy `reference/v2.9.0.json` to `tests/regression/data/` and delete the 4 pending files **in the same commit**.
   - Add the 2.9.0 label to `reference/version_notes.json` if the harness needs it.
   - Then `PCBT_FROZEN_CELLS=2,1,0.5 pytest tests/regression` green.
   - If e33 goes in: add both boards to `tests/regression/regress_boards.py` **and** `releases/regression-harness/lib/regress_boards.py` (byte-identical, `tests/regression/test_harness_copy.py`) in one commit before the harness runs. They are then "added" records of v2.9.0, frozen at the refreeze. Board (a): 420 µm copper with a part over absent copper. Board (b): `top_block_pad`, 40 x 30 mm, 3 W, 8 x 8 mm part, 5 mm aluminium top block at 5e-3 m²K/W (PLAN row e33).

e. **"Not in 2.9.0" in the CHANGELOG and the README.** Add one sentence at the end of the CHANGELOG [2.9.0] short paragraph and of the README 'Versions' line, for example "Not in 2.9.0: the FEM on slanted or curved outlines and on imported copper, the measured memory law, the version comparison, the surface of a time simulation (see docs/versions.md 'Planned')". Today the list is only in `versions.md`, `PLAN.md` and the documentation review.

f. **CHANGELOG line 26** (L2) and the wording of L7.

g. **`CLAUDE.md` 11, first bullet**: it still says the FEM "ships steady in 2.8.0; the transient and the comparison campaign are in 2.9.0". At the bump, reword it to the state after 2.9.0 (steady and time; campaign in validation 56/57).

h. **Pictures**: regenerate the 32 pictures after the bump. If the L1 fix is ever made, it changes `results_temperature*`, `animation*` and `results_views*`, which is one more reason to leave it for 2.10, when the pictures are regenerated anyway.

i. **Release workflow (not exercised)**: the draft-creating job and `check_release.py` have not run on a tag. Before tagging, push the final `main` commit to a `build-test/` branch, download the three artifacts and run `packaging/check_release.py files --version 2.9.0` locally on them. On the tag, while the release is a draft, a failed runner may be re-run on the same commit (A1). Any code fix needs 2.9.1. The real QtGui swap test per system stays open (PLAN e42b, the maintainer's).

## 5. What was not verified

- The final whole battery of this tree: it was running and is the tester's.
- The example-board and reference-board rows of the stepping study: only the two-layer and disc rows were compared to the digit.
- The 3D-solid copper slabs against the independent solver (rests on the branch review and `releases/2.9.0/solid3d-copper-slabs/README.md`).
- The FEM campaign tables of validation 56/57 (rest on their closing review). T3 rests on the published value; the primary NAFEMS document was not obtained, as stated.
- The Windows and Linux packages beyond the self-test of the trial run.
- The real Qt library swap.
- The 32 screenshots, which are regenerated after the bump.
- The reproduction pass ran 91 of 258 scripts by decision (`releases/2.9.0/reproduction/DECISION.md`); the other 167 were not re-run for this release.

## 6. Open decisions (maintainer)

1. e33: add the two harness boards in the refreeze (recommended) or move them to 2.10.
2. L1 (Tmax titles, and the board numbers under a layer title): 2.10 (recommended) or before the release with another battery.
3. Pre-tag check of the packages with `check_release.py` on a `build-test/` run of the final commit (recommended, about 30 min of Actions).
