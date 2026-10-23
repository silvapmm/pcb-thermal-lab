# Conclusions: importing Gerber copper into the thermal grid

Written 2026-10-23 on branch `research/gerbers`. Everything quoted here has a section of `README.md` (numbers, tables, limits), a script (`study_*.py`) and, where it is a claim that can break, a test (`tests/`, 58 tests in 8 s with NumPy and SciPy only; `python -m pytest -q tests` from this folder). Nothing in `pcbthermal/` was changed.

## 1. Where we stand

1. **Reading is solved without third-party libraries for what the program needs** (copper layers and drills). The NumPy-only reader (`native_gerber.py`) gives the same raster as gerbonara + shapely at the pixel, is faster, refuses what it cannot do, and reads the net names (`TO.N`). It is a smaller reader, not a better one (README 4.17 to 4.19, 4.22, 4.24).
2. **The fill fraction the program uses today is biased cool on real copper**: 10 to 23 % on real boards depending on the regime, up to 49 % across stripes, because clearances cut paths that the average assumes connected (README 4.4, 4.7, 4.11 to 4.13, 4.25).
3. **A good mapping exists and is cheap**: the flow-based face conductances (a local conduction problem between two cell centres) are within 0.3 to 3.6 % in every case tested, 5.5 s per 100 x 160 mm layer once at import. **This is Sampson's method (2005, article 2017), not ours.** Lambda 0.5 (the geometric mean of the two Wiener bounds per direction) is almost as good at no cost (1.0 to 3.2 %), and is the quick mode (section 3 below, README 4.4).
4. **Zone fill must keep its formula**; imported copper gets its own element (README 4.10, `INTEGRATION.md`).
5. **Resolution matters more than the reader**: at most half the thinnest track per pixel for area and connectivity, 8 to 10 pixels across for the resistance of a thin track; binary masks lose or invent area on thin copper; a lattice-aligned track as wide as the pixel can vanish (README 4.3, 4.22, 4.23).
6. **Nets and Joule heat are feasible**: the net comes from the file (pads and tracks; zone fills may carry none, so use connectivity), and `joule.py` turns a current into a heat map that sums exactly to I²R (README 4.20).

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
* Sampson's headline case (copper absent over large areas around posts, no convection) is not reproduced at his scale; our stripes boards reproduce the direction and part of the size of the effect.
* The synthetic random board of the test is one deterministic case, a regression check and not a statistic; the statistics are the 42 windows.

## 5. Recommendations and decisions left to the maintainer

1. **Stage 1 (smallest useful)**: imported copper as its own element with the **flow-based faces** for FVM, FDM and the 3D solid; **lambda 0.5** as the quick mode; Lumped reads the result unchanged; Analytic gets one effective conductance per layer. Keep `Zone.fill` as it is (`INTEGRATION.md`).
2. **Import settings the program should enforce**: pixel at most half the thinnest track found in the file (and a warning when a track is thinner than the pixel); 8-connected labelling for any question of "which piece is which"; a pixel of at most 0.1 mm for copper, finer for nets with thin tracks.
3. **Nets**: use the X2 net attribute when present, infer by connectivity for the rest, and let the user assign a piece otherwise; the heat of a net needs the current (user input) and the terminals; vias between layers and `rho(T)` coupling come later (README 4.20).
4. **Honest labelling in the documents of the program**: the method is Sampson's; the mappings are compared in this research; there is no measurement yet.
5. **Two validation scenarios to add**: Sampson's copper-stops-before-the-posts case at board scale, and Guenin's local vertical overlap against the 3D solid (`docs/literature.md`, section 6). A measurement on one real board would turn the whole study from "agrees with the resolved model" into "agrees with the world".
6. **Open decisions** (the maintainer's): which stage enters the program; the zone `pattern` for hatched zones; whether to try the finer-pixel / nine-point repeat of the mapping studies first; whether to download the Ucamco example data sets as extra conformance files.

## 6. How to reproduce

```
python -m pytest -q tests                      # 58 tests, about 8 s (NumPy and SciPy)
python study_sampson_boundary.py               # section 4.25, about 10 minutes
python compare_readers.py synthetic            # needs gerbonara, pygerber, pcb-tools, shapely, pillow
python make_figures.py                         # the pictures in figures/
```
The boards are downloaded by `fetch_boards.py` and `study_reader_conformance.py` into `data/` (git-ignored; their licences differ).
