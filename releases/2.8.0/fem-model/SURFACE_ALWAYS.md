# Always compute and always show the surface read-out? (design note)

Question of the maintainer: why does the surface value appear only on some boards (outer copper above 105 um, and only when it differs from the column mean by at least max(0.1 K, 1 % of the rise)), and not always, both numbers, for every steady FVM/FDM result? And in the pictures, which value is drawn and how is the other reached? Follow-up: "always computing is fine; why not always SHOW it too, and how do the graphs look with two values?"

Tree: `development` at `dfde802b` (the surface read-out merged). Nothing of the program was edited; the measurements below were made with a script outside the repository that sets `thickness.THICK_MIN_M = 0` at run time.

## 1. Facts from the code

| What | Where | Fact |
| :-- | :-- | :-- |
| What is solved | `fvm._result_from_theta` (`fvm.py` 916), `fdm.solve_steady` (`fdm.py` 498) | One temperature per copper layer, the column mean (`res.T`). `thickness.attach` is called AFTER the solve with the solved rise; it changes nothing that exists. |
| Gate 1: thickness | `thickness.py` 30, 173 | `THICK_MIN_M = 105e-6`: only an outer layer thicker than 105 um gets `arrays["T_surface"]`, `T_surface_mean`, `T_surface_flag` and the extras `t_max_surface_top/bottom`, `surface_excess_k`. Only the OUTER faces: top of layer 1, bottom of the last layer (both faces of the copper on a one-layer board). Inner copper, laminate nodes and metal blocks get none. |
| Gate 2: size | `thickness.significant` (`thickness.py` 202) | `surface_excess_k >= max(0.1 K, 1 % of res.t_max - ambient)`. Read by the report line (`api.surface_report_lines`, `api.py` 145), the part lines of the report (`api.py` 370, the same test per part), the Layer box entries (`results_view.surface_faces`, 370) and the part-table columns (`results_view.py` 705). |
| Not gated | `analysis.surface_stats` (146, 288), `checks.py` 1392 | The heater rows get `t_max_surface`, `t_mean_surface`, `surface_upper` whenever the arrays exist; the thick-plate warning quotes them. |
| Nothing decides on it | `tests/test_thickness.py::test_nothing_that_decides_a_number_reads_the_surface` | Tj, margin, power limit, top path, power coefficient, Power Calculator, calibration stay on the column, bit-identical with and without the arrays. |
| Pictures | `plots.draw_field`, `draw_fields`, `draw_surface` (673); `results_view.py` 456-476; `api.Simulation.save` 417-452 | Every map, the all-layers view, the gradient, the saved `fields_<model>.png`, `comparison.png`, `profiles.png`, the Animation and Power-profile pages draw the COLUMN (`res.T` or the transient fields). The surface is drawn only by the Layer-box entries `Surface (top)` / `Surface (bottom)` of the Temperature tab (data 200/201), title `FVM - surface (top), estimate   max ... (layer mean ...)`, colour bar `Surface temperature, estimate (°C)`. No saved figure, no CSV and no CLI line holds the surface except the report line. |
| Naming of the column maps | `results_view.py` 470-476, `plots.py` 644, 751 | The column maps are titled `FVM - layer 1   max ... min ...` with the colour bar `Temperature (°C)`: they do NOT say 'layer mean (column)'. On a board that has a surface this leaves the default map unnamed against the other read-out (rule of CLAUDE.md 11: every number names its read-out). |
| Exports | `api.Simulation.save` 424 | `field_<model>.csv` writes `layer, x_mm, y_mm, T_c` of the column only; `summary.json` gets the extras through the results' summaries. |
| Frozen numbers | `regress_classify.metrics_of` | Records hold `t_max`, `t_mean`, `t_min`, balances, layer means and the part keys `t_max`, `t_mean`, `t_junction`, `power_w`, `power_top_w`; extras and surface keys are NOT compared. Adding the arrays to every board moves no frozen number. |
| Stale text | `thickness.py` 5 and the `@brief` of `attach` | Say 'or metal block' / 'and of the blocks'; the code computes no block surface (the NOT-modelled line of the same docstring says so). A wording defect, no number. |

### 1.1 Measured: the surface forced on every board of the harness (FVM and FDM, 1 mm)

Script outside the repository, 20 boards of `tests/regression/regress_boards.py`, `THICK_MIN_M = 0`:

* **Copper term on 35 um copper**: 0.4 to 5.6 mK over the whole board, 0.4 to 3.3 mK under a part (the research study gave 0.57 to 3.79 mK for the bound, `research/through-thickness-readout` 4.3). At one decimal the surface and the column print the SAME number on every board.
* **Cost**: `thickness.attach` took 0.0 to 3 ms per run against 0.02 to 3.6 s for the whole simulation. Memory: three arrays (2, ny, nx), about the size of the column field of a four-layer board; small next to the factorised matrix (the memory guard does not count them; to be checked if they become permanent).
* **The laminate face term**: on two patterned boards (`hatched_copper`, `drawn_ell`) the forced `surface_excess_k` was 1.22 K and 3.65 K, and `significant()` would be TRUE, although the copper term there is 0.1 and 2 mK. The difference is the laminate face term (`face_peak`, the rise across the bare laminate under a source over absent copper), which the part rows ALREADY include in their 'column' max (`analysis._footprint_stats`, `face=True`): the part's surface minus 'column' is 0.000 K on both. So the board-level gate compares the surface (with the face term) against `res.t_max` (the node maximum, without it), two different things. Consequence for any 'always' design: the 'column' of a part is the node plus the laminate face term, not a pure layer mean; its label must say so, and no gate may be built on `surface_excess_k` as it stands.
* (Observed, not investigated, outside this question: `drawn_ell` reads a rise of 99.0 K in the FVM and 67.0 K in the FDM at 1 mm.)

## 2. Why the thresholds exist

1. **105 um: not cost.** It was chosen so that the ordinary 35 to 105 um boards keep their results, their report, their tables and their Layer box exactly as before (`thickness.py` 30: 'the 35 to 105 um boards are unchanged'; `research/through-thickness-readout/INTEGRATION.md` 5.4 proposed 0.2 mm). The cost is milliseconds (1.1).
2. **max(0.1 K, 1 %): not validity, display.** Below 1 % of the rise the difference is smaller than the discretisation error of the node itself (1.5 % low at 0.25 mm on the copper core, `research/readout-conventions` 2.1, from `research/through-thickness-readout` 4.4) and than the parabola's own error on Muzychka case 2 (0.8 to 1.6 % of the rise); 140 um copper on FR-4 passes the 105 um gate and would print columns that differ by milli-kelvin.
3. **Is the estimate meaningless on thin copper?** No: it is **correct and tiny**. The parabola `T_face - T_m = t (2 q_top - q_bot) / (6 k)` assumes a slow in-plane variation against the thickness; 35 um under a millimetre source is its best case (t/a near 0.01; the 3D check gave 1.76 mK against the bound 2.53 mK, `research/through-thickness-readout` 4.3). It is merely smaller than what the program can resolve elsewhere, and smaller than the 0.1 K the tables print.
4. **Any layer?** Only the outer faces of the outer copper mean something to measure; the formula uses `k_copper` and is the copper slab's term. Inner copper faces are interfaces with the laminate (continuous temperature, not reachable by a thermocouple). The laminate is already resolved through its thickness by the sub-gap nodes (`laminate.py`), and the bare laminate face under a source is already the face term. So 'every layer' means: every outer face of every steady FVM/FDM board; an inner layer shows the column only.

## 3. Options

| | (a) As now | (b) Always compute, always show both, Layer-box views | (b-switch) As (b) plus a Display switch 'Column mean / Surface' | (c) Always compute, show on demand |
| :-- | :-- | :-- | :-- | :-- |
| Arrays | thick outer copper only | every steady FVM/FDM result | same | same |
| Tables and report | both only above the gate | both always; the difference stated in K and % | same | column; surface in the report line and exports only |
| Pictures | column; Surface entries only above the gate | column by default; Surface entries always in the Layer box | as (b) plus a switch on the outer-layer maps | as (b) |
| Hidden thresholds | two | none (only the stated print resolution) | none | none |
| Effort, risk | 0 | M, low (display only) | M+, low-medium (a second way to the same view; meaningless on inner layers and on the all-layers view) | S-M, low |
| Frozen numbers | - | none move | none | none |

**Is a pure display switch safe?** Yes, if it only chooses which array `plots` draws and never reaches `analysis.heater_stats`, `heater_rows`, `api._top_path_split`, `api._solve_with_tc`, the calculator or calibration (the earlier objection was to a MODE that switched Tj inside the solve; this is not that). It must never change: Tj, margin, power limit, top-path split, power coefficient loop, Power Calculator, calibration, the profile decision (average or resolve), the model comparison table, `res.t_max`/`t_mean`, the frozen records. A test holds it: every number of the run bit-identical for both positions. It is still redundant with the Layer box, which already gives the surface map in one click, and it would have to be greyed out on inner layers, on 'All layers' and in time pages; hence (b) without it.

### 3.1 By model: what 'column mean' and 'surface' mean, what is given, what could be

| Model | Field through the copper thickness | 'Column mean' in it | 'Surface' in it | Given today (steady) | Possible with always-both | Effort, risk |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| **FVM** steady | no: one node per copper layer and cell (laminate resolved by sub-gap nodes) | the node itself | node + parabola from the solved face fluxes (`thickness.attach`, from the matrix couplings) | arrays above 105 um; shown above max(0.1 K, 1 %) | every board, both outer faces; within 7 % of an independent 3D up to t/a 0.5, upper beyond (validation 55.6) | S (gate removal) within (b) |
| **FDM** steady | no: one node per copper layer | the node | the same parabola (`fdm.py` 498) | as the FVM | as the FVM | S within (b) |
| **FVM, FDM** transient and power profiles | no | the node at each step | none; the parabola is quasi-static, valid when the step is long against `t^2 / alpha` through the copper (35 um: about 10 ns; 10 mm copper: about 0.1 s; `research/through-thickness-readout` 7.4) | column only | an offset per step from the step's fluxes, as the laminate face term is applied; not studied, not validated against a 3D transient | M-L, medium; recommended: keep the column with a note |
| **Lumped** (rings per heater) | no; no per-cell flux | the ring or zone node | only a bracket from the part's flux, `q t / 3k` (heat spreading sideways) to `q t / 2k` (heat crossing the plate) | none | a bracket or the upper bound, labelled 'bound', not an estimate; its own column error on case 2 is of the size of the term (`readout-conventions/INTEGRATION.md` 7) | S to show a bound, low; a real estimate: no |
| **Analytic** (multilayer series) | no: one temperature per layer in the series | the layer value of the series | could be built from the series' own interface fluxes (the source flux on the face and the modal flux to the next layer) with the same parabola; first planned, then left out (`SURFACE_NOTES.md`) | none | possible, not derived for the local via/heatsink corrections; would need its own check against the independent 3D | M, medium |
| **3D solid** | yes in the laminate and in metal blocks (slabs of about 1 mm), **no in copper**: one cell per copper slab | the copper cell | none for copper (the cell IS the column); a block face is resolved | none | either the same parabola from its fluxes (S), or the copper slabs of `research/through-thickness-readout` option C (`n_cu` slabs above 105 um; case 2 within 0.09 K at 8 slabs) | S (parabola) or S-M (slabs, unknown count and memory law change), low |
| **FEM** (not selectable yet) | yes: 1 element through copper up to 105 um, `ceil(t / 70 um)` up to 8 above (DESIGN 3.2) | volume mean over the cell and the copper slab (DESIGN 5.4) | the face integral of the field: computed, not estimated (exact to the mesh) | not yet | always both, natively; the reference for the estimate of the others | in the FEM branch already; no extra |
| **FEM** transient | as steady | as steady | the face value of each step | not yet | both at each step (the only model where a transient surface is computed) | in its branch, to be checked |

The always-both design is therefore 'both numbers wherever the model has them': FVM and FDM steady (estimate), FEM (computed); the Lumped, the Analytic and the 3D solid show `n/a (this model has no surface)` until one of the rows above is done; every transient page stays on the column with a note.

### 3.2 Decisions taken so far, their reason, and what always-both changes

| Decision | Reason (one line) | Always-both |
| :-- | :-- | :-- |
| The surface is a VIEW and a second number, never a mode (no option, project key or CLI switch) | Tj and the top path are read inside the solve, so a read-out switch would let a display choice move the field | kept |
| The column is the number of every table and of every model comparison | it is the solved quantity, common to all models, like for like; the frozen numbers rest on it | kept |
| Tj, margin, power limit, top path, power_tc, Power Calculator, calibration stay on the column | they run in the solve loop and the datasheet theta/psi already include the plate; the surface would double-count it | kept |
| Gate 1: arrays only above 105 um of outer copper | ordinary boards keep their results and screens exactly as before | **removed** (cost is milliseconds; the frozen numbers do not see the arrays) |
| Gate 2: shown only above max(0.1 K, 1 % of the rise) | below it the difference is smaller than the node's own discretisation error | **removed**; replaced by printing the difference honestly (K and %) |
| Only the FVM and the FDM give it | the Lumped, the Analytic and the 3D solid have no per-cell face flux or no through-thickness copper | kept for now; 'n/a (this model has no surface)' shown instead of hiding the column; the FEM adds it natively |
| Steady state only; Animation and Power profile pages show the column | the parabola is quasi-static and was validated only in steady state | kept, with a note on those pages |
| Surface entries live in the Layer box, not in the Display popover | a surface map is another quantity of one face, like a metal block face, not a property of every picture | kept; the entries become permanent |
| The word 'estimate' everywhere the surface is shown, 'upper side' above t/a 0.5 | it is a formula on the column, not a solved field | kept; plus 'column mean' on every column map (new) |

## 4. Recommendation: (b), with the Layer box as the one-click switch

Always compute the arrays for every steady FVM/FDM result (drop `THICK_MIN_M`); always show both numbers wherever a part or a face temperature is printed, each with its name; draw the column by default; reach the surface through the Layer box entries, always listed. No project key, no CLI option, no Display switch. Thin copper is shown honestly: the same number at the table's resolution and the difference written in the report ('+0.003 K, 0.005 % of the rise'), which tells the user that a thermocouple and the program agree there. The 105 um limit can go; `significant()` is removed (or kept only to choose the wording 'equal at 0.1 K'), so no line or entry appears and disappears with the board.

**Why the plots show the column by default**: it is the solved quantity, it exists on every layer and in every model (Lumped, Analytic, 3D solid, transient, profiles), so the default map compares like with like across models and with the decision numbers; the surface is an estimate of one face, and an upper one for t/a above 0.5.

**Why Tj, margin, power limit, top path, power_tc and the Power Calculator stay on the column**: they run inside the solve loop and rest on a datasheet theta/psi measured on a board whose plate is already in the number, so moving them to the surface would double-count the plate and let a view change the field.

### 4.1 What each place shows (text mock-ups)

Names used everywhere: **column** = the layer mean through the copper (for a part, the node plus the laminate face term under a source over absent copper); **surface** = the estimate of the outer face of the copper.

* **Layer box (Temperature tab)**: `Layer 1 (top) · column mean`, `Layer 2 · column mean`, ..., `All layers · column mean`, `All layers (grid) · column mean`, then always `Surface (top) · estimate`, `Surface (bottom) · estimate` (for a one-layer board `Surface (bottom, on the laminate) · estimate`), `Metal block (top)` when present. Gradient tab: the column layers only (a gradient of an estimate is not offered).
* **Column map**: title `FVM - layer 1, column mean   max 101.2 °C   min 45.3 °C`; colour bar `Temperature, column mean (°C)`. All-layers view: suptitle `FVM - column mean, all layers`, colour bar the same.
* **Surface map**: title `FVM - surface (top), estimate   max 103.6 °C   (column max 101.2 °C, +2.4 K)`; colour bar `Surface temperature, estimate (°C)`; `estimate, upper side` when flagged. On thin copper: `FVM - surface (top), estimate   max 101.2 °C   (column max 101.2 °C, +0.003 K)`. The hotspot contour and the extreme rings of a surface map are drawn on the surface field and say so in the legend (`hotspot of the surface, 100 °C`).
* **Results, Components table**: always `Mean °C (column) | Max °C (column) | Junction °C | Margin K | Power limit W | Top path W | Max °C (surface, estimate)`, header tooltips naming each read-out; the surface mean goes to the report and the CSV only (one extra column, not two). Inner-layer parts: `n/a (inner layer)`; Lumped/Analytic/3D solid reference: `n/a (model has no surface)`.
* **Zone table**: column only (a zone has no source; its face differs by the copper term only); noted in the header tooltip.
* **Hotspot table**: column (`Tmax °C (column)`); the hottest surface is the report line below.
* **Summary card / Results summary and report.txt**: always the line `Read-outs: column (layer mean, used for Tj, margins and comparisons); surface (outer face of the copper, an estimate)` and `Hottest surface (top): 101.2 °C (estimate; column max 101.2 °C; +0.003 K, 0.005 % of the rise)`; part lines always `column mean 80.1, column max 101.2 °C, ...; surface mean 80.1, surface max 101.2 °C (estimate)`.
* **CLI `run`**: the comparison table stays the column (all models); one line after it, `FVM surface (estimate): top 101.2 °C, bottom 61.0 °C; column max 101.2 °C`.
* **Exports**: `field_<model>.csv` gains no columns (the layers stay the column); a new `surface_<model>.csv` (`face, x_mm, y_mm, T_surface_c, T_surface_mean_c, upper`); `summary.json` keeps the extras; a saved `surface_<model>.png` beside `fields_<model>.png` (titled as the surface map).
* **Profiles and Animation**: unchanged, column; the page subtitle says `column mean (the surface read-out is a steady-state estimate; see the Temperature tab)`.

## 5. What would change (option b)

* **Code** (`fix/` branch, files shared with the FEM branch, so after it): `thickness.py` (drop the gate; the docstring's block wording; `significant` removed or reduced to wording), `api.py` (report lines always, part lines always, CLI line, `save` writes the surface CSV and PNG), `analysis.py` unchanged, `plots.py` (column labels on `draw_field`/`draw_fields`, the difference in the `draw_surface` title), `gui/results_view.py` (Layer entries always, the table columns always, column titles), `gui/layerchoice.py` (entry names), `gui/tips.py`. The memory guard: add the three arrays if the review finds them significant.
* **Documents**: the guide section written on `docs/surface-readout-help` (13298f7c) goes from 'shown only when' to 'always shown' (where it appears, the mock-ups of 4.1, the thin-copper example); `docs/theory.md` 1.2 (the column of a part includes the laminate face term), `docs/models.md` 4b.1, `docs/validation.md` 55.6 (the thin-copper row of 1.1 with the harness boards), README, CHANGELOG, `docs/versions.md`, `docs/decisions-log.md`, `thickness.py` and `results_view` docstrings.
* **Tests**: invert `test_thin_copper_has_no_surface_and_the_results_are_unchanged` (thin copper HAS the surface; every non-surface key bit-identical), `test_the_layer_box_lists_the_surface_only_with_it_and_only_in_temperature`, `test_the_report_names_both_read_outs_only_when_they_exist`; add: surface minus column below `q t / 2k` on the harness boards, the CSV/PNG outputs, the column labels of every map, the GUI stress scenario, `tests/test_help.py` words, `tests/test_tooltips.py`. `test_nothing_that_decides_a_number_reads_the_surface` stays the guard.
* **Frozen numbers**: none move (arrays and extras are added; `metrics_of` reads neither); confirm with `PCBT_FROZEN_CELLS=2,1,0.5` on the branch; no pending file.
* **Project format and CLI options**: none.
* **Effort**: M (about two days with the documents and the battery). **Risk**: low; the one trap is the laminate face term of 1.1 (a surface map 1 to 4 K above the column map on patterned thin copper while the part rows agree), which the labels must explain and no gate may use.

## 6. Open decisions for the maintainer

1. Adopt (b) (recommended), the switch variant, (c) or keep (a). Impact: no number of any model; a visible change on every board.
2. One surface column in the Components table (max) or two (mean and max). Recommended: one.
3. Whether the saved outputs gain `surface_<model>.csv` and `.png` on every run, or only the report line.
