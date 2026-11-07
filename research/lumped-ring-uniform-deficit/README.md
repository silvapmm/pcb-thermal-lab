# Why the Lumped model reads cool on a uniform sheet: the width of its first ring

Question (open finding of `research/reduced-models-imported-passives`, chapters 3 and 6): on a **uniform** layer-average sheet the Analytic model agrees with the FVM (-4 to +5 % on RP2040) but the Lumped reads cool by 2 to 16 % and by up to 30 % on CO60, and nobody knew why. The Analytic with the same equivalent rectangle is only 2 to 4 % cool on CO60, which pointed at the Lumped ring construction and not at the rectangle.

Every number below was printed by a script of `scripts/` (run from the repository root; the imported boards need `eval "$(pcb-library/scripts/link_env.sh)"`); the JSON files are in `out/` (git-ignored). Percentages are "model / FVM - 1" on the hottest node unless a table says "mean over the footprint". The program is not edited: the Lumped ring construction is changed on a copy built at import time from the program's own source (`lib/lumped_log.py`, which fails loudly if its anchors move and is bit-identical to the program at its defaults: `tests/test_lumped_log.py`).

## 1. Findings in short

* **Cause found.** The first ring of the Lumped network is `E1 = max(1.5 cells, 0.04 E_max)` wide, where `E_max` is the distance from the footprint to the **farthest cell of the board** (`lumped.ring_edges`, theory 5.1 eq. 5.1). So the width of the ring next to a small part grows with the size of the board and with the distance of the part from the far corner. The link between ring means is the sum of two half rings taken as straight strips of length `area / width` (theory 5.2); for a wide ring around a small footprint that strip has far less resistance than the annulus the heat really crosses (0.79 of it for a ring as wide as the footprint radius, 0.43 for ten radii, section 4), so the part reads cool. On the uniform sheets the effect is: 1 mm part on a two-layer board centred, 30 x 20 mm +0.0 %, 60 x 40 -1.4 %, 100 x 80 **-13.7 %**, 200 x 150 **-25.3 %**.
* **It is the only term that matters on a centred part.** One thing at a time on a 100 x 80 mm board (section 5): the ring count (6, 20, 40), the merge of thin rings, the vertical-loss (Bessel) factors, the footprint peak and the raster all leave the 1 mm deficit at -13 to -14 % (the cell of 1 mm makes it -21 %); the first ring alone takes it to +0.3 %.
* **Fix proposed** (a one-line change in `ring_edges`, a copy in `lib/lumped_log.py`): the first ring is at most one equivalent radius of the footprint wide (never less than 1.5 cells): `E1 = min(max(1.5 cells, 0.04 E_max), max(1.5 cells, a_eq))`, `a_eq = sqrt(footprint cells x cell area / pi)`. A footprint larger than `0.04 E_max` keeps the program's value, so **the 62 via boards of the earlier Lumped studies, the example board with its via arrays and every one of the 17 x 3 frozen records are bit-identical** (sections 6 and 7). A stronger variant, a first ring always 1.5 cells wide, takes small parts nearer the FVM but moves the example board and six frozen records at 2 mm (section 6): a decision for the maintainer.
* **Numbers of the fix.** Simple boards (section 5): a 1 mm part on 200 x 150 mm from -25.3 % to +2.5 %, on 100 x 80 mm from -13.7 % to +0.3 %; 2 mm sources on 100 x 80 mm for 1, 2 and 4 layers, fill 1 and 0.6, films 10 to 200 W/m2K, with and without edge convection: -5.5 to -10.8 % become -1.1 to -4.3 %; the independent 3D solver confirms (section 5.3: -15.0 % becomes -3.0 % for a 1 mm part). Imported boards on the uniform sheet (section 7): RP2040 27 parts mean -10.6 % to -4.2 %, CO60 5 parts -19.6 % to -8.0 % (C1 -29.7 % to -9 %), oswlight 51 parts -9.0 % to -8.1 % (this board is small: the first ring was not the cause there, section 8).
* **What is left** (not fixed here): (a) a source **near a board edge or corner** is still 5 to 15 % cool in the Lumped (the Analytic is exact there), section 9; (b) on a board with an **outline** both reduced models run on the equivalent rectangle and read 10 to 19 % cool next to the outline (oswlight SW2: Analytic -9.7 %, Lumped -18.7 %, and without the outline +0.8 % / -5.5 %), section 8; (c) the Lumped on the **imported copper** stays 45 to 60 % cool because of the copper structure below the cell: this fix removes only the uniform-sheet part of that gap (RP2040 imported mean -59.6 % to -56.8 %).

## 2. How the uniform deficit was reproduced

`lib/variants.py` of `reduced-models-imported-passives` builds the uniform variant (one zone per layer at the layer-average fill, vias and outline kept); `scripts/study_imported_parts.py` runs it for every heat source, one part at a time, 1 W, cell 0.5 mm, FVM as the reference:

| Board | parts | Lumped, program: mean (range) | Analytic: mean (range) |
| :-- | --: | :-- | :-- |
| RP2040 (52 x 51 mm, 2 layers) | 27 | -10.6 % (-16.0 to -2.0) | -1.9 % (-3.9 to +5.1) |
| oswlight (36 x 36 mm, 4 layers) | 51 | -9.0 % (-19.0 to +8.3) | -4.1 % (-10.1 to -0.7) |
| CO60 (285 x 95 mm, 2 layers; R1, C1, U1, RGB1, D59) | 5 | -19.6 % (-29.7 to -9.5) | -2.3 % (-3.8 to -1.5) |

*Table 1 (`study_summary.py`).* The earlier folder's ranges are reproduced (RP2040 -2 to -16 %, CO60 up to -30 %, C1 -29.7 %). Removing the vias or the outline of RP2040 does not move the Lumped (C3 -12.1 % with both, -11.4 % without either), so neither is the cause there.

## 3. The simple boards separate the ring construction from the imported geometry

![rings](figures/fig_01_rings_small_and_large_board.png)

*Figure 1 (`fig_01_rings_small_and_large_board.png`, `make_diagrams.py`): the rings as `lumped.ring_edges` builds them around a 1 mm part, 0.5 mm cell, ten rings, to scale in the first 12 mm; top the program (first ring 1.41 mm on a 60 x 40 board, 4.97 mm on 200 x 150), bottom the first ring of at most one equivalent radius.*

`scripts/study_board_size_sweep.py`: two-layer full-copper boards, 35 um, films 10/15 W/m2K, edge 10 W/m2K, centred square source, 1 W, FVM at 0.25 mm (1 and 3 mm sources on boards up to 100 x 80) or 0.5 mm. Lumped hottest node against the FVM (per cent):

| board | source (mm) | FVM (K) | program | first ring 1.5 cells | first ring at most 1 a | Analytic |
| :-- | --: | --: | --: | --: | --: | --: |
| 30 x 20 | 1 / 3 / 10 | 95.00 / 82.91 / 70.46 | 0.0 / +1.2 / 0.0 | 0.0 / +1.2 / 0.0 | 0.0 / +1.2 / 0.0 | -2.1 / -0.3 / 0.0 |
| 60 x 40 | 1 / 3 / 10 | 53.19 / 41.08 / 28.46 | -1.4 / +1.7 / -0.4 | +1.0 / +0.7 / -0.5 | +1.0 / +1.7 / -0.4 | -3.8 / -0.5 / 0.0 |
| 100 x 80 | 1 / 3 / 10 | 44.63 / 32.52 / 19.87 | **-13.7** / -1.2 / -1.7 | +0.3 / +2.9 / +0.3 | +0.3 / -2.5 / -1.7 | -4.5 / -0.7 / -0.1 |
| 200 x 150 | 1 / 3 / 10 | 42.81 / 30.96 / 18.34 | **-25.3** / -8.8 / -3.3 | +2.5 / +1.3 / -0.9 | +2.5 / -2.4 / -3.3 | -4.5 / -0.6 / -0.1 |

*Table 2 (centred sources; the sweep also holds 6 and 20 mm: 200 x 150 gives -4.4 / -1.5 % for the program).*

![deficit against board size](figures/fig_03_deficit_against_board_size.png)

*Figure 3 (`fig_03_deficit_against_board_size.png`): the same numbers against the diagonal of the board, three source sizes.*

The deficit is a function of the board size (it grows from nothing on 30 x 20 mm to a quarter of the rise), of the source size (largest for 1 mm) and of nothing else tried: the conditions of the table below change it very little.

| conditions (100 x 80 mm, 2 mm source unless stated) | program | first ring at most 1 a | first ring 1.5 cells |
| :-- | --: | --: | --: |
| 2 layers, fill 1, 10/15 W/m2K, edge 10 | -7.3 | -2.0 | +0.8 |
| 1 layer | -5.5 | -1.1 | +1.3 |
| 4 layers | -8.7 | -2.6 | +0.7 |
| 2 layers, fill 0.6 | -10.0 | -4.3 | -1.3 |
| 50 / 50 W/m2K | -8.9 | -2.5 | +0.7 |
| 200 / 200 W/m2K | -10.8 | -3.2 | +0.7 |
| no edge convection | -7.3 | -2.0 | +0.7 |

*Table 3 (`study_sensitivity.py`, table 2 of its output; sources of 6 and 10 mm are within -2.4 to +2.0 % in every row and equal for the two candidates but the 1.5-cells one).* The 2 mm source on the 60 x 40 board goes from +2.5 % to -1.7 % with the cap: both are inside the few per cent that the grid phase of a small source gives (section 7).

### 3.1 The independent 3D solver

`scripts/study_independent_3d.py`: board 70 x 70 mm, copper 35 um (400 W/mK), one FR-4 gap of 1.5 mm at 0.4 W/mK in every direction, films 10 W/m2K, insulated edges, 1 W. The solver is `research/effective-conductivity/lib/layered3d.py` (imports nothing of the program; it reproduces Seri Lee's plate and the coupon of Culham and Yovanovich there). Mean rise over the source cells:

| source (mm) | centre | 3D (K) | FVM 0.5 mm | Analytic | Lumped, program | Lumped, first ring at most 1 a |
| --: | :-- | --: | --: | --: | --: | --: |
| 1 | centre | 47.55 | -0.5 % | -3.9 % | -5.2 % | +1.0 % |
| 3 | centre | 33.31 | -0.3 % | -0.9 % | -1.0 % | -1.3 % |
| 10 | centre | 21.12 | -0.1 % | -0.2 % | -0.8 % | -0.8 % |
| 1 | (20, 17) | 50.66 | -0.5 % | -3.7 % | **-15.0 %** | -3.0 % |
| 3 | (20, 17) | 36.42 | -0.3 % | -0.8 % | -8.1 % | -5.9 % |
| 10 | (20, 17) | 24.25 | -0.1 % | -0.1 % | -8.0 % | -8.0 % |

*Table 4.* The FVM is within 0.5 % of the 3D solver, so it is a fair reference for the deficit; the off-centre rows also show the second cause (section 9).

## 4. Why a wide first ring cools the part

![half ring](figures/fig_02_half_ring_strip_and_annulus.png)

*Figure 2 (`fig_02_half_ring_strip_and_annulus.png`, `make_diagrams.py`): the first ring around a small footprint. The heat crosses an annulus whose contour grows with the radius; the program's resistance between the footprint boundary and the ring mean uses a strip of constant length `area / width` (theory 5.2).*

The ring mean is an area mean, so for a wide ring it is far from the footprint, and the resistance to it is `ln` shaped. The ratio of the strip's resistance to that of the annulus (closed form, pure conduction: mean of `ln(r/a)` over the annulus, my own derivation, not a published case):

![ratio](figures/fig_06_strip_against_annulus.png)

*Figure 6 (`fig_06_strip_against_annulus.png`, `make_figures.py`): R(strip) / R(annulus) against the ring width over the footprint radius. Illustrative closed form, not a measurement.*

| width / radius | 0.5 | 1 | 2 | 5 | 10 | 25 |
| :-- | --: | --: | --: | --: | --: | --: |
| R(strip) / R(annulus) | 0.87 | 0.79 | 0.68 | 0.53 | 0.44 | 0.34 |

For a 1 mm part (footprint radius about 0.56 mm on the 0.5 mm raster) the first ring is 1.4 mm wide on 60 x 40 mm (2.5 radii), 2.7 mm on 100 x 80 (4.8 radii) and 5.0 mm on 200 x 150 (8.9 radii): resistance ratios of about 0.6, 0.5 and 0.45, and deficits of 1.4, 13.7 and 25.3 %. The ratio fixes the sign and the order of magnitude; the sizes of the deficits also depend on the interior term and the vertical losses, so this is an explanation that the sensitivity table supports (the first ring is the only term that changes it), not a proof.

The earlier tuning (ten rings, `0.04 E_max`) was done on boards of 30 to 100 mm with sources of several millimetres, where the first ring is narrower than the footprint: the example board and the via families are in that range and are untouched by the cap.

## 5. One thing at a time

`scripts/study_sensitivity.py`, table 1: 100 x 80 mm, two layers, full copper, centred source, Lumped hottest node against the FVM (per cent). Every column changes one thing of the program's construction (`lumped_log.configure`):

| source (mm) | FVM (K) | program | first ring 1.5 cells | first ring cap 1 a | 6 rings | 20 rings | 40 rings | no ring merge | merge at 2 cells | vertical-loss factors = 1 | footprint peak off | cell 1 mm | log link |
| --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| 1 | 44.63 | -13.7 | +0.3 | +0.3 | -13.7 | -13.4 | -13.4 | -13.7 | -13.7 | -13.7 | -13.7 | -20.8 | +12.6 |
| 3 | 32.52 | -1.2 | +2.9 | -2.5 | -0.3 | -0.5 | -0.7 | -1.2 | -1.2 | -1.2 | -8.7 | -7.6 | +5.8 |
| 10 | 19.87 | -1.7 | +0.3 | -1.7 | -0.6 | -1.3 | -1.2 | -1.7 | -1.8 | -1.4 | -13.5 | -1.2 | +1.1 |

*Table 5.* The footprint peak and the cell matter for the hottest node of the larger sources (peak off: -8.7 and -13.5 % for 3 and 10 mm) but do not change the 1 mm deficit (-13.7 % with and without it). The "log link" column replaces the strip by the annulus formula in every half ring with the first ring at 1.5 cells: it overshoots by 6 to 13 % (the cell-based footprint radius and ring positions are inconsistent at 0.5 mm), so the annulus formula is **not** proposed. More rings do not help, and ring counts above 10 **without** the merge of thin rings are unstable (`study_ring_count.py`: 20 rings -7 to +15 %, 40 rings +10 to +27 %, 80 rings +25 to +67 % over the centred sources; it is the reason the merge exists: rings thinner than a cell have a wrong contour length); 40 rings looked good near an edge (+0.2 to +9 % at five places, section 9) only by that instability, since the same setting is +10 to +27 % on the centred sources.

## 6. What the fix changes in the program's own boards

* **62 boards of the via studies** (`study_family` 36 and `study_holdout` 26 of `lumped-via-groups`, with and without vias, `study_via_boards_unchanged.py`): bit-identical for both candidates (0 boards move, change of `T_max` and of the via effect 0.00e+00 K): boards of 30 mm (the default of the specs) with sources of at most 20 mm, where `0.04 E_max` is under 1.5 cells; the result that no number moves is what was printed, the reason is my reading of the specs.
* **The example board with its via variants** (`study_example_board_vias.py`, FVM at 0.25 mm): the cap leaves every row bit-identical (via effect -3.4 / -0.4 / -0.3 / -2.9 / -3.1 / -1.7 / -1.1 / -1.6 %, `T_max` +0.0 to +1.3 %). The 1.5-cells variant moves it to `T_max` +1.3 to +4.3 % (hotter, still on the safe side) and the via effect of the 7 x 7 and 20 x 20 copper-filled arrays to -4.6 to -4.9 %.
* **The 17 frozen boards at 2, 1 and 0.5 mm** (`study_frozen_impact.py`): the cap moves **no record** (every difference is exactly 0). The 1.5-cells variant moves six boards at the test's 2 mm (the Lumped cell is clipped to 1 mm): example and profile board -0.34 K, reference board +0.58 K, example cut to a T +0.26 K, plate with vias -0.38 K, two-layer partial copper -2.61 K (it was -0.3 %, becomes -2.2 % of the FVM rise), and at 0.5 mm many more (plate with a pad -10.6 K, one-layer pad -2.0 K: boards on which the Lumped is already 10 to 14 % cool, where it becomes 3 points cooler).
* **Cost**: none; the ring construction does the same work.

## 7. The parts of the imported boards

`study_imported_parts.py` / `study_summary.py`, one part at a time, 1 W, cell 0.5 mm. Error of the hottest node against the FVM on the same sheet (mean and range over the parts):

| board | sheet | parts | Lumped, program | first ring at most 1 a | first ring 1.5 cells | Analytic |
| :-- | :-- | --: | :-- | :-- | :-- | :-- |
| RP2040 | uniform | 27 | -10.6 (-16.0 to -2.0) | **-4.2 (-12.4 to 0.0)** | -5.4 (-11.0 to +1.3) | -1.9 (-3.9 to +5.1) |
| RP2040 | imported copper | 27 | -59.6 (-74.1 to -31.2) | -56.8 (-71.3 to -31.2) | -57.1 (-72.2 to -28.9) | -55.5 (-74.5 to -21.6) |
| oswlight | uniform | 51 | -9.0 (-19.0 to +8.3) | -8.1 (-19.0 to +8.3) | -8.6 (-19.3 to +6.8) | -4.1 (-10.1 to -0.7) |
| CO60 | uniform | 5 | -19.6 (-29.7 to -9.5) | -8.0 (-11.5 to -4.6) | **-4.6 (-7.8 to 0.0)** | -2.3 (-3.8 to -1.5) |

![parts](figures/fig_05_uniform_sheet_parts.png)

*Figure 5 (`fig_05_uniform_sheet_parts.png`): the error on the uniform sheet of every part, per board.*

The RP2040 imported row confirms what the earlier folder found: the gap on the imported copper is the copper structure under the cell; this fix takes about three points off it. The residual -4 to -12 % on the uniform sheet of small parts is the grid: a 1.5 x 0.65 mm part moved by 0.125 mm on the grid reads 72.7 to 73.4 K in the FVM at 0.25 mm and 68.9 to 75.5 K at 0.5 mm, and the Analytic, which has no ring, is -2 to -7 % on the same parts.

## 8. What is not the cause, and the two other contributions

* **The equivalent rectangle is not the cause** (hypothesis c of the earlier folder). RP2040 is the same with and without the outline. On oswlight it matters, **for both reduced models**: SW2 (uniform, no vias) FVM 74.8 K, Analytic -10.5 %, Lumped -15.3 %; with the outline removed FVM 58.3 K, Analytic +0.8 %, Lumped -5.5 % (`study_outline_and_vias.py`). The FVM follows the true outline (the part sits 4 mm from an edge of a rounded board) and the rectangle of the same area does not: the known limit of `docs/validation.md` 13 (10 to 18 % cool near an edge), shared by both models.
* **Vias are not the cause**: removing them changes the Lumped by 1.4 to 3.8 points on oswlight (SW2 -18.7 % to -15.3 %) and nothing on RP2040 C3 and U1 beyond the FVM's own change.
* **Raster and shape**: the hottest node of a part smaller than three cells is a grid number (section 7).

## 9. A second deficit that this does not fix: a source near an edge

![near an edge](figures/fig_04_deficit_near_an_edge.png)

*Figure 4 (`fig_04_deficit_near_an_edge.png`): error against the distance of the source to the board edge (left edge, centred vertically) and to the corner, 100 x 80 mm board.*

`study_edge_distance.py`, 100 x 80 mm, two layers, full copper, edge 10 W/m2K (a 1.6 mm edge: nearly insulated), FVM 0.5 mm, hottest node:

| source | place | distance (mm) 2 / 5 / 10 / 20 / 40 | program | first ring at most 1 a | first ring 1.5 cells | Analytic |
| --: | :-- | :-- | :-- | :-- | :-- | :-- |
| 3 mm | edge | | -10.0 / -9.9 / -9.1 / -6.3 / -4.4 | -7.7 / -6.9 / -5.6 / -4.5 / -2.3 | -4.9 / -3.4 / -1.9 / -1.1 / +0.5 | -0.4 to -0.6 |
| 3 mm | corner | | -11.7 / -15.4 / -12.8 / -9.2 / -3.9 | -12.4 / -10.7 / -8.5 / -5.1 / -2.2 | -10.7 / -8.2 / -4.9 / -1.4 / +0.7 | -0.3 to -0.6 |
| 10 mm | edge | | -9.2 / -8.3 / -5.7 / -4.3 / -0.6 | same | -8.0 / -6.2 / -4.9 / -2.4 / +0.3 | -0.0 to -0.1 |
| 10 mm | corner | | -15.4 / -12.9 / -10.4 / -5.1 / -2.6 | same | -14.6 / -11.0 / -8.1 / -4.0 / -0.4 | -0.0 to -0.1 |

*Table 6 (the "first ring 1.5 cells" column is from `LRU_PROPOSAL="first 1.5 cells"` runs of the same script).* The cosine series of the Analytic puts the image of the edge in exactly; the ring network keeps one temperature per ring and cannot show that the side of a ring next to the source is hotter. This is a second construction limit (the "angular resolution" of the earlier Lumped studies), it grows with the size of the source and does not depend on the first ring. On boards in which parts sit near the edge (imported boards mostly do) the Lumped is 5 to 15 % cool for it. A fix would need a different representation (rings that are not closed contours, or an image term) and is a separate investigation (`research/ROADMAP.md` entry to be added by the reviewer).

## 10. Limits and honest notes

* One construction (strip links, ten rings, 0.5 mm raster) was changed; the zone network (a footprint over a dense group of vias) calls the same `ring_edges`, and the two call sites of the copy pass the footprint radius to both; the zone model was not measured separately beyond the 62 via boards (bit-identical) and the example board.
* The FVM is the reference for most tables; it is within 0.5 % of the independent 3D solver on the uniform sheet (table 4) but is itself 5 to 12 % below the converged value for a hottest cell of 0.65 mm (research `reduced-models-imported-passives` 3.2), so the absolute errors of the smallest parts in sections 2 and 7 carry that uncertainty; the comparison of the candidates among themselves does not.
* Memory and cost: the CO60 uniform runs peaked at 3.1 GB (above the 2.5 GB of the brief; the peak is the import session and the 0.5 mm FVM of a 285 x 95 mm board), and the independent 3D solves at 70 x 70 mm with 8 sub-slabs peaked at 6.3 GB (a mistake of sizing on my side: a first attempt at 100 x 100 mm reached 4 GB before it was stopped); neither was repeated (the 3D references are kept in `out/ref3d_store.json`).
* The cell 0.5 mm clip of the API: `lumped.solve_steady` is run at the cell the API gives it (clipped to 0.5 to 1 mm); at 1 mm the program's first ring is `max(1.5 mm, 0.04 E_max)` and the cap changes less (a part 1 mm wide is two cells).
* The tests of this folder (`tests/test_lumped_log.py`, 5 tests, 2 s) check bit identity of the copy, the first ring width, the deficit and its removal, and that the cap leaves a 10 mm source unchanged.

## 11. What was read and what was not verified

* **No new source was opened.** The comparison uses the independent 3D layered solver of `research/effective-conductivity/lib/layered3d.py` (its own checks against Seri Lee's plate, the coupon of Culham and Yovanovich and an energy balance are in that folder's README, which was not re-run here: the solver was used as it is, with its source-edge alignment check). The closed form of section 4 (strip against annulus) is my own derivation, not a published case; no published numerical case about the ring construction exists in the bibliography of the program (`docs/theory.md` 5 cites the program's own derivation), so there is no reproduction of a publication in this folder, only of the program's own earlier numbers (section 2) and of the independent 3D solver (section 3.1). `research/theory/BIBLIOGRAPHY.md` needs no change.
* **Reproduced:** the uniform-sheet deficit of the earlier folder (RP2040 -2 to -16 %, CO60 up to -30 %, oswlight -7 to -19 %); the numbers of `reduced-models-imported-passives` Table 1 were not re-run beyond the uniform-sheet rows.
* **Not verified:** a physical board; boards with several heaters at once (the Lumped superposes single-heater networks, every study here has one source); transient and profile runs of the Lumped (the same `ring_edges` feeds them: not run); the zone network with a part larger than a core at the fix; the effect on `docs/validation.md` 27.7 numbers (the imported-copper warning text quotes 17 to 42 % and 22 to 75 % for the whole RP2040 board; only the uniform-sheet share of those moves); the first ring variants on boards with a metal block or a heatsink; the parts of oswlight on the imported copper with the cap (not run: the board is small, so the cap changes nothing there by construction, see the uniform rows).
* **Own doubts:** (1) the explanation of section 4 is supported by the one-at-a-time table and the ratio, but the size of the deficit is not predicted by the ratio alone; (2) the cap value 1 (equivalent radius) is a choice made for zero impact on the existing boards, not an optimum (1.5 cells is nearer the FVM on small parts); (3) `a_eq` is the radius of the cells that the footprint touches, which for a part smaller than a cell is the cell, not the part.
