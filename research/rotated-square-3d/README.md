# The rotated square in the 3D solid (A3)

**Question.** A square board turned against the grid comes out hotter in the 3D solid than the same square on the grid when the edge coefficient is high (+1.15 K in the reviews of `solid3d-verification` and `outline`). Does it still happen on the current program, where does it come from, is it only the 3D solid, and is there a correction that can be measured on a copy?

**Answer in short** (details, tables and limits below):

* It still happens, and it is larger than +1.15 K at high edge coefficients: 40 mm square, 1 mm cells, 2 W part: +0.8 to +1.8 K at `h_side` 100 W/m2K, +2.5 to +3.1 K at 1000 W/m2K, within 0.3 K at the default 10 (section 2). It falls only slowly with the cell: at 160 cells per side the error is still +2.0 to +2.3 K (section 4.1; against the continuum value of an independent solver +2.1 to +2.4 K, section 9.2).
* It is not about turning: a **straight edge shifted by half a cell** gives +12 K at 20 cells per side and +2.0 K at 160 (section 4). It is the treatment of the cells that the outline cuts: the conducting cross-section is scaled by the cover of the cell in **all** directions, and the conduction to the edge is a fixed half cell (`0.25 (dx + dy)`) through that scaled conductivity (`pcbthermal/solid3d.py`, the lines that scale `kx` and the edge term). The edge of the turned square then conducts 27 to 38 % less than the aligned one at the same perimeter (section 3).
* Against an independent axisymmetric reference (rings times the same slabs, no square grid) on a **round** board, where every edge cell is cut, the program's 3D solid is +6.6 % high at 1 mm and `h_side` 1000 and still +3.2 % at 0.25 mm; a **cut-cell copy** made in memory from the program's own source (links through the face aperture between the centroids of the board parts, edge conduction over half the depth of the board strip, conductivity not scaled) is within +0.6 % at 1 mm and +0.2 % at 0.25 mm (section 5).
* On the shifted and turned squares the copy removes the dependence: 0.0 to 0.3 K at 40, 80 and 160 cells per side (the 45 degree turn: +0.7 and +0.5 K at 40 and 80), against 5.6 to 5.8, 3.6 to 3.7 and 2.0 to 2.3 K for the program (section 4). Where the program was right (a rectangle, the example board with the five outline presets at the default coefficient) the copy gives the same answer within 0.2 K, at 100 W/m2K within 0.4 K (section 6).
* The FVM and the FDM show the same effect in a much milder form (FVM +4.6 K at 20 cells per side for a half-cell shift, +0.22 K at 80; FDM within 1.2 K) and agree with their own axisymmetric reference on a round board within 0.6 % at 1 mm (section 7). No change is proposed for them.
* The review (section 9) confirmed the cut-cell copy against the continuum value of an independent solver on the shifted and turned squares (within 0.2 K at 40 cells per side and better, except the 45 degree turn), corrected the explanation of the 45 degree residual and of the T board (a part that crosses the outline: a separate defect of the FVM, the FDM and the 3D solid, +2.2 K on the example board cut to a T at the default coefficient), and recommends documenting the edge effect as a limit (P2) and fixing the part across the outline.
* The decision (a correction of `solid3d.py` as measured here, or a documented limit) is the maintainer's: `INTEGRATION.md`.

## 1. The question, and what would answer it

The continuum problem does not know the grid: moving the board by a fraction of a cell, or turning it together with its part, cannot change the temperature. Any difference is a discretisation artefact. So the reference for every comparison is the **invariance itself** (aligned against shifted against turned, same model, same cell) and, for the absolute value, an **independent axisymmetric solution** of the round board (section 5), which no square grid enters.

The program's models are given the same boards: a square board of side `S` in a box, two copper planes (full copper), a square part at the centre, `h_side` from 10 to 5000 W/m2K, cells from 1 mm down to 0.125 mm. `S = 40 mm` in a 60 mm box with a 6 mm part (sections 2, 3), `S = 20 mm` in a 30 mm box with a 3 mm part and `h_side = 2000` (the same edge Biot number as 40 mm at 1000; sections 4, 5) so that the cell ladder reaches 160 cells per side under the size limit of the 3D solid (lifted on the copy and on the program alike, `lib/runs.py`).

### 1.1 What the pictures show

![the same square on the grid three ways](figures/fig_01_cut_cells.png)

*Figure 1 (`figures/fig_01_cut_cells.png`): a 10 mm square on a 1 mm grid, aligned (every edge cell whole), shifted by half a cell (every edge cell half board) and turned by 27 degrees (cells cut at every depth). Shading is the board fraction of the cell, the dots are the centroids of the board parts of the cut cells, the blue line is the outline.*

![section of an edge cell](figures/fig_02_section_of_an_edge_cell.png)

*Figure 2 (`figures/fig_02_section_of_an_edge_cell.png`): section through one edge cell (two copper layers, four dielectric slabs) when the outline leaves the whole cell, half of it and a sliver. The red dot is the node of the program (cell centre) and the distance it assumes to the edge (half a cell, whatever the cut); the green square is the centroid of the board part and the distance of the copy (half the depth of the strip). Red arrows: the edge film on every slab; the heat has to come down through the FR-4 (kz = 0.3) to the edge slabs, which is why the distance to the edge matters at high `h_side`.*

![edge resistances](figures/fig_03_edge_resistances.png)

*Figure 3 (`figures/fig_03_edge_resistances.png`): the edge element of one cell and one slab: film `1/(h L dz)` in series with the conduction `d/(k L dz)`; what `d` and `k` are in the program and in the cut-cell copy.*

## 2. Re-measure on the current program

`scripts/study_remeasure.py`. 40 mm square, 60 mm box, two full copper layers, 2 W in a 6 mm square part at the centre, 1 mm cells. "both" turns the board and the part (the continuum problem is the same as the aligned one); "board only" turns the square and leaves the part on the grid; "part only" turns the part and leaves the board aligned. Maximum temperature in °C, in brackets the difference to the aligned square of the same model (K).

**h_side = 10 W/m2K** (the program's default; the 3D solid moves by at most 0.29 K)

| case | FVM | FDM | 3D solid (program) | 3D cut-cell copy |
| :-- | --: | --: | --: | --: |
| aligned | 105.20 | 105.20 | 105.59 | 105.59 |
| both 20 | 104.94 (-0.26) | 104.93 (-0.27) | 105.43 (-0.16) | 105.37 (-0.22) |
| both 45 | 104.97 (-0.23) | 105.14 (-0.06) | 105.76 (+0.17) | 105.95 (+0.36) |
| board only 20 | 105.21 (+0.01) | 105.20 (+0.00) | 105.65 (+0.06) | 105.59 (-0.00) |
| board only 45 | 104.95 (-0.25) | 105.12 (-0.08) | 105.40 (-0.19) | 105.59 (+0.00) |
| part only 20 | 104.92 (-0.27) | 104.93 (-0.27) | 105.37 (-0.22) | 105.37 (-0.22) |

**h_side = 100 W/m2K**

| case | FVM | FDM | 3D solid (program) | 3D cut-cell copy |
| :-- | --: | --: | --: | --: |
| aligned | 90.60 | 90.65 | 91.92 | 91.91 |
| both 10 | 90.41 (-0.19) | 90.38 (-0.27) | 92.73 (+0.81) | 91.53 (-0.38) |
| both 20 | 90.41 (-0.19) | 90.38 (-0.28) | 92.98 (+1.06) | 91.65 (-0.26) |
| both 45 | 90.58 (-0.02) | 90.63 (-0.02) | 93.67 (+1.75) | 92.27 (+0.36) |
| board only 20 | 90.68 (+0.08) | 90.65 (-0.00) | 93.19 (+1.28) | 91.87 (-0.04) |
| board only 45 | 90.56 (-0.04) | 90.61 (-0.05) | 93.31 (+1.40) | 91.91 (+0.01) |
| part only 20 | 90.32 (-0.28) | 90.38 (-0.28) | 91.70 (-0.22) | 91.69 (-0.22) |

**h_side = 1000 W/m2K**

| case | FVM | FDM | 3D solid (program) | 3D cut-cell copy |
| :-- | --: | --: | --: | --: |
| aligned | 70.28 | 70.52 | 74.74 | 74.71 |
| both 20 | 70.33 (+0.05) | 70.23 (-0.29) | 77.64 (+2.90) | 74.31 (-0.40) |
| both 30 | 70.30 (+0.02) | 70.23 (-0.29) | 77.50 (+2.77) | 74.32 (-0.40) |
| both 45 | 70.55 (+0.27) | 70.48 (-0.04) | 77.60 (+2.86) | 75.07 (+0.36) |
| board only 20 | 70.60 (+0.33) | 70.51 (-0.01) | 77.86 (+3.12) | 74.53 (-0.18) |
| board only 45 | 70.53 (+0.25) | 70.46 (-0.06) | 77.25 (+2.51) | 74.72 (+0.00) |
| part only 20 | 70.00 (-0.28) | 70.24 (-0.28) | 74.52 (-0.22) | 74.49 (-0.22) |

*(The rows "both 10" and "both 30" at the other coefficients are in `out/remeasure.json`, regenerated by the script.)*

Reading: the +1.15 K of the reviews is in the program today (+1.06 and +1.28 K at 100 W/m2K, the coefficient where it sits); it comes from the **board** being turned, not from the part (turning only the part moves every model by -0.22 to -0.28 K, the same in all of them: that is the discretisation of a turned source, not the edge). At the default 10 W/m2K the 3D solid moves by at most 0.3 K, which is why the effect passed unseen. The FVM and the FDM move by 0.3 K or less at every coefficient, the part-only row included. The reviews' exact setup was not reproduced; this one has the same dependence on the coefficient and reproduces the sign and the size.

## 3. Where it comes from: the edge element of a cut cell

`scripts/study_edge_conductance.py`. In `pcbthermal/solid3d.py` the in-plane conductivity of a board slab is multiplied by the cover of the cell (`slabs[-1]["kx"] * bcov`) and the edge of a non-rectangular board is `1 / (1 / (h L dz) + 0.25 (dx + dy) / (kx L dz))` per cell and slab, with `L` the outline length in the cell and `kx` that scaled conductivity. For a whole edge cell (aligned) `d = dx/2` and `kx` is the full conductivity: the exact half-cell series. For a cell the outline cuts, `d` stays a half cell although the board part is thinner, and the conductivity is divided by the cover: the path to the edge is made 1 / cover too resistive, for the slivers of a turned square as well as for the half cells of a shifted edge. The 3D solid is the one that shows it because only its edge term has a conduction part: the FVM and the FDM attach the film `h t L` to the node directly (the total is exactly `h t P` at every angle, below).

Total side conductance of the network (sum over cells and slabs), 40 mm square, perimeter 160 mm at every angle, 1 mm cells, ratio to the aligned square of the same model:

| h_side | angle | FVM G / (h t P) | 3D program: G (mW/K), ratio | 3D cut-cell copy: G (mW/K), ratio |
| --: | --: | --: | --: | --: |
| 10 | 0 | 1.000 | 2.55, 1.000 | 2.55, 1.000 |
| 10 | 20 | 1.000 | 2.51, 0.987 | 2.55, 1.003 |
| 100 | 0 | 1.000 | 24.31, 1.000 | 24.34, 1.000 |
| 100 | 20 | 1.000 | 22.08, 0.908 | 24.96, 1.025 |
| 100 | 45 | 1.000 | 21.14, 0.870 | 24.88, 1.022 |
| 1000 | 0 | 1.000 | 168.56, 1.000 | 170.27, 1.000 |
| 1000 | 20 | 1.000 | 117.79, 0.699 | 207.03, 1.216 |
| 1000 | 45 | 1.000 | 121.47, 0.721 | 202.12, 1.187 |
| 5000 | 0 | 1.000 | 379.64, 1.000 | 389.07, 1.000 |
| 5000 | 20 | 1.000 | 235.24, 0.620 | 646.18, 1.661 |

![edge conductance ratio](figures/fig_07_edge_conductance_ratio.png)

*Figure 7 (`figures/fig_07_edge_conductance_ratio.png`): total side conductance of the 3D network of the square turned 20 degrees, ratio to the aligned one, against `h_side`.*

The ratio is not an invariant of the problem: the node of a cell is closer to the edge in the copy (centroid of the board part) than in the aligned square (cell centre), so the conductance from the node to the air is larger by construction; what has to agree is the temperature, and the program's turned edge conducts 27 to 38 % less than the aligned one at 1000 to 5000 W/m2K for the same perimeter, with the temperature 3 K high; the copy's conductance is higher and its temperature is on the aligned one (section 4). The first column (FVM) shows that the length of the edge is not the problem: the perimeter is counted exactly (`edge_length_on_board`, `outline` 4.6).

## 4. Shift and turn against the cell

`scripts/study_cut_cells.py`. 20 mm square board in a 30 mm box, 2 W in a 3 mm part, `h_side` 2000 W/m2K, the board and the part moved together. Maximum temperature in °C (difference to the aligned board of the same model and cell, K). Columns: FVM, FDM, the program's 3D solid, and four copies of the 3D solid made in memory from the source (`lib/rotsq.py`): `kx_physical` (edge term with the unscaled conductivity), `strip` (plus the distance `c dx dy / (2 L)`), `cutcell_floor` and `cutcell` (plus links through the aperture between the centroids; `_floor` limits each half distance to a quarter cell).

**1 mm cells (20 per side)**

| layout | FVM | FDM | 3D program | kx_physical | strip | cutcell_floor | cutcell |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| aligned | 77.74 | 78.49 | 91.02 | 91.02 | 90.86 | 90.86 | 90.86 |
| shift 1/4 cell | 80.71 (+2.97) | 78.64 (+0.15) | 102.77 (+11.75) | 97.55 (+6.53) | 95.13 (+4.27) | 92.27 (+1.40) | 91.94 (+1.08) |
| shift 1/2 cell | 82.31 (+4.57) | 77.90 (-0.60) | 103.31 (+12.28) | 98.31 (+7.29) | 95.51 (+4.65) | 93.61 (+2.75) | 93.61 (+2.75) |
| turned 20 | 79.28 (+1.55) | 79.04 (+0.54) | 100.06 (+9.04) | 95.60 (+4.58) | 93.26 (+2.39) | 91.15 (+0.29) | 90.89 (+0.03) |
| turned 45 | 79.54 (+1.80) | 79.59 (+1.09) | 97.77 (+6.75) | 94.74 (+3.71) | 91.59 (+0.72) | 91.30 (+0.44) | 91.19 (+0.33) |

**0.5 mm cells (40 per side)**

| layout | FVM | FDM | 3D program | kx_physical | strip | cutcell_floor | cutcell |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| aligned | 80.08 | 80.45 | 91.82 | 91.82 | 91.79 | 91.79 | 91.79 |
| shift 1/4 cell | 80.67 (+0.58) | 80.04 (-0.42) | 98.92 (+7.10) | 95.85 (+4.03) | 94.62 (+2.83) | 91.87 (+0.08) | 91.63 (-0.17) |
| shift 1/2 cell | 80.53 (+0.45) | 79.22 (-1.24) | 97.60 (+5.78) | 94.90 (+3.08) | 93.46 (+1.67) | 91.56 (-0.23) | 91.56 (-0.23) |
| turned 20 | 80.28 (+0.20) | 80.13 (-0.32) | 97.42 (+5.59) | 94.85 (+3.03) | 93.70 (+1.90) | 91.71 (-0.08) | 91.53 (-0.27) |
| turned 45 | 80.48 (+0.40) | 80.38 (-0.08) | 96.63 (+4.81) | 94.45 (+2.63) | 93.64 (+1.84) | 92.62 (+0.83) | 92.49 (+0.69) |

**0.25 mm cells (80 per side)**

| layout | FVM | FDM | 3D program | kx_physical | strip | cutcell_floor | cutcell |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| aligned | 80.27 | 80.45 | 91.48 | 91.48 | 91.47 | 91.47 | 91.47 |
| shift 1/4 cell | 80.56 (+0.29) | 80.36 (-0.09) | 96.12 (+4.64) | 94.31 (+2.83) | 93.66 (+2.19) | 91.60 (+0.13) | 91.45 (-0.03) |
| shift 1/2 cell | 80.49 (+0.22) | 80.07 (-0.38) | 95.06 (+3.58) | 93.64 (+2.16) | 92.90 (+1.43) | 91.43 (-0.04) | 91.43 (-0.04) |
| turned 20 | 80.45 (+0.18) | 80.37 (-0.09) | 95.19 (+3.72) | 93.68 (+2.20) | 93.09 (+1.62) | 91.58 (+0.11) | 91.47 (-0.00) |
| turned 45 | 80.52 (+0.25) | 80.47 (+0.02) | 95.26 (+3.78) | 93.37 (+1.89) | 92.90 (+1.43) | 92.01 (+0.54) | 91.96 (+0.49) |

**0.125 mm cells (160 per side, program and cut-cell copy only; run with `--fine`)**

| layout | 3D program | cutcell |
| :-- | --: | --: |
| aligned | 91.38 | 91.38 |
| shift 1/2 cell | 93.42 (+2.03) | 91.37 (-0.01) |
| turned 20 | 93.70 (+2.32) | 91.41 (+0.03) |

![shift and turn against the cells](figures/fig_04_shift_and_turn_vs_cells.png)

*Figure 4 (`figures/fig_04_shift_and_turn_vs_cells.png`): the absolute difference of the maximum temperature to the aligned board against the number of cells per side, for a half-cell shift (left) and a 20 degree turn (right), floor 0.01 K for the log axis.*

![turned square against h_side](figures/fig_05_turned_square_vs_h_side.png)

*Figure 5 (`figures/fig_05_turned_square_vs_h_side.png`): the square turned 20 degrees (part on the grid) minus the aligned one, 40 mm board, 1 mm cells, against `h_side`, four models (the data of section 2).*

4.1 The program's error does not go away at the cell sizes in use: it falls more slowly than first order (12.3, 5.8, 3.6, 2.0 K for the half-cell shift at 20, 40, 80, 160 cells per side: ratios 0.47, 0.62, 0.57 per halving).

4.2 Every ingredient of the copy matters: at 40 cells per side and the half-cell shift (5.78 K) the physical conductivity in the edge term removes about half of the error (3.08 K), the distance of the strip about a quarter more (1.67 K), and the links through the aperture between the centroids the rest (-0.23 K); the copy is within 0.3 K at 40, 80 and 160 cells per side for every layout but the 45 degree turn (+0.7 and +0.5 K at 40 and 80).

4.3 The aligned board is itself not converged at 20 cells per side (90.86, 91.79, 91.47, 91.38 for the copy at 1, 0.5, 0.25, 0.125 mm): the comparison is to the aligned board **of the same cell**, which is the invariance test; the absolute error of the aligned board is the first column of section 5.

4.4 The residual of the copy at 45 degrees (+0.3 to +0.8 K) was split: board turned 45 with the part on the grid +0.26 K and part turned 45 on the aligned board +0.23 to +0.37 K at 0.5 and 0.25 mm. Not removed here. *Corrected by the review (section 9.3)*: the second share is not the discretisation of a turned source (the continuum effect of turning the part is -0.01 K, and an exact footprint on the same cells gives -0.03 K) but the 3D solid's sampling of the footprint on 4 x 4 points per cell, which keeps 97.4 % of the area of the turned part at 0.25 mm and puts the lost edge power in the centre; with 8 x 8 points (as the FVM samples it) the turned part reads +0.02 / +0.06 K instead of +0.37 / +0.23 K at 0.5 / 0.25 mm.

4.5 The program's FVM and FDM also depend on the position of the edge at 20 cells per side (FVM +4.6 K for the half-cell shift, FDM -0.6 K) and not at 80 (+0.22 K, -0.38 K): section 7.

## 5. The independent reference: a round board

A round board with a round part at its centre is axisymmetric, and every edge cell of a Cartesian grid is cut. `lib/axisym3d.py` solves it with its own finite volumes, rings times the **same slabs** the 3D solid builds (copper slab, four dielectric slabs with the program's in-plane and through conductivities, copper slab), the film on both faces everywhere and the film on the rim over every slab (half a ring of conduction in series). It imports nothing from the program's grids. Its tests (`tests/test_rotated_square.py`) compare it with the modified Bessel solution of a thin plate with a disc source (inside and outside the source), with the energy balance (heat to both faces and the rim = power, residual 1e-9) and with the series circuit of a whole-face source; the two ring counts (4000 and 2000) agree to the digit printed.

`scripts/study_disc.py`. 40 mm disc (a 128-sided polygon of the same area, in a 42 mm box), 2 W in a part of 3 mm radius, rise of the top copper at the centre in K (error against the reference):

| h_side | reference | program 1 mm | copy 1 mm | program 0.5 mm | copy 0.5 mm | program 0.25 mm | copy 0.25 mm |
| --: | --: | --: | --: | --: | --: | --: | --: |
| 10 | 95.16 | 94.89 (-0.3 %) | 94.85 (-0.3 %) | 95.10 (-0.1 %) | 95.09 (-0.1 %) | 95.15 (-0.0 %) | 95.14 (-0.0 %) |
| 100 | 76.96 | 78.11 (+1.5 %) | 76.79 (-0.2 %) | 77.88 (+1.2 %) | 76.95 (-0.0 %) | 77.52 (+0.7 %) | 76.96 (+0.0 %) |
| 1000 | 53.64 | 57.16 (+6.6 %) | 53.91 (+0.5 %) | 56.16 (+4.7 %) | 53.83 (+0.3 %) | 55.34 (+3.2 %) | 53.72 (+0.1 %) |
| 5000 | 48.14 | 50.95 (+5.9 %) | 48.42 (+0.6 %) | 50.06 (+4.0 %) | 48.33 (+0.4 %) | 49.42 (+2.7 %) | 48.22 (+0.2 %) |

![the disc against the axisymmetric reference](figures/fig_06_disc_against_axisymmetric.png)

*Figure 6 (`figures/fig_06_disc_against_axisymmetric.png`): error of the rise against the axisymmetric reference, program and copy, for three edge coefficients, against the cells across the disc.*

This is the check that the copy is **right** and not merely invariant: its absolute error is at most 0.6 % at the coarsest cell and falls with it, and the program's is 6 % high at 1000 W/m2K and falls slowly. At 10 W/m2K (the default) both are within 0.3 %.

## 6. Where the program was already right

`scripts/study_regression.py`, 1 mm cells.

| board | program | copy | difference (K) |
| :-- | --: | --: | --: |
| rectangle, no outline | 91.9190 | 91.9190 | +0.0000 (bit-identical: the copy changes only the outline branches) |
| rectangle given as an outline (grid lines) | 91.9190 | 91.9088 | -0.0102 |

The example board (100 x 80 mm, 22 W, vias, heatsink) cut to the five presets of the Board panel; the last column is the heat to the air over the power in the copy (energy balance).

| outline | h_side | FVM | 3D program | 3D copy | copy minus program (K) | heat / power, copy |
| :-- | --: | --: | --: | --: | --: | --: |
| ellipse | 10 | 90.75 | 90.91 | 90.90 | -0.01 | 1.0000 |
| ellipse | 100 | 86.10 | 86.73 | 86.35 | -0.38 | 1.0000 |
| L | 10 | 109.76 | 110.19 | 110.19 | -0.00 | 1.0000 |
| L | 100 | 101.39 | 102.43 | 102.43 | -0.00 | 1.0000 |
| T | 10 | 109.06 | 109.31 | 109.52 | +0.20 | 1.0000 |
| T | 100 | 99.70 | 100.57 | 100.68 | +0.11 | 1.0000 |
| chamfer | 10 | 86.44 | 86.60 | 86.60 | -0.00 | 1.0000 |
| chamfer | 100 | 82.95 | 83.29 | 83.24 | -0.05 | 1.0000 |
| rounded | 10 | 86.09 | 86.25 | 86.25 | -0.00 | 1.0000 |
| rounded | 100 | 82.69 | 83.03 | 82.98 | -0.05 | 1.0000 |

The only change above 0.2 K is the ellipse at 100 W/m2K (-0.38 K), where the copy moves towards the FVM. The T is +0.2 K at the default coefficient. The first explanation (cells with two edges at the re-entrant corners) was wrong, *review section 9.4*: the difference is the same with no edge loss at all; the part U1 hangs over the cut-away corner of the T, and the program and the copy give a cut cell the power of the part's cover of the whole cell, so the board part of the cell gets 1 / cover of the power density. Both are +2.2 to +2.4 K above the value at 2/3 mm, where the T falls on grid lines; the copy differs from the program there only because its centroid links react differently to that misplaced power (the L, the chamfer and the rounded board are on the program within 0.05 K). Energy is conserved in the copy (a first version leaked 22 % of the power into the cells taken as off the board through links of a sliver; fixed with a regression test, `test_cutcell_copy_closes_the_energy_balance_on_a_turned_square`).

## 7. The layered models

On the same boards the FVM and the FDM depend on the position of the edge much less than the 3D solid at the cells in use, and converge faster (section 4: FVM +4.6, +0.45, +0.22 K for the half-cell shift at 20, 40 and 80 cells per side; FDM -0.60, -1.24, -0.38 K). On the round board against the axisymmetric reduction of the layered model itself (`axisym3d.solve_layered_disc`, two nodes and the sheet conductance of each layer, as in `docs/theory.md`) both are within 0.6 % at 1 mm for 10 to 5000 W/m2K and within 0.1 % at 0.5 mm:

| h_side | layered reference | FVM 1 mm | FDM 1 mm | FVM 0.5 mm | FDM 0.5 mm | FVM 0.25 mm | FDM 0.25 mm |
| --: | --: | --: | --: | --: | --: | --: | --: |
| 10 | 94.71 | 94.33 (-0.4 %) | 94.32 (-0.4 %) | 94.59 (-0.1 %) | 94.61 (-0.1 %) | 94.67 (-0.0 %) | 94.67 (-0.0 %) |
| 100 | 75.52 | 75.18 (-0.5 %) | 75.18 (-0.5 %) | 75.43 (-0.1 %) | 75.44 (-0.1 %) | 75.50 (-0.0 %) | 75.49 (-0.0 %) |
| 1000 | 48.88 | 48.63 (-0.5 %) | 48.64 (-0.5 %) | 48.86 (-0.0 %) | 48.84 (-0.1 %) | 48.89 (+0.0 %) | 48.87 (-0.0 %) |
| 5000 | 43.11 | 42.85 (-0.6 %) | 42.89 (-0.5 %) | 43.09 (-0.0 %) | 43.08 (-0.1 %) | 43.13 (+0.0 %) | 43.11 (+0.0 %) |

The layered models and the 3D solid solve different idealisations (one node through the thickness against slabs with the FR-4 between the copper layers): at 1000 W/m2K the layered reference is 48.9 K and the 3D reference 53.6 K on the same round board. That difference (the heat has to cross the FR-4 to reach the edge slabs) is not a grid error and is not part of this question; it is why the table of this section is against the layered reference. Nothing is proposed for the FVM or the FDM.

## 8. Limits of the study

* Full copper on two layers, uniform conductivity per slab. Boards with patterned copper (zones with a fill per cell), vias and metal blocks were run only in the regression of section 6 (the example board: energy conserved, within 0.4 K of the program); the copy's links use the per-cell `kx` as the program does, but no patterned-copper board has an independent reference here.
* Steady state; the 3D solid has no time simulation. Boards with a block or a heatsink on the outline edge were not tried.
* The copy is a measurement tool (a text replacement of four expressions of `solid3d.py` executed in memory, `lib/rotsq.py`, which refuses to build if the source changed), not a proposed implementation; the cost of the 16 x 16 sampling per cell, and the way to write it vectorised in the program, are not measured (no timings are quoted).
* Single outline shape (squares, a round board, five presets of the example board); L-shaped and T-shaped boards were only run for the regression, with no reference.
* The independent reference of the study covered a round board only; for the shifted and turned squares the review added the continuum value of an independent quarter-board solver (section 9.2).
* The `+1.15 K` of the reviews was not re-run in its original setup (the board is not recorded there); section 2 reproduces its sign, size and dependence on the coefficient.

## 9. Review

Status: **reviewed**. Every table of sections 2 to 7 was re-run (`study_remeasure.py`, `study_edge_conductance.py`, `study_cut_cells.py --fine`, `study_disc.py`, `study_regression.py`) and printed the same numbers to the digit quoted. The code of the copies (`lib/rotsq.py`, `lib/cutcell.py`) was read against `pcbthermal/solid3d.py`: the four replaced expressions are the ones the text names, the copy is refused when the source changes, and it changes only the outline branches (the rectangle stays bit-identical). The independent reference `lib/axisym3d.py` was read (the same slabs, films on both faces and on the rim over every slab, no grid of the program); its docstring named a test file and a fin check that do not exist and was corrected.

### 9.1 What the review found

| # | finding | kind | where |
| :-- | :-- | :-- | :-- |
| R1 | The shifted and turned squares had no independent reference (only the invariance). Added: `lib/square3d.py` and `scripts/study_square_reference.py`; the copy is confirmed, the program's error against the continuum is slightly larger than its difference to the aligned board. | study, completed | 9.2 |
| R2 | The 45 degree residual was explained as the discretisation of a turned source. Wrong: it is the 3D solid's 4 x 4 sampling of the part's footprint (the FVM samples 8 x 8). | wrong explanation, corrected (4.4) | 9.3 |
| R3 | The +0.2 K of the T board was explained by cells with two edges. Wrong: a part that crosses the outline puts the power of a whole cell on the board part of a cut cell, in the FVM, the FDM and the 3D solid. A program defect, separate from A3, at the default coefficient. | program defect (finding, not edited) and wrong explanation, corrected (6) | 9.4 |
| R4 | "It does not go away with the cell" overstated: it falls by 0.5 to 0.6 per halving of the cell (4.1). | wording, corrected | answer |
| R5 | `research/REVIEW.md` had the row of this folder after the decision list, outside the table. | register, corrected | |
| R6 | The x ticks of figure 4 overlapped. | figure, corrected | |
| R7 | `lib/axisym3d.py` named a test file (`tests/test_axisym3d.py`) and a fin check that do not exist. | docstring, corrected | |

Checked and right: the claims of the question (1) to (4) as worded in the answer; the edge conductance ratios (0.70 to 0.73 at 1000, 0.62 to 0.68 at 5000 with the 10 degree rows of `out/edge_conductance.json`); the FVM edge term `h t L` equal to `h t P` at every angle; the energy balance of the copy (1e-9, test); the axisymmetric reference (Bessel to 0.2 %, series circuit to 1e-6, balance to 1e-9, 4000 and 2000 rings equal); the regression of section 6; the share of the cheaper variant P1a (5.78 -> 1.67 K at 40 cells per side, 71 %; 3.58 -> 1.43 K at 80, 60 %). Licence headers and Doxygen documentation pass `tests/test_license_header.py` and `tests/test_docs.py`; the documents carry no dates; no source is cited that was not opened (the cut-cell idea is attributed to no paper, as section 10 says).

### 9.2 An independent continuum value for the shifted and turned squares

A board and its part moved or turned together are the same continuum problem as the aligned board, so the continuum value of the aligned board is the answer of all of them. `lib/square3d.py` (imports nothing of the program) solves the aligned square on its quarter, with the same slabs and films, on cells the edge never cuts; on a 20 mm board at 1 mm cells it equals the program's rectangular branch to 1e-14 (test `test_square_reference_is_the_program_rectangle_on_cells_the_edge_does_not_cut`), it is the series circuit with insulated sides and converges as the square of the cell (test). The ladder (`scripts/study_square_reference.py`) to 1/32 mm and a Richardson step give:

| board | part | 0.5 mm | 0.25 mm | 0.125 mm | 0.0625 mm | 0.03125 mm | continuum |
| :-- | :-- | --: | --: | --: | --: | --: | --: |
| 20 mm, `h_side` 2000 | aligned | 91.822 | 91.477 | 91.382 | 91.357 | 91.351 | 91.349 |
| 20 mm, `h_side` 2000 | turned 45 (diamond) | 91.670 | 91.452 | 91.367 | 91.335 | 91.342 | 91.344 |
| 40 mm, `h_side` 100 | aligned | 91.919 (1 mm) | 91.898 | 91.889 | 91.886 | | 91.886 |
| 40 mm, `h_side` 1000 | aligned | 74.738 (1 mm) | 74.379 | 74.267 | 74.236 | | 74.226 |

(the 40 mm rows are at 1, 0.5, 0.25, 0.125 mm; energy balance 1.000000 everywhere). Against that value (K above it):

| cell | layout | program 3D | cut-cell copy | copy, part sampled 8 x 8 |
| --: | :-- | --: | --: | --: |
| 0.5 | aligned | +0.47 | +0.44 | +0.44 |
| 0.5 | shift 1/2 cell | +6.25 | +0.21 | +0.21 |
| 0.5 | turned 20 | +6.07 | +0.18 | +0.11 |
| 0.5 | turned 45 | +5.28 | +1.14 | +0.79 |
| 0.25 | aligned | +0.13 | +0.12 | +0.12 |
| 0.25 | shift 1/2 cell | +3.71 | +0.08 | +0.08 |
| 0.25 | turned 20 | +3.85 | +0.12 | +0.11 |
| 0.25 | turned 45 | +3.91 | +0.61 | +0.44 |
| 0.125 | aligned | +0.03 | +0.03 | +0.03 |
| 0.125 | shift 1/2 cell | +2.07 | +0.03 | +0.03 |
| 0.125 | turned 20 | +2.35 | +0.06 | +0.06 |
| 0.125 | turned 45 | +1.45 | +0.26 | +0.18 |

40 mm board of section 2 at 1 mm cells, against its continuum value (91.89 degC at `h_side` 100, 74.23 at 1000): program aligned +0.03 / +0.51 K, turned 20 (board and part) +1.09 / +3.41 K, board only turned 20 +1.31 / +3.63 K, turned 45 +1.78 / +3.37 K; the copy -0.29 to +0.38 K at 100 and +0.03 to +0.85 K at 1000 (+0.51 K with the 8 x 8 footprint at 45 degrees). The rise is about 67 K at 100 and 49 K at 1000, so the program's error on the turned square at 1 mm is 1.6 to 2.7 % at `h_side` 100 and about 7 % at 1000, the same size as the round board of section 5 (+1.5 % and +6.6 %).

![against the continuum](figures/fig_08_square_against_continuum.png)

*Figure 8 (`figures/fig_08_square_against_continuum.png`): the maximum temperature minus the continuum value of the independent solver, 20 mm board at `h_side` 2000, for the half-cell shift and the turns of 20 and 45 degrees, against the cells per side; program, cut-cell copy, the copy with the footprint sampled 8 x 8, and the aligned board (no cut cell) for scale.*

Reading: the copy reaches the continuum value from 40 cells per side for a shifted or turned straight edge (within 0.21 K), so section 4's invariance test was not hiding an offset; the program is 2 to 6 K above it at 40 to 160 cells per side. The 45 degree turn of the board keeps a residual in the copy (+0.44 / +0.18 K at 80 / 160 cells per side with the 8 x 8 footprint), first order in the cell: P1 does not remove everything.

### 9.3 The 45 degree residual (corrects 4.4)

`scripts/study_turned_part.py`. On a 20 mm rectangle (no outline, no cut cell) at `h_side` 2000 the 3D solid reads, part turned 45 minus part aligned: +0.37 / +0.23 / +0.11 K at 0.5 / 0.25 / 0.125 mm; the same with the footprint sampled on 8 x 8 points (variant `program_src8` of `lib/rotsq.py`): +0.02 / +0.06 / +0.03 K; the independent solver with a 16 x 16 footprint: -0.15 / -0.03 / -0.02 K; the continuum: -0.005 K. The 4 x 4 lattice keeps 94.4 / 97.4 / 98.9 % of the area of the turned 3 mm part at the three cells (8 x 8: 97.4 / 98.9 / 99.6 %; test `test_footprint_of_a_part_turned_45_degrees_is_short_on_4_by_4_samples`) (test `test_footprint_of_a_part_turned_45_degrees_is_short_on_4_by_4_samples`), and the power normalised over the shorter footprint lands nearer the centre. A program finding (3D solid only; small, and only on a turned part), recorded, not edited: `coverage_fraction(h.polygon, 4)` in `solid3d.py` where the FVM uses 8.

### 9.4 A part that crosses the outline (corrects 6; a program defect)

`scripts/study_part_across_outline.py`. The FVM (`fvm.py`, `cov = coverage_fraction(h.polygon, ...) * self.active`), the FDM and the 3D solid (`w = cover(h.polygon, 4) * self.active`) weight a board cell by the part's cover of the **whole** cell. Where the part crosses the outline, a cut cell gets the power of its whole area on its board part: the power density there is 1 / cover too high. The warning "x % of the footprint is outside the board; its full power is applied to the part that is inside" describes the intent, which is right in total but not in place. At the default `h_side` 10 W/m2K, maximum temperature in degC:

| board | cell (mm) | outline on grid lines | FVM | FVM, power on the board part | 3D solid | 3D, power on the board part |
| :-- | --: | :-- | --: | --: | --: | --: |
| small T (part over the re-entrant corner) | 1 | no | 233.08 | 230.84 | 234.27 | 231.96 |
| | 0.5 | no | 237.65 | 230.63 | 239.16 | 231.83 |
| | 1/3 | yes | 230.06 | 230.06 | 231.13 | 231.13 |
| | 0.25 | no | 230.46 | 229.82 | 231.56 | 230.90 |
| | 1/6 | yes | 229.96 | 229.96 | 231.03 | 231.03 |
| | 0.125 | no | 231.16 | 229.96 | 232.34 | 231.08 |
| | 1/12 | yes | 229.91 | 229.91 | | |
| example board cut to the T (U1 over the corner) | 1 | no | 109.06 | 107.56 | 109.31 | 107.79 |
| | 2/3 | yes | 106.85 | 106.85 | 107.08 | 107.08 |

Where the outline is on the grid lines no cell is cut and every rule agrees; where it cuts cells the program is +0.5 to +7.7 K above that value and does not converge monotonically, and the weight "part cover times board cover" (a one-line change per model, measured on copies: `rotsq.fvm_part_on_board`, variant `program_part_on_board`) brings it within 0.1 to 0.9 K. The example board cut to a T is +2.2 K in the FVM at 1 mm for this reason, so the FVM reference of `docs/validation.md` 13 (row "T, example", 109.1 degC) is about 2.2 K (2.6 % of the rise) high and the Lumped and Analytic errors of that row are measured against it. This is not part of A3 (it is not the edge term, and it is in the reference model at the default coefficient); the product of the two covers is exact only when one of the two covers the cell, a sample-wise intersection is the clean form. The copy's +0.2 K on the T is this power reacting to the centroid links, not a defect of the edge term.

### 9.5 Recommendation on A3 (asked by the maintainer)

* **How often**: the edge coefficient is typed (the computed coefficients leave it alone) and its default is 10 W/m2K; the effect needs an outline that is not on the grid lines **and** `h_side` of about 100 W/m2K or more (a board edge clamped to a chassis or a card guide). At 10 W/m2K the 3D solid moves by 0.3 K or less on every board measured (40 mm square, round board -0.3 %, five outline presets).
* **Size at the cells in use** (1 mm, 40 mm board): +1.1 to +1.8 K (1.6 to 2.7 % of the rise) at 100 W/m2K, +3.4 to +3.6 K (about 7 %) at 1000; round board +6.6 % at 1000, +3.2 % at 0.25 mm. Larger numbers (up to 12 K) need a small board (20 cells per side) at 2000 W/m2K.
* **The FVM is the reference and is adequate here**: on the same round board it is within 0.6 % of its own axisymmetric reference at 1 mm from 10 to 5000 W/m2K, and its edge term is exact in length. At high edge coefficients the 3D solid and the layered models differ by physics (48.9 against 53.6 K on the round board at 1000), so a user who needs the edge-clamped case reads the FVM and uses the 3D solid as the comparison it is.
* **Cost and risk of P1**: four rewritten expressions of `solid3d.py` (cover, links, edge term, conductivity), a sampling pass whose cost was not measured, every 3D number of an outline case and the tests that compare it move; a residual of 0.2 to 0.5 K stays at 45 degrees; patterned copper, vias and blocks on a cut edge have no independent reference. The gain is 1 to 4 K at 1 mm in a case the default does not reach, in a comparison model.
* **Recommendation: P2** (document the limit; no change of `solid3d.py`), with P1 kept in `docs/versions.md` ('Planned') as an option if a user case with edge cooling appears. Separately, and more worth doing than P1: **fix the power of a part that crosses the outline** (9.4) in the FVM, FDM and 3D solid on a `fix/` branch, because it reaches the reference model at the default coefficient (+2.2 K on the example board cut to a T) and is a one-line change per model; and, smaller, sample the footprint of a part 8 x 8 in the 3D solid as the FVM does (9.3). Text of the limit: `docs/for-the-project-documents.md`.

### 9.6 What the review did not verify

The 1/32 mm step of the diamond reference is not monotone (91.335 then 91.342: the 16 x 16 sampling of its footprint), so its continuum is good to about 0.01 K; patterned copper, vias and blocks on a cut edge against a reference; the FDM with the corrected part weight (only the FVM and the 3D solid were run); the cost of P1's sampling; the original +1.15 K setup.

## 10. What was read and what was not verified

* **No new external source was opened for this investigation.** The question is internal to the program's grid: the reference is the invariance of the continuum problem under a translation and a rotation, the modified Bessel solution of a thin plate with a disc source (used only to check `lib/axisym3d.py`; the formulas are the standard `I0, K0, I1, K1` solution, written from memory and checked numerically by the test to 0.2 %), and the series circuit. Nothing was added to `research/theory/BIBLIOGRAPHY.md`.
* **Read in full in the repository**: `pcbthermal/solid3d.py` (slab construction, links, edge term), `pcbthermal/geometry.py` (`edge_length_per_cell`, `edge_length_on_board`, `coverage_fraction`), `research/outline/README.md` (4.6), `research/outline/scripts/study_disc_reference.py` (the layered radial reduction, which `solve_layered_disc` repeats with its own constants), `docs/theory.md` as quoted in `CLAUDE.md`. The cut-cell finite-volume scheme (face apertures, centroid distances) is the standard idea of cut-cell methods; no paper was opened for it and none is cited.
* **Reproduced**: every table above by the script named in its section (outputs in `out/`, git-ignored); tests `tests/test_rotated_square.py` (12 tests: 9 of the study, 3 added by the review).
* **Not verified**: the original +1.15 K setup; patterned copper, vias and blocks against any reference; the 45 degree residual of the board turn (+0.2 to +0.4 K left with an 8 x 8 footprint, not removed); (the independent square, the T board and the turned part were checked by the review, section 9); whether the 16 x 16 sampling is the right resolution (the cover itself converges as 1/256; the sensitivity to `m` was not swept); the program's FVM and FDM at cells finer than 0.125 mm.
* **Defect in the investigation's own code, found and fixed**: the first cut-cell copy conducted heat into the cells taken as off the board (cover below 0.01) through the apertures of their faces: it lost 22 % of the power and read 4 K cool on a turned square at the finest cell; the apertures of cells off the board are now zero and a test checks the energy balance.
