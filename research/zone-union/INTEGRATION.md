# Integration: combining the zones of a layer in the program

Design for entering the program, from the measurements of the [README](README.md). Nothing here is implemented; the program was not edited. The change would be made on a `fix/zone-union` branch off `develop` (the prototype commit `1c9d154` and its merge exist there) with the whole battery, and the reviewer is called before the merge.

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
| The same, peak rise against the independent solver | FVM -22.4 %, FDM -29.3 %, Lumped -31.6 %, Analytic -34.3 %, 3D -8.5 % | FVM -24.0 %, FDM -33.7 %, Lumped -33.0 %, Analytic -35.4 %, 3D -9.7 % |
| Input check on 40 strips | false warning "copper fill 0.50" | none |
| Heat capacity and time constant (40 strips) | 1.0781 J/K, 134.76 s | 1.0906 J/K, 136.32 s (the one-zone values) |
| Time of the fill, 25 M sample points | 0.243 s (one zone), 1.65 s (2000 zones) | 0.235 s, 0.116 s |
| Peak memory of the fill, 25 M sample points | 1.07 GB (one zone), 0.04 GB (100 zones) | 1.46 GB, 0.63 GB |

**The honest reading of the real-board row.** The union is more copper and the program then gets cooler, which on that board is **farther** from the independent solver (by 0.1 to 1.6 points for the FVM). The old rule's loss of copper had been compensating the scalar fill's overstatement of the conduction of patterned copper (gerber-models 4.10, 4.11). Adopting the union is correct for the copper and makes the mapping error visible; it is not an accuracy gain on boards drawn as many polygons until the mapping is improved (gerber-models 5). The gain is exact copper, boards that give the same answer drawn as one zone or as pieces (10 to 28 % on strips), and no false warning.

**What changes** (files and lines of `develop` at the time of the study; the prototype's patch is `lib/zone_union_prototype.patch`):

| File | Lines | Change |
| :-- | :-- | :-- |
| `pcbthermal/geometry.py` | `coverage_fraction` (line 68) | split into `_sample_mask` (the bounding-box lattice of one polygon) and `coverage_fraction` (unchanged results); new `zone_fill` after it |
| `pcbthermal/fvm.py` | 74-78 | `f = zone_fill(problem.zones, L, nx, ny, dx, dy, samples=4)` |
| `pcbthermal/fdm.py` | 134-136 | the `"area"` sampling (the default): `zone_fill` on the cells, then `_node_average` per layer; the `"point"` sampling keeps the per-node maximum (a node is inside or outside: the maximum is exact) |
| `pcbthermal/solid3d.py` | 158-160 | `fill = zone_fill(...)` |
| `pcbthermal/analytic.py` | 132-135 and 215-217 | `fill_map = zone_fill(...)`, `fill_t = zone_fill(...)` on the tiles |
| `pcbthermal/checks.py` | 61-63 | `fill = zone_fill(...)` |
| `tests/test_zone_union.py` (new) | | the prototype's test file (zones that meet equal one zone, in four models; a hatched zone keeps its fill; zones that do not touch are unchanged) plus the invariants below |

**Not changed**: `coverage_fraction` of heaters, vias, heatsinks and blocks (each looks at one polygon); `analysis.zone_stats` and the zone check (`checks.py` line 112), which are per zone; the Lumped (it reads the fill from the FVM network); `inverse.py` (scales `z.fill`; the maximum commutes with the scaling); the file format (a saved project is the same; the **results** of a project with zones that meet or abut inside cells change); the user's input (no new field).

**Tests to add** (in `tests/test_zone_union.py` and `tests/test_docs.py` applies to the new functions): (1) abutting strips equal one zone in `zone_fill` for every layer; (2) overlapping zones of equal fill equal one zone; (3) disjoint cell-aligned zones equal the old loop (a copy of the old loop in the test); (4) a zone entirely outside, partly outside, a zero-area polygon; (5) zones on different layers are independent; (6) `check_problem` gives no "copper edge" warning on 40 strips under the part; (7) the heat capacity of the strips equals that of one zone; (8) the same invariants through `simulate` for the five models (the prototype's test has four). `lib/zone_rules.py` and `tests/test_zone_union_research.py` of this folder are the starting point.

**Documents to update** (when adopted): `docs/models.md` (the model of a zone: the fill of a point and of a cell), `docs/theory.md` (the layered idealisation: "copper fill of a cell is the mean over the cell of the largest fill at every point"; a figure from `figures/fig_01_cell_two_zones.png` and `fig_03_hatched_pour.png`), `docs/validation.md` (the tables of 4.2 and 4.3 of the README, the example boards unchanged), `docs/versions.md` (what, where, how tested), `CHANGELOG.md` (the zones of a layer are united per point: boards whose zones meet inside a cell get the copper that was lost), the user guide (`pcbthermal/help/index.html`, the zone row: "overlapping zones are united; for hatched zones the larger fill wins; two hatched zones do not add up" and `tests/test_help.py` with the new words), the tooltip of the zone fill (`gui/tips.py`), and the Decisions Log of `CLAUDE.md`. The text is in [`docs/for-the-project-documents.md`](docs/for-the-project-documents.md).

**Risks.**

* A saved project whose zones meet or abut inside cells is cooler after the change (0.5 to 1 % for a seam, up to 10 % on many abutting pieces); the example boards are not affected. A line in the CHANGELOG is enough; no migration.
* On a board drawn as many polygons the results move away from a better reference (above). It is the mapping's error being uncovered, not a new one.
* Memory: the lattice of the layer is held at once; at 25 million sample points (1.56 million cells) the peak grows by 0.4 to 0.6 GB for the fill of one layer; the FVM matrix of that board is far larger. If it matters, hold the lattice in float32 or by bands of rows (not measured here).
* The point-sampling path of the FDM keeps its own maximum: not reachable from the interface; left as it is.
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
4. Whether the union fix should wait for the mapping of gerber-models (so that boards drawn as polygons also get cooler-than-reference numbers corrected in the same release), or go first because it is independent of it. The reviewer's reading of README 8.2 is needed before this decision.
5. The FDM point-sampling path (left as is in the prototype).
6. Whether the user guide gets the pictures `fig_01` and `fig_03` (they are in `docs/for-the-project-documents.md` as candidates).
