# Conclusions: importing Gerber copper into the thermal grid

Written 2026-10-23 on branch `research/gerbers`. Everything quoted here has a section of `README.md` (numbers, tables, limits), a script (`study_*.py`) and, where it is a claim that can break, a test (`tests/`, 71 tests in about 21 s; `python -m pytest -q tests` from this folder; the two program tests need the program's dependencies and one geometry test needs shapely). Nothing in `pcbthermal/` was changed.

## 1. Where we stand

1. **Reading is solved without third-party libraries for what the program needs** (copper layers and drills). The NumPy-only reader (`native_gerber.py`) gives the same raster as gerbonara + shapely at the pixel, is faster, refuses what it cannot do, and reads the net names (`TO.N`). It is a smaller reader, not a better one (README 4.17 to 4.19, 4.22, 4.24).
2. **The fill fraction the program uses today is biased cool on real copper**: 10 to 23 % on real boards depending on the regime, up to 49 % across stripes, because clearances cut paths that the average assumes connected (README 4.4, 4.7, 4.11 to 4.13, 4.25).
3. **A good mapping exists and is cheap**: the flow-based face conductances (a local conduction problem between two cell centres) are within 0.3 to 3.6 % in every case tested, 5.5 s per 100 x 160 mm layer once at import. **This is Sampson's method (2005, article 2017), not ours.** Lambda 0.5 (the geometric mean of the two Wiener bounds per direction) is almost as good at no cost (1.0 to 3.2 %), and is the quick mode (section 3 below, README 4.4).
4. **Zone fill must keep its formula**; imported copper gets its own element (README 4.10, `INTEGRATION.md`).
5. **Resolution matters more than the reader**: at most half the thinnest track per pixel for area and connectivity, 8 to 10 pixels across for the resistance of a thin track; binary masks lose or invent area on thin copper; a lattice-aligned track as wide as the pixel can vanish (README 4.3, 4.22, 4.23).
6. **A coverage (grey-level) mask is a better default than a binary one**: at the same 0.1 mm grid it cuts the error of the flow-based faces from 6.5 to 4.1 % on 21 real 20 mm windows and by a factor 3 to 4 on thin-track layouts; part of the gain compensates a small bias of the mapping (README 4.26).
7. **The program's zones cannot carry fine copper as they are**: a zone is one polygon without holes, and zones are combined per cell with a maximum instead of a sum, so copper tiled in many polygons loses copper in each shared cell (+7 % FVM to +17 % FDM; test). The import needs its own path (mapping and data model), and one line of the program (an additive union) is advisable independently (README 4.27, `INTEGRATION.md` section 0).
8. **Vias and nets map from the files**: plated holes (X2 file function of the drill file) matched to the via pads (aperture function) and their nets give the program's vias and the connection of polygons across layers; on a real 4-layer KiCad board 225 of 225 vias have the same net on all four layers (README 4.29).
9. **Nets and Joule heat are feasible**: the net comes from the file (pads and tracks; zone fills may carry none, so use connectivity), and `joule.py` turns a current into a heat map that sums exactly to I²R (README 4.20).

## 1b. Where we stand with importing Gerbers with our code (2026-10-23)

The path exists as research code (`lib/importer.py`, README 4.31, figure 7): files, copper masks, holes, nets and vias, a `Problem` with the vias, face conductances, and a solve through the program's own `fvm.Network`. On the Stormduino (2 layers, 109 vias) the heater temperature is -15.1 % with the program's mapping and -2.1 % (binary) or -5.3 % (coverage) with imported faces; on our IC board -5.0 % against +4.0 % and +2.1 %. Another reader changes the result by 0.01 to 0.04 %. **Missing**: the step where the user confirms layers and outline, several heaters, directional faces in the FDM and the 3D solid, component leads, any measurement.

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

**What is new here** (to the best of what was read; the literature search was not exhaustive): the head-to-head ranking of ten mappings against the resolved solution on real boards and regular patterns, including the lambda mix of the Wiener bounds and the finding that the fill fraction and the tile bound alone are biased in opposite directions; the evidence that zone fill must keep its formula (hatched zones +26 to +45 %); the program-in-the-loop check; the Lumped and Analytic treatment (README 4.16); a reader and rasteriser with no licence cost, checked against four other tools; nets and Joule heat; the study of tracks at an angle; the cost figures.

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
| Every model, 42 real windows against the resolved sheet, MAE % for arithmetic fill / geometric / lambda 0.5 / flow mean (additive-union copy of the program) | FVM 11.9 / 2.6 / 2.9 / 4.0; FDM 15.9 / 7.1 / 7.8 / 7.8; Lumped 13.0 / 4.8 / 4.9 / 4.9; Analytic 18.6 / 12.2 / 12.5 / 12.4; 3D solid not usable (+43 % already, 49 to 70) | 4.27 | `study_lumped_analytic.py` |
| Every model against itself on the fine mask (4 windows) | FVM 11.6 to 1.3 to 1.9; FDM 8.1 to 2.4 to 3.1; Lumped and Analytic are reduced models, judge them against the physics | 4.27 | `study_models_self.py` |
| Program unions zones by maximum: the same copper in 0.5 mm strips is hotter | +7 % FVM, +17 % FDM, +10 % 3D solid, +7 % Analytic, +8 % Lumped | 4.27 | `test_union_by_maximum_loses_copper_when_zones_share_cells` |
| Coverage mask against binary at 0.1 mm (21 real windows, truth 0.025 mm): flow-based faces | 6.5 to 4.1 % (thin-track boards 15.8 to 4.6 and 11.3 to 2.8) | 4.26 | `study_coverage.py`, `study_coverage_real.py`, `test_coverage_keeps_the_area_of_thin_tracks` |
| Post-mounted board analogue: smeared model against the bitmap, maximum rise | -81 to -90 % without convection (factor 5 to 10; the article: 26), -28 to -35 % with 10 W/m2K | 4.28 | `study_post_board.py` |
| A board of our own (`our_board.py`): nine nets in one piece each and no short, 16 holes with the right nets, arc net resistance within +15 % of the hand count, fill fraction -5.6 % and flow-based faces +4.4 % at 1 mm cells | 4 tests | 4.30 | `tests/test_our_board.py` |
| Vias and nets: 225 vias of a 4-layer KiCad board, net equal on all four layers | 225 of 225; 68 of 68 plated component holes of the X2 test set agree on both layers | 4.29 | `study_vias_nets.py`, `tests/test_nets.py` |
| Published 10 % copper example: along 39.6 (article ~40), across 0.655 W/m K (article 0.65) | exact | 4.21 | `test_published_parallel_and_series_example` |
| Blackmore's tile formulas = `low` bound + arithmetic fraction | exact | 4.21 | `test_blackmore_tile_formulas_are_the_lower_bound_and_the_arithmetic_mean` |
| Through the program's `fvm.Network` only the conductances change | agreement 3e-12 | 4.14 | `prototype_in_program.py` (needs the program) |
| Lumped inherits a better S: 13.0 to 4.8 %; Analytic needs one effective conductance (influence-weighted geometric-type mean): 18.6 to 5.9 % | | 4.16 | `study_lumped_analytic.py` |
| Reader area vs gerbonara + shapely, 8 real boards | 0.0 to 0.9 % average per board | 5 | `study_native_check.py` |
| Reader on 14 files of known area: same raster as gerbonara + shapely and pcb-tools (binary) | to the digit; error is the pixel | 4.22 | `compare_readers.py`, `tests/test_native_gerber.py` |
| Reader, files of gerbonara's test set | 149 of 164 comparable within 3 % | 4.17 | `study_reader_conformance.py` |
| Drills, 35 files read by both tools | 35 identical | 4.19 | `study_reader_scope.py`, `test_excellon_*` |
| gerber-writer files: arcs and thermal macros | -0.04 % (gerbonara -8.57 %) | 4.24 | `study_gerber_writer.py` |
| Track at any angle: area within 0.5 % except 45° on the lattice (±6 %); 4-connectivity breaks a track as narrow as the pixel, 8-connectivity does not | | 4.23 | `test_thin_track_at_an_angle_connectivity_area_and_resistance`, `test_a_track_as_wide_as_the_pixel_can_vanish_on_the_lattice` |
| Resistance of a tilted track, five-point stencil: +97 % at 1.5 px, +10 % at 8 px, +6 % at 12 px across | | 4.23 | same, `study_angles.py` |
| Net pieces by connectivity; wire keeps its net | | 4.20 | `test_net_pieces_are_found_by_connectivity_and_a_thin_wire_keeps_its_net` |
| Joule heat of a net: strip, series, parallel, conservation | exact to 1e-9 | 4.20 | `tests/test_joule.py` |

## 4. What is not validated, and the limits

* **No comparison with a physical measurement**, by us or in the first-hand data of the articles beyond Blackmore's 5.7 %. Every number is against a resolved mask, i.e. against the same physics solved finely.
* The reference solver is a layered sheet model (copper sheet on laminate, convection on both faces), the program's own model. The 3D effects (a trace over a plane, Guenin's local overlap) are covered only through the two- and four-layer studies at 0.6 to 1 mm cells.
* The conduction reference uses the four-neighbour stencil; for very thin tilted tracks (fewer than about 8 pixels across) its absolute resistance is high (README 4.23); the relative ranking of the mappings was not repeated with finer pixels or the nine-point stencil.
* Cells of 2 mm and larger: every method is limited by the grid (a 6 mm heater is 3 cells).
* The reader: no aperture blocks, mirrored/rotated/scaled apertures, moire or image mirror; a drill file with no unit is refused; net names exist only when the CAD tool writes them (zone fills often have none); the Ucamco specification and test files were not read (host blocked).
* Four formulas (2D Bruggeman, Hashin-Shtrikman, Dykhne duality, the Ucamco text on aperture holes) are from memory, checked by limits only (`docs/literature.md`).
* Sampson's board cannot be rebuilt (its bitmaps are figures); the analogue of 4.28 reproduces the mechanism (smearing predicts 10 to 19 % of the real rise without convection, a factor 5 to 10 where the article has 26) but not the size, and uses one equivalent sheet with an invented perforation. The 3D solid, the only model with real slabs, cannot be used as a check of the mapping (4.27).
* The synthetic random board of the test is one deterministic case, a regression check and not a statistic; the statistics are the 42 windows.

## 5. Recommendations and decisions left to the maintainer

1. **Stage 1 (smallest useful)**: imported copper as its own element with the **flow-based faces** for FVM, FDM and the 3D solid; **lambda 0.5** as the quick mode; Lumped reads the result unchanged; Analytic gets one effective conductance per layer. Keep `Zone.fill` as it is (`INTEGRATION.md`).
2. **Import settings the program should enforce**: draw the copper as a coverage mask (4 x 4 sub-samples) at 0.1 mm; a pixel at most half the thinnest track found in the file (and a warning when a track is thinner than the pixel); 8-connected labelling for any question of "which piece is which"; finer pixels for the resistance of thin tracks.
   **Independently of the import**, change the program's zone union from a maximum to an additive coverage (non-overlapping zones add up; overlapping ones are capped at 1): the maximum loses copper in every cell shared by several zones (4.27).
3. **Nets**: use the X2 net attribute when present, infer by connectivity for the rest, and let the user assign a piece otherwise; the heat of a net needs the current (user input) and the terminals; vias between layers and `rho(T)` coupling come later (README 4.20).
4. **Honest labelling in the documents of the program**: the method is Sampson's; the mappings are compared in this research; there is no measurement yet.
5. **Two validation scenarios still to add**: Sampson's own board (needs its bitmaps; the analogue is in 4.28) and Guenin's local vertical overlap against the 3D solid (`docs/literature.md`, section 6; the 3D solid itself needs checking at fine cells first, 4.27). A measurement on one real board would turn the whole study from "agrees with the resolved model" into "agrees with the world".
6. **Open decisions** (the maintainer's): which stage enters the program; the zone `pattern` for hatched zones; whether to try the finer-pixel / nine-point repeat of the mapping studies first; whether to download the Ucamco example data sets as extra conformance files.

## 6. How to reproduce

```
research/gerbers/.venv/bin/python -m pytest -q research/gerbers/tests                    # 68 tests, about 17 s
research/gerbers/.venv/bin/python research/gerbers/scripts/study_sampson_boundary.py     # section 4.25, about 10 minutes
research/gerbers/.venv/bin/python research/gerbers/scripts/compare_readers.py synthetic  # needs gerbonara, pygerber, pcb-tools, shapely, pillow
research/gerbers/.venv/bin/python research/gerbers/scripts/make_figures.py               # the pictures in figures/
```
The boards are downloaded by `scripts/fetch_boards.py` and `scripts/study_reader_conformance.py` into `data/` (git-ignored; their licences differ). The layout of the folder is described in `README.md`, section 3; what was read and how in `LOG.md`.
