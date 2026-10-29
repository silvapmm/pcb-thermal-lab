# Integration: combining the zones of a layer in the program

Design for entering the program, from the measurements of the [README](README.md). Nothing here is implemented; the program was not edited. The change would be made on a `fix/zone-union` branch off `develop` (the prototype commit `1c9d154` and its merge exist there) with the whole battery, and the reviewer is called before the merge. The whole battery on that branch, merged with `develop` of that time, gave **681 passed** (run by the maintainer). `develop` has moved since (the top-path fix, `434a6c0`): the branch must take `develop` again before the merge; the six loops are at the same lines in `develop` now (checked by the review).

## 1. Proposal 1: the maximum fill at every sample point (the prototype)

**What it is.** One function, `geometry.zone_fill(zones, layers, nx, ny, dx, dy, samples=4)`, returns the copper fill of every layer as the mean over the cell of the largest fill at every sub-sample point; `coverage_fraction` is rewritten on a shared helper `_sample_mask` (same numbers, bit for bit). It replaces the loop `fill = max(fill, coverage * z.fill)` that is written six times.

**Measured impact** (README 4 and 8; the old column is the unmodified program):

| Situation | Old rule | Per-point union |
| :-- | :-- | :-- |
| Example boards (`example_board`, `profile_board`, `reference_board`, 1 and 0.5 mm cells, five models) | | change of 0.0000 K |
| One zone; zones that overlap with fills of 1; zones that do not share a cell; the cases that are exact today | exact | the same, bit for bit (test of the folder) |
| Two solid zones meeting along one seam (a line, a T, a corner of four), 1 mm cells | +0.4 to +1.1 % (FVM), +0.8 to +2.3 % (FDM), up to +1.6 % (Lumped) | the one-zone value in every model (-0.09 % FVM, the model's own error) |
| 40 abutting strips of 0.5 mm over 1 mm cells | +9.95 % FVM, +28.0 % FDM, +11.8 % Lumped, +9.1 % Analytic, +10.0 % 3D | the one-zone value (-0.08 %) |
| The same on two layers | +8.65 % FVM, +23.6 % FDM | the one-zone value (-0.13 %) |
| Strips of 0.25 mm over 1 mm cells | +28 % FVM, +58 % FDM | 0.00 % |
| Overlapping zones of fill 0.5 (must equal one zone of 0.5) | exact | exact (additive rule: -8.2 %; `prob` -5.3 %; the union is the only rule exact on both this and the strips) |
| A real board drawn as 440 polygons (densest 24 mm window of the Stormduino), 1 mm cells | copper fraction 0.531 (resolved 0.596) | 0.591 |
| The same, peak rise against the independent solver (a reference that is itself 5 to 14 % low, README 8.3) | FVM -22.4 %, FDM -29.3 %, Lumped -31.6 %, Analytic -34.3 %, 3D -8.5 % | FVM -24.0 %, FDM -33.7 %, Lumped -33.0 %, Analytic -35.4 %, 3D -9.7 % |
| Input check on 40 strips | false warning "copper fill 0.50" | none |
| Heat capacity and time constant (40 strips) | 1.0781 J/K, 134.76 s | 1.0906 J/K, 136.32 s (the one-zone values) |
| Time of the fill, 25 M sample points | 0.243 s (one zone), 1.65 s (2000 zones) | 0.235 s, 0.116 s |
| Peak memory of the fill, 25 M sample points | 1.07 GB (one zone), 0.04 GB (100 zones) | 1.46 GB, 0.63 GB |

**The honest reading of the real-board row.** The union is more copper and the program then gets cooler, which on that board is **farther** from the independent solver (by 0.1 to 1.6 points for the FVM). The old rule's loss of copper had been compensating the scalar fill's overstatement of the conduction of patterned copper (gerber-models 4.10, 4.11). Adopting the union is correct for the copper and makes the mapping error visible; it is not an accuracy gain on boards drawn as many polygons until the mapping is improved (gerber-models 5). The review split the error of that row (README 8.3): the scalar fill at the cell size accounts for 5 to 19 % of the peak, and the union adds 0.2 to 1.7 points to it; the larger errors of the FVM, FDM, Lumped and Analytic (12 to 14 points more than the 3D solid) come from a part sitting on bare laminate, which the one-node-per-layer models do not resolve, and have nothing to do with the zone rule. The gain is exact copper, boards that give the same answer drawn as one zone or as pieces (10 to 28 % on strips), and no false warning.

**What changes** (files and lines of `develop` at the time of the study; the prototype's patch is `lib/zone_union_prototype.patch`):

| File | Lines | Change |
| :-- | :-- | :-- |
| `pcbthermal/geometry.py` | `coverage_fraction` (line 68) | split into `_sample_mask` (the bounding-box lattice of one polygon) and `coverage_fraction` (unchanged results); new `zone_fill` after it |
| `pcbthermal/fvm.py` | 74-78 | `f = zone_fill(problem.zones, L, nx, ny, dx, dy, samples=4)` |
| `pcbthermal/fdm.py` | 134-136 | the `"area"` sampling (the default): `zone_fill` on the cells, then `_node_average` per layer (today each zone is averaged to the nodes before the maximum, which loses more than the FVM: 0.25 instead of 0.5 on the strips, README 4.1); the `"point"` sampling keeps the per-node maximum (a node is inside or outside: the maximum is exact) |
| `pcbthermal/solid3d.py` | 158-160 | `fill = zone_fill(...)` |
| `pcbthermal/analytic.py` | 132-135 and 215-217 | `fill_map = zone_fill(...)`, `fill_t = zone_fill(...)` on the tiles |
| `pcbthermal/checks.py` | 61-63 | `fill = zone_fill(...)` |
| `tests/test_zone_union.py` (new) | | the prototype's test file (zones that meet equal one zone, in four models; a hatched zone keeps its fill; zones that do not touch are unchanged) plus the invariants below |

**Not changed**: `coverage_fraction` of heaters, vias, heatsinks and blocks (each looks at one polygon); `analysis.zone_stats` and the zone check (`checks.py` line 112), which are per zone; the Lumped (it reads the fill from the FVM network); `inverse.py` (scales `z.fill`, and the maximum commutes with the scaling and the clip at 1; the board-sized "undrawn plane" of `_design_planes` is added only to an inner layer that has no zone, so no rule meets it); the file format (a saved project is the same; the **results** of a project with zones that meet or abut inside cells change); the user's input (no new field).

**Tests to add** (in `tests/test_zone_union.py` and `tests/test_docs.py` applies to the new functions): (1) abutting strips equal one zone in `zone_fill` for every layer; (2) overlapping zones of equal fill equal one zone; (3) disjoint cell-aligned zones equal the old loop (a copy of the old loop in the test); (4) a zone entirely outside, partly outside, a zero-area polygon; (5) zones on different layers are independent; (6) `check_problem` gives no "copper edge" warning on 40 strips under the part; (7) the heat capacity of the strips equals that of one zone; (8) the same invariants through `simulate` for the five models (the prototype's test has four); (9) a board of one zone per layer gives bit-identical results in the five models before and after (the FDM changes the order of the average and the maximum, so this is the test that one zone is untouched there); (10) the FDM `"point"` sampling of abutting zones equals one zone. `lib/zone_rules.py` and `tests/test_zone_union_research.py` of this folder are the starting point.

**Documents to update** (when adopted): `docs/models.md` (the model of a zone: the fill of a point and of a cell), `docs/theory.md` (the layered idealisation: "copper fill of a cell is the mean over the cell of the largest fill at every point"; a figure from `figures/fig_01_cell_two_zones.png` and `fig_03_hatched_pour.png`), `docs/validation.md` (the tables of 4.2 and 4.3 of the README, the example boards unchanged), `docs/versions.md` (what, where, how tested), `CHANGELOG.md` (the zones of a layer are united per point: boards whose zones meet inside a cell get the copper that was lost), the user guide (`pcbthermal/help/index.html`, the zone row: "overlapping zones are united; for hatched zones the larger fill wins; two hatched zones do not add up" and `tests/test_help.py` with the new words), the tooltip of the zone fill (`gui/tips.py`), and the Decisions Log of `CLAUDE.md`. The text is in [`docs/for-the-project-documents.md`](docs/for-the-project-documents.md).

**Risks.**

* A saved project whose zones meet or abut inside cells is cooler after the change (0.5 to 1 % for a seam, up to 10 % on many abutting pieces); the example boards are not affected. A line in the CHANGELOG is enough; no migration.
* On a board drawn as many polygons the results move away from a better reference (above). It is the mapping's error being uncovered, not a new one.
* Memory: the lattice of the layer is held at once; at 25 million sample points (1.56 million cells) the peak grows by 0.4 to 0.6 GB for the fill of one layer; the FVM matrix of that board is far larger. If it matters, hold the lattice in float32 or by bands of rows (not measured here).
* The point-sampling path of the FDM keeps its own maximum: not reachable from the interface, and exact there; left as it is.
* Hatched overlaps: no rule is right for every pattern (README 4.6, 3); the maximum is the choice that is exact for nested patterns and gives the least copper. The documents must say so.

## 2. Proposals that the investigation suggests, with their impact

2. **A check for self-intersecting zones** (`checks.py`): the program fills them by the even-odd rule (a pentagram leaves its centre empty: 61.9 cells against 90.0 under non-zero winding); Gerber forbids them and the CAD tools do not make them. A warning "zone N crosses itself: the central area is left empty" costs one pass of segment intersections per zone. Impact: none on valid boards; not measured on any board. Open decision.
3. **A warning for overlapping hatched zones** (`checks.py`): two zones of the same layer with a fill below 1 that overlap: "the larger fill is used where they overlap; two hatched zones do not add up". Impact: documentation of 4.6; costs the overlap test of the filled windows.
4. **The pattern attribute** (`pattern`, gerber-models 5): the only complete answer for hatched pours (README 4.6: the combination of two hatched zones cannot be written as a scalar rule). Not part of this change; already on `docs/roadmap.md` as after the investigation `gerber-models`.
5. **Exact polygon union by a library** (shapely): measured, 2 to 61 times slower than the lattice, a new dependency, and the lattice error (0.0036 mean fill, -0.03 % of the copper area for 4 x 4) is far below the mapping error: **not recommended** (README 6).

## 3. Recommendation and open decisions

Adopt proposal 1 on a `fix/zone-union` branch: it is a correction (copper that the user drew is lost today), it moves no example board, it makes the one-zone and the many-pieces drawing of the same copper give the same answer in the five models (10 to 28 % on strips), and removes a false warning. It is cheap in time and acceptable in memory. Say in the documents that a fill below 1 is a density, that overlapping hatched zones take the larger fill, and that the accuracy on patterned copper is limited by the mapping (the scalar fill is optimistic).

Open decisions for the maintainer:

1. Adopt the per-point maximum as the rule (recommended) or keep a per-cell rule and document the loss.
2. Whether to reduce the memory of the lattice now (float32 or bands) or only if a user meets it.
3. Whether to add the two warnings of proposals 2 and 3.
4. Whether the union fix should wait for the mapping of gerber-models (so that boards drawn as polygons also get cooler-than-reference numbers corrected in the same release), or go first because it is independent of it. The reviewer's reading of README 8.2 is in README 8.3 and section 4 below.
5. The FDM point-sampling path (left as is in the prototype).
6. Whether the user guide gets the pictures `fig_01` and `fig_03` (they are in `docs/for-the-project-documents.md` as candidates).

## 4. The reviewer's opinion on the open decisions

These are opinions with the measured impact; the decisions are the maintainer's.

1. **Adopt the per-point maximum.** It is the exact union for solid copper (Gerber, KiCad, Altium agree), it removes errors of 0.5 to 1 % on a seam and 10 to 28 % on abutting pieces, it moves no example board (0.0000 K) and passed the whole battery (681). Keeping a per-cell rule would keep a defect whose size depends on where the user's polygons cut the grid.
2. **Memory: not now.** The extra 0.4 to 0.6 GB appears only at 25 million sample points (1.56 million cells), where the FVM matrix already needs several GB; holding the lattice in `float32` is a one-line change that halves it at a relative cost below 1e-7 in the fill and could be taken in the same branch if the maintainer wants it, but bands of rows are not worth their code until a user meets the limit.
3. **The self-intersection check: yes; the hatched-overlap warning: no, a sentence in the user guide instead.** A self-intersecting zone is filled wrongly in silence (a pentagram loses a third of its area) and an import will meet them; the check is cheap. Overlapping hatched zones are legitimate drawings whose CAD meaning depends on priority (README 2), so a warning would fire on boards that are fine; the guide sentence of `docs/for-the-project-documents.md` is enough.
4. **The union goes first.** It corrects the input (the copper area), which is right whatever mapping comes later; the mapping (gerber-models 5) is a larger project. The "farther from the reference" effect is 0.2 to 1.7 points of the peak on a board drawn as hundreds of polygons, a kind of board the program cannot import today, against 10 to 28 % on abutting pieces that a user can draw now.
5. **The FDM point sampling: leave it.** The per-node maximum is exact for point sampling; add test (10) above so that it stays so.
6. **Figures in the user guide: `fig_01` only.** It shows the rule a user needs (a cell, two zones, what the program counts). `fig_03` (three hatched combinations) explains a limit and belongs in `docs/theory.md` with the text of `docs/for-the-project-documents.md`; both are first copied to `research/theory/` and `docs/images/` as the rules ask.
