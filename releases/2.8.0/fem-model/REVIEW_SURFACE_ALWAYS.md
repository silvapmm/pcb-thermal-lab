# Review: the surface read-out always computed and always shown (`feature/surface-always-both`)

Reviewer's record of the model-change review of commits `9e0070f0` (code and tests) and `6d3f0459` (documents and screenshots), on top of the merges of `docs/readout-always-both` and `docs/surface-readout-help`. Tree: this branch on `development` `dfde802b`, with the corrections of this review. Decision under review (maintainer, final): the surface is always computed and always shown beside the column mean for every steady FVM/FDM result; maps and graphs draw the column mean and name it; the surface is one click away in the Layer box; one surface column in the part table; surface files only on request; Tj, margin, power limit, top path, power coefficient and the Power Calculator stay on the column.

**Verdict: GO** for the merge, after the corrections below (all made on this branch). No number of any model moves.

## 1. Claims and verdicts

| # | Claim | Verdict | Evidence |
| :-- | :-- | :-- | :-- |
| 1 | `T_surf - T_col = t (2 q_top - q_bot)/(6 k)` on the outer faces, from the face fluxes read off K | Right | Independent 1D board (uniform source over the whole board, insulated edges; closed form by series resistances), FVM and FDM at 4 mm: where every watt crosses the layer (2 layers, 1 mm of 50 W/mK, no top film), surface minus column = 0.187500 K = `q t/(2k)` on both faces; under a plain heatsink the same; under a 3 mm metal block 0.1873/-0.1852 K (block sides lose heat); with films on both faces within 0.5 % of the series solution (2 and 4 layers, 35 um to 2 mm). |
| 2 | Inner copper: surface = column, no array | Right physically | An inner face is an interface with the laminate (continuous temperature); nothing can measure it. A part on an inner layer gets n/a with that reason (tested). |
| 3 | Laminate: a node; metal block: "a node of the block (resolved)" | **Wrong for blocks**, corrected | `blocks.py`: ONE node through the block thickness, so the block face is not resolved and has no surface read-out. Corrected in `thickness.py`, `docs/theory.md` 1.2c, `docs/models.md` 4b.1, `SURFACE_DECISIONS.md` row 9. |
| 4 | One-layer board: both faces of layer 0, Surface (bottom) = copper face against the laminate | Right | 1D plate test of `tests/test_thickness.py` and the block case of the review (source and block on the same face: net face flux about zero, offset 2 mK, consistent). |
| 5 | Outer layer drawn bare (no copper) | Right for the read-out | No copper, no copper term: surface = node (only the laminate face term under a source). Separate pre-existing limit: a bare layer with a DECLARED 1 mm copper thickness reads the bottom 2.1 K off the series solution (the empty copper slot carries no resistance); 35 um makes it negligible. Not this branch. |
| 6 | Face flux balance closes (3e-10 W) | Right | Re-run: -2.9e-10, 2.2e-11, -4.1e-11 W for 5 W at 0.035, 3, 10 mm. It checks that every exit of the layer is counted. |
| 7 | Flag `t/a > 0.5`, partly filled cells (peak = max(c, laminate peak), mean = f c + face mean) | Right | Code read against theory 1.2c; unchanged by this branch. |
| 8 | The trap: 1.215 K (`hatched_copper`) and 3.646 K (`drawn_ell`) board-level, part rows +0.000 K | Right, now explained with its closed form | The difference is exactly the laminate face term `q t_cu/(2 k_z)`: 3 W/(12 mm)^2 x 35 um/(2 x 0.3) = 1.2153 K; 1 W/(4 mm)^2 x 35 um/0.6 = 3.6458 K (re-run: 1.2153 and 3.6458, FVM and FDM). The part's column maximum holds the same term (`analysis._footprint_stats`), so the row difference is at most the copper term (raw 0.0 on `drawn_ell`). Wording "the difference is the copper term only" made precise ("at most"). |
| 9 | Thin copper +0.4 to +3.2 mK under the part | Reproduced on the example board | +1.33 mK (FVM), +1.60 mK (FDM) at 2 mm; +1.33/+1.39 mK for U1/U2 at 1 mm. The other 19 boards were not re-run one by one (the frozen set and the trap boards were). |
| 10 | Nothing else moves | Right | Frozen numbers `PCBT_FROZEN_CELLS=2,1,0.5`: 317 passed (twice, before and after the corrections); bit-identical non-surface numbers with `attach` off and a byte-identical saved project (tests pass). |
| 11 | Picture hash `c86e8a40 -> c29d267c` is only the title text | Right | Rendering the new code with the old suptitle and colour-bar text gives `c86e8a40` again. |
| 12 | Bottom face compared with the board maximum printed -23 K (fixed) | Fix verified | The report line now compares each face with the column of its own layer; `drawn_ell` bottom prints +0.000 K against layer 2. |
| 13 | Docs: guide, tooltips, models 4b, theory 1.2c, validation 55.6, README, CHANGELOG, versions, decisions-log | Mostly right; corrections below | |

## 2. Corrections made in this review

* **Negative zero** (cosmetic): the cooled bottom face and the patterned part rows printed `-0.000 K`. New `numfmt.signed_fixed` used by the report lines, the part lines, the map title and the part-table tooltip. Tests `tests/test_numfmt.py::test_signed_fixed_never_prints_a_negative_zero`, `tests/test_thickness.py::test_no_surface_text_prints_a_negative_zero`.
* **Stale warning text** (`checks.check_thick_plates`): still said the surface columns appear "when it differs by at least max(0.1 K, 1 % of the rise)" and "for an outer copper layer thicker than 105 um". Rewritten.
* **Graphs did not name their read-out** (the decision says maps AND graphs): the part bar chart (legend and title), the Profiles cut, the model comparison, the transient and power-profile curves and the animation maps (window and GIF) now say "column mean" (`plots.COLUMN_LABEL`). The three hashed pictures are untouched.
* **Exported surface picture**: the one-line title was cut at both sides at 6.4 x 4.8 in; now two lines. Both surface screenshots regenerated (`examples/make_screenshots.py --surface`) and looked at; the guide says "on its second line".
* **Theory 1.2c**: the inserted paragraph had split the formula from its own parenthesis; reordered. Removed the stale `thickness.significant` sentence. Added what the surface inherits from the column (below).
* **FEM wording**: the guide and `models.md` said the FEM "resolves / fills the same arrays"; `feature/fem-model` is in review, so "will" until it merges.
* **FEM hook contract** written in the `thickness.py` docstring (names, shapes, units, NaN rule, which readers use them).
* **`docs/versions.md`**: the entry named a tooltip that no longer exists (`SURFACE_MEAN_TIP`); 'Planned' item (1) moved to done, saying that the `readout` option and `--readout` were deliberately not made and what stays open.
* **Guide**: the film row said "exact for a column" (now: for a column whose film face carries no source); files: the PNG can be saved from the figure tool bar, the CSV has no GUI path; the trap numbers name their cell and their closed form.
* `docs/validation.md` 55.6: the independent checks of this review.

## 3. Limits found (recorded, not changed here)

* **The surface inherits the column's omissions** (theory 1.2b): the half copper between the node and the laminate is not in the vertical link: on 1 mm of 50 W/mK under 18 750 W/m^2 the column, and the surface with it, are 0.375 K too cool (2 x `q t/(2k)`, measured exactly). The thick-plate warning already bounds it.
* **The film of 1.2a under a source on the same face**: `h_eff = h/(1 + h t/(2k))` is exact for a face that carries no source; where a source and a film share a face the film is driven `h_eff q_src t/(2k)` too low (75 W/m^2 of 18 750, about 0.17 K too hot, 1 mm of 50 W/mK at 400 W/m^2K; scales as 1/k, confirmed at k = 5000: 0.0017 K). A fraction `h t/(2k)` of the source flux: 1e-3 on 2 mm of copper at 400 W/m^2K, 5e-7 on 35 um at 10 W/m^2K. A correction (add `h_eff q_src t/(2k)` to the film of a face under a source) would move numbers through a pending file; a question for the maintainer, not urgent.
* The zone and hotspot tables of the Components tab still head "Mean °C", "Max °C", "Tmax °C" without "(column)".

## 4. Not verified

* The whole battery (not asked). Run here: `test_thickness`, `test_thick_plate`, `test_results_views`, `test_docs`, `test_license_header`, `test_version`, `test_help`, `test_tooltips`, `test_shortcuts`, `test_numfmt` (995 passed), `test_published_cases` (10 passed, 1 skipped gate), `test_gui_stress.py -k 'surface or thin or readout'` (3 passed), `test_gui.py -k 'anim or profile or result or component'` (3), `test_gui_profile`, `test_profile_face`, `test_profiles`, `test_results_views` (33), frozen numbers 317 at 2, 1 and 0.5 mm.
* `test_random_user_actions` and the rest of `test_gui_stress.py`.
* The thin-copper range +0.4 to +3.2 mK on all 20 boards (only the example board and the two trap boards re-run).
* The size of the estimate against a 3D solver on a board with a metal block and imported copper masks (unchanged from the earlier review).

## 5. Open decisions for the maintainer

1. **Surface CSV from the application**: today only the picture (figure tool bar) and the command line (`--surface-files`). Least invasive: one File menu item "Export surface read-out (CSV)..." beside "Export report (TXT)...", calling `Simulation.save(surface_files=True)` into a chosen folder (a later item; no new control in the dialogs).
2. Name the zone and hotspot table headers "(column)" (text only).
3. The film under a source on the same face (section 3): correct it in a `fix/` branch with a pending file, or record it as a limit.
