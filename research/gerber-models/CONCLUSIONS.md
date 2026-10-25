# Conclusions, phase 2: the copper in the simulation models

Written on branch `research/gerbers` (phase 2 of three of the Gerber research, split from one study: `research/gerber-import`, `research/gerber-models`, `research/gerber-nets`; the section numbers 4.1 to 4.50 are those of the original study; the sections of this folder are listed in `README.md`, the map of all of them in `research/README.md`). Everything quoted here has a section of `README.md` (numbers, tables, limits), a script (`scripts/`) and, where it is a claim that can break, a test (`tests/`, 34 tests in about 30 s; `cd research/gerber-models && ../../.venv/bin/python -m pytest -q tests`; they need the program's dependencies). Nothing in `pcbthermal/` was changed.

**Scope**: this file concludes on the copper in the simulation models (the mappings, the five models, the import into the program's FVM, the corrections to the program). The reading of the files is concluded in [`../gerber-import/CONCLUSIONS.md`](../gerber-import/CONCLUSIONS.md), the nets with a current in [`../gerber-nets/CONCLUSIONS.md`](../gerber-nets/CONCLUSIONS.md).

**After the independent review** (README, section Review): the numbers that run the program were re-run on `develop` at `a6f822b` and replaced below; the 42-window studies use a one-sheet reference that an independent 3D solver shows to be 22 % cool on real one-layer copper, so their percentages are the mapping error inside that idealisation (about half of what the program shows); the program's own pixel run is 10 % cool against the same 3D solution (two laminate nodes bridge the clearances).

## 1. Where we stand

1. **The fill fraction the program uses is biased cool on real copper**, because clearances cut paths that the average assumes connected: against an independent 3D solution of seven real one-layer windows 24 to 26 % on average (17 to 38 %), against the program's own pixel run 16 to 18 % (README Review R2); in the one-sheet studies 10 to 23 % depending on the regime, up to 49 % across stripes (README 4.4, 4.7, 4.11 to 4.13, 4.25).
2. **A good mapping exists and is cheap**: the flow-based face conductances (a local conduction problem between two cell centres) are within 0.3 to 3.6 % of the resolved mask in every one-sheet case tested and 1.1 to 1.5 % (mean) of the program's own pixel run on seven real windows (up to +7.3 % on our sparse IC board), 5.5 s per 100 x 160 mm layer once at import. **This is Sampson's method (2005, article 2017), not ours.** Lambda 0.5 (the geometric mean of the two Wiener bounds per direction) is almost as good at no cost (1.0 to 3.2 %), and is the quick mode (section 3 below, README 4.4).
3. **Zone fill must keep its formula**; imported copper gets its own element (README 4.10, `INTEGRATION.md`).
4. **Resolution matters more than the reader**: at most half the thinnest track per pixel for area and connectivity (README 4.3, 4.42); another reader changes the heater temperature by 0.01 to 0.04 % (4.31). That binary masks lose or invent area on thin copper and that a lattice-aligned track as wide as the pixel can vanish is shown in `gerber-import` 4.22; the pixels needed for the resistance of a thin track (8 to 10 across) in `gerber-nets` 4.23.
5. **A coverage (grey-level) mask is a better default than a binary one**: at the same 0.1 mm grid it cuts the error of the flow-based faces from 6.5 to 4.1 % on 21 real 20 mm windows and by a factor 3 to 4 on thin-track layouts; part of the gain compensates a small bias of the mapping (README 4.26).
6. **The program's zones cannot carry fine copper as they are** (README 4.27, 4.39): a zone is one polygon without holes, and zones are combined per cell with a maximum, so copper tiled in many polygons loses copper in each shared cell (+7 % FVM to +17 % FDM; test). The import needs its own path; and the combination can be corrected independently: **by the maximum per sample point, not by an additive rule** (the additive rule double counts overlapping zones, -7.8 %, and failed four program tests); the example boards do not move.
7. **The program can take the faces without a change of algorithm** (4.14, 4.31): `fvm.Network` with the face conductances of the copper layers replaced, the laminate nodes, vertical couplings, vias and losses untouched, reproduces its own formula to 1e-6 K (the subclass had to be corrected for the laminate nodes by the review, README Review R1). On the Stormduino the heater temperature error goes from -15.1 % to -2.1 % (binary) / -5.3 % (coverage); on our board from -4.8 % to +7.3 % / +5.2 % against the program's pixel run, and from -12.2 % to -1.2 % against an independent 3D solution.
8. **The five models are not the same physics** (4.34, 4.35, 4.37): on rectangles the FVM and FDM converge to the same value, the Lumped is 16 % and the Analytic 26 % below, the 3D solid (two layers) 7 to 9 % above; the grid matters for drawn rectangles too (6 % on the FVM at 1 mm when the copper is between cells). The 3D solid had no laminate under a single copper layer (346 against 174 K): the earlier "unusable" was this; the program has built that laminate since.
9. **Mappings as an option** (4.38, 4.43): on eleven boards the flow-based faces, the Wiener upper bound, lambda 0.5 and the cell problem (mean error 2.3, 2.3, 2.4, 2.4 %) beat the fill fraction (7.4 %) and are equivalent; design `SolverOptions.copper_mapping` with `fill` as the default.
10. **Thin tracks and angles** (4.42): the mask recognises a track if the pixel is at most half its width (a coverage mask keeps the area of any); a track of 0.05 mm already cools a 6 mm heater by 3 %; the 1 mm cells reproduce 96 to 98 % of an axis-aligned track's effect but only 38 to 53 % (flow-based faces) of a 45-degree one (the fill fraction 63 to 106 %): **isolated diagonal copper on a coarse grid is the largest known residual error**, a property of the four-neighbour network.
11. **Diagonal couplings, simulated** (4.44): faces to the four diagonal neighbours (a hybrid: the flow-based axial faces plus the diagonal conduction they miss) raise the share of a 45-degree track's cooling reproduced from 37 to 84 % to 88 to 120 % (64 to 94 % damped by 0.5) with no change at 0 degrees; on the 42 real windows the undamped version over-adds (3.1 % error, -2.8 % bias) and the version damped by 0.5 keeps the flow-based faces' accuracy (1.77 % against 1.85 %). The damping is a fudge factor chosen on the same windows; a detector of single dominant diagonal conductors is the next step.

## 2. How this differs from the three Electronics Cooling articles

| | Sampson 2005 / 2017 | Blackmore 2010 | Guenin 2015 | this research |
| :-- | :-- | :-- | :-- | :-- |
| Idea | conductance between neighbouring nodes from a local solve on the layer bitmap (200 ppi) | tiles with k_x, k_y, k_z by pixel counting (rows parallel of series chains; k_z arithmetic) | smeared plane from the copper near the package, dielectric derated by width / pitch | all of these as candidates, compared on the same cases |
| Relation to ours | **identical** to `dual_faces` | **identical** to the `lam 0` bound plus the arithmetic fraction | not implemented (two tests proposed, 5 below) | |
| Tile / cell size | grid nodes, finer than the board features | 7 to 14 mm tiles (25 to 50 per side) | n/a | 0.6 to 1 mm cells (heaters of a few mm are the hard case) |
| Reference for validation | a fine model; one post-mounted board, 236 °C against 9 °C smeared | explicit single-layer simulation (3.3 % average, 15.3 % maximum) and one automotive board by experiment (5.7 %) | explicit-trace FEA of the JEDEC board | the mask solved pixel by pixel: 42 windows of 7 real boards, patterns, two layers with plated holes, a four-layer board, copper 18 to 140 µm, heater sizes, time response |
| Number of mappings compared | 2 (smeared against bitmap) | 1 | 3 smeared variants | about 10: fill, power means (geometric, harmonic), Wiener bounds, lambda family, Hashin-Shtrikman, Bruggeman, cell problem, flow-based faces |
| Anisotropy / direction | yes (conductance per pair) | yes (k_x, k_y) | no | yes (directional bounds, flow-based faces); stripes across and along |
| Vias and layers | layer by layer | vias by %Cu bands | vias in the plane model | plated holes as vertical links; 2 and 4 layers |
| Solver | FDM | finite volume | FEA | the program's own FVM, unchanged (agreement 3e-12) |
| Measurement | no | yes (5.7 %) | no | **no** |

**What is new here** (to the best of what was read; the literature search was not exhaustive): the head-to-head ranking of ten mappings against the resolved solution on real boards and regular patterns, including the lambda mix of the Wiener bounds and the finding that the fill fraction and the tile bound alone are biased in opposite directions; the evidence that zone fill must keep its formula (hatched zones +26 to +45 %); the program-in-the-loop check; the Lumped and Analytic treatment (README 4.16); the cost figures (the reader, checked against four other tools, is `gerber-import`; nets, Joule heat and tracks at an angle are `gerber-nets`).

**Where the articles are ahead of us**: Blackmore validates against a physical measurement and studies the tile resolution and the %Cu bands (and says vias need many bands); Sampson fits a k_eff for FEM from the FDM result and treats a post-mounted board at board scale; Guenin explains the local copper near the package and the entrance length of about ten dielectric thicknesses. We have not repeated Sampson's headline (236 °C against 9 °C); our synthetic stripes boards give -49 % (smearing) against +6 % (flow-based) when the heat crosses the stripes, a smaller effect because the geometry is different (his traces do not reach the posts over large areas). That case is open (5 below).

## 3. The validated numbers

Error of the mean temperature rise over the heater block against the resolved mask (MAE %, bias in the README). Single copper sheet, 1 mm cells unless stated.

| Regime | Fill fraction (today) | Geometric mean | Tile (low bound) | Lambda 0.5 | Flow-based faces | Where | Test |
| :-- | --: | --: | --: | --: | --: | :-- | :-- |
| 42 real windows, h = 10, edges insulated (0.6 / 1.0 / 2.0 mm cells) | 9.7 / 11.3 / 11.1 | 2.2 / 2.4 / 3.0 | 2.6 / 4.5 / 9.5 | 1.0 / 1.3 / 3.2 | 0.6 / 0.9 / 3.6 | 4.4 | `test_conduction.py` (limits), `study_mapping.py` |
| 42 real windows, border held at 0 K, h = 0 | 22.6 (cool) | 4.8 | 11.0 (hot) | 2.8 | 2.3 | 4.25 | `study_sampson_boundary.py` |
| same, h = 10 | 20.8 | 4.2 | 9.7 | 2.4 | 2.1 | 4.25 | same |
| random synthetic board (test layout, one case) | -13.7 | +8.8 | +16.8 | +7.6 | +4.9 | `test_claims.py` | `test_fill_fraction_is_too_cool_and_flow_based_faces_hold_on_a_random_board` |
| stripes, heat across them (0.5 mm stripes, 1 mm pitch, no convection) | -48.7 | -13.6 | +6.0 | +6.0 | +6.0 | 4.25 | `test_stripes_show_the_direction_effect_that_smearing_misses` |
| stripes, heat along them | -19.9 | +34.9 | +7.5 | +7.5 | +7.5 | 4.25 | same |
| two layers + plated holes | 13.6 to 14.9 | 3.9 to 4.1 | | 1.0 | 0.4 to 1.3 | 4.12 | `study_two_layer.py` |
| real four-layer board | 3.0 to 4.6 | 0.4 to 1.5 | | 1.5 to 2.8 (up to 7.5 on planes) | 0.3 to 1.1 | 4.13 | `study_multilayer_real.py` |
| regular patterns at 1 mm cells | 7 to 43 | -20 to +22 | | 0 to 2.4 (diagonal +12 at 0.6 mm) | 0.9 to 3.4 | 4.11 | `study_patterns*.py` |

Other validated results:

| Claim | Number | Where | Test |
| :-- | :-- | :-- | :-- |
| Every model, 42 real windows against the program's pixel run, MAE % for arithmetic fill / geometric / lambda 0.5 / flow mean (additive-union copy of `develop` `a6f822b`) | FVM 21.3 / 5.6 / 7.6 / 9.6; FDM 26.3 / 12.7 / 15.3 / 15.9; Lumped 27.7 / 15.5 / 17.6 / 17.9; Analytic 30.4 / 22.0 / 23.3 / 23.4; 3D solid 19.4 / 7.0 / 7.5 / 8.7 | 4.16, 4.27 | `study_lumped_analytic.py` |
| Every model against itself on the fine mask (4 windows) | FVM 11.6 to 1.3 to 1.9; FDM 8.1 to 2.4 to 3.1; Lumped and Analytic are reduced models, judge them against the physics | 4.27 | `study_models_self.py` |
| Program unions zones by maximum: the same copper in 0.5 mm strips is hotter | +7 % FVM, +17 % FDM, +10 % 3D solid, +7 % Analytic, +8 % Lumped | 4.27 | `test_union_by_maximum_loses_copper_when_zones_share_cells` |
| Coverage mask against binary at 0.1 mm (21 real windows, truth 0.025 mm): flow-based faces | 6.5 to 4.1 % (thin-track boards 15.8 to 4.6 and 11.3 to 2.8) | 4.26 | `study_coverage.py`, `study_coverage_real.py`, `test_coverage_keeps_the_area_of_thin_tracks` |
| Post-mounted board analogue: smeared model against the bitmap, maximum rise | -81 to -90 % without convection (factor 5 to 10; the article: 26), -28 to -35 % with 10 W/m2K | 4.28 | `study_post_board.py` |
| Published 10 % copper example: along 39.6 (article ~40), across 0.655 W/m K (article 0.65) | exact | 4.21 | `test_published_parallel_and_series_example` |
| Blackmore's tile formulas = `low` bound + arithmetic fraction | exact | 4.21 | `test_blackmore_tile_formulas_are_the_lower_bound_and_the_arithmetic_mean` |
| Through the program's `fvm.Network` only the conductances change | plumbing check 1e-6 K (the 3e-12 agreement with the research solver held only before the laminate nodes) | 4.14 | `tests/test_importer.py`, `prototype_in_program.py` |
| Lumped inherits a better S: 27.7 to 15.5 %; Analytic needs one effective conductance (influence-weighted power mean, p = -0.2): 30.4 to 8.8 % | against the program's pixel run | 4.16 | `study_lumped_analytic.py` |
| Our IC board as a thermal bench: fill fraction -5.6 % and flow-based faces +4.4 % at 1 mm cells | 1 test | 4.30 | `tests/test_our_board_models.py` |
| Import end to end on two boards, through the program's FVM | Stormduino -15.1 to -2.1 / -5.3 %; our board -4.8 to +7.3 / +5.2 %; another reader 0.01 to 0.04 % (not re-run: gerbonara is not installed in the review's environment; the Stormduino did not move) | 4.31 | `study_import_end_to_end.py`, `tests/test_importer.py` |
| Rectangle board: convergence | FVM and FDM to the same value (1 %); 1 mm FVM +1.3 % (edges on cells) and -6.4 % (off); Lumped -16 %, Analytic -26 %, 3D +7 to +9 % of the FVM | 4.35, 4.37 | `study_rect_convergence.py`, `tests/test_rect_board.py` |
| Our board in the five models, mappings as cell values | FVM +14 to +24 %, FDM +15 to +24 %, Lumped +29 to +43 % | 4.34 | `study_models_our_board.py` |
| Every mapping as an option, eleven boards, mean absolute error | fill 7.4 %, flow 2.3 %, Wiener upper 2.3 %, lambda 2.4 %, cell problem 2.4 % | 4.38, 4.43 | `study_boards_matrix.py` |
| Diagonal couplings: share of a 45-degree track's cooling (flow-based faces / hybrid alpha 0.5 / alpha 1), and the 42 windows | 37 to 84 % / 64 to 94 % / 88 to 120 %; windows 1.85 % / 1.77 % / 3.13 % | 4.44 | `study_diagonal.py`, `tests/test_diagonal.py` |
| One track across the heater: share of its cooling reproduced by the 1 mm cells | 96 to 98 % at 0 degrees; 38 to 53 % (flow), 63 to 106 % (fill) at 45 degrees | 4.42 | `study_track_width_angle.py`, `tests/test_track_width_angle.py` |
| Corrections to the program | strips -8.2 % FVM, -19.1 % FDM, -8.3 % 3D; overlap exact; example boards 0 (zone union, not applied); single layer 3D 346 to 174.5 K (in the program since) | 4.39 | `study_fix_impact.py` |

## 4. What is not validated, and the limits

* **No comparison with a physical measurement**, by us or in the first-hand data of the articles beyond Blackmore's 5.7 %. Every number is against a resolved mask, i.e. against the same physics solved finely.
* The reference solver of the 42-window studies is one sheet (copper and the whole laminate in the plane, convection on both faces), the program's idealisation before its laminate nodes: 22 % cool against an independent 3D solution of real one-layer copper (README Review R2). The 3D effects (a trace over a plane, Guenin's local overlap) are covered only through the two- and four-layer studies at 0.6 to 1 mm cells.
* The conduction reference uses the four-neighbour stencil; for very thin tilted tracks (fewer than about 8 pixels across) its absolute resistance is high (`gerber-nets` README 4.23); the relative ranking of the mappings was not repeated with finer pixels or the nine-point stencil.
* Cells of 2 mm and larger: every method is limited by the grid (a 6 mm heater is 3 cells).
* Three formulas written from memory (2D Bruggeman, Hashin-Shtrikman, the Keller-Dykhne duality) are now checked by an independent derivation and numbers (`test_hashin_shtrikman_and_bruggeman_against_independent_forms`); no textbook was opened for them (README Review R5). The Ucamco text on aperture holes, once from memory, was read in the specification (revision 2024.05) by the review of `gerber-import` (`research/gerber-import/docs/literature.md`).
* Sampson's board cannot be rebuilt (its bitmaps are figures); the analogue of 4.28 reproduces the mechanism (smearing predicts 10 to 19 % of the real rise without convection, a factor 5 to 10 where the article has 26) but not the size, and uses one equivalent sheet with an invented perforation. The program's 3D solid could not be used as a check of the mapping when the study was made (4.27); its fine runs are now refused by its size limit, and the review used an independent 3D solver instead (README Review R2).
* The synthetic random board of the test is one deterministic case, a regression check and not a statistic; the statistics are the 42 windows.
* The corrections of 4.39 were measured on copies of the program outside the repository and with the tests that touch zones and the 3D solid (57 passed, 2 GUI tests need `pytest-qt`), not with the whole battery.
* The 3D solid (two layers) is the independent formulation available here; it is not a measurement.

## 5. Recommendations and decisions left to the maintainer

1. **Stage 1 (smallest useful)**: imported copper as its own element with the **flow-based faces** for FVM, FDM and the 3D solid; **lambda 0.5** as the quick mode; Lumped reads the result unchanged; Analytic gets one effective conductance per layer. Keep `Zone.fill` as it is (`INTEGRATION.md`). Offer the mapping as `SolverOptions.copper_mapping` (default `fill`).
2. **Independently of the import, correct the combination of zones** by the maximum per sample point (`geometry.zone_fill`; 4.39), in a `fix/<topic>` branch off `develop` with the whole battery (the laminate of the 3D solid under a single copper layer is in the program already).
3. **Honest labelling in the documents of the program**: the method is Sampson's; the mappings are compared in this research; there is no measurement yet.
4. **Two validation scenarios still to add**: Sampson's own board (needs its bitmaps; the analogue is in 4.28) and Guenin's local vertical overlap against the 3D solid (`docs/literature.md`, section 6). A measurement on one real board would turn the whole study from "agrees with the resolved model" into "agrees with the world".
5. **To continue with the copper mapping** (REPORT.md section 8): a detector of the cells that should get diagonal faces: a first one was tried (4.48: the cell tensor's coherence as a ramp gives 1.43 % on the 42 windows against 1.77 % for the fixed share, and reproduces 99 to 106 % of a 45-degree track of 0.15 to 0.3 mm, but not the thinnest and the widest) and **did not hold up on held-out data** (4.50: 1.76 % against 1.86 % with no diagonals at 1.0 mm, none on a board never used, worse at 0.5 mm; the best share depends on the cell size), so it is a diagnostic, not a method; and the nine-point faces in the program's network; one measurement of a real board; the mapping studies with a finer pixel and a nine-point reference; more boards (power, heavy copper, metal core, many diagonals).
6. **Open decisions** (the maintainer's): which stage enters the program; which mapping is the default of an import; the zone `pattern` for hatched zones.

## 6. How to reproduce

```
cd research/gerber-models && ../../.venv/bin/python -m pytest -q tests                  # 34 tests, about 30 s
.venv/bin/python research/gerber-models/scripts/study_sampson_boundary.py               # section 4.25, about 10 minutes
.venv/bin/python research/gerber-models/scripts/study_mapping_options.py                # section 4.38, about 5 minutes (PYTHONPATH=. if the program is not importable)
.venv/bin/python research/gerber-models/scripts/study_fix_impact.py max                 # and additive, union, union_lam with the patched copies on PYTHONPATH; then --compare
.venv/bin/python research/gerber-models/scripts/make_figures.py                         # the pictures in figures/
```
The boards are in `research/gerber-import/data` (`research/gerber-import/scripts/fetch_boards.py`; git-ignored; their licences differ). The layout of the folder is described in `README.md`, section 3; what was read and what was not verified in the last section of `README.md`.
