# Young's omega for the SOR (S3) and a tile rule for the Analytic via correction (S4)

**Status: studies run, ready for review.** Every number below is copied from the output of the scripts of `scripts/` (run on this machine; the Markdown they print is in the git-ignored `out/`). Nothing was changed in the program: the proposals are in `INTEGRATION.md` with their measured impact.

**Summary.** S3: the Rayleigh bound of the Jacobi radius (one product with K, restricted to the linked nodes) gives an omega on the safe side of Young's optimum on every board tested, 2.8 to 11 times fewer sweeps than the program's formula on the ten boards of the program (2.8 on the example board), and meets the decision rule written before the runs; Lanczos, the power method and the adaptive estimate are not worth their cost. S4: with a tile equal to `min(1 mm, 0.75 d_nn)` (d_nn the nearest-neighbour distance of the vias, floor 0.25 mm) the Analytic via correction stays within 3.0 % (simple boards), 1.8 % (dense boards) and 4.2 % (4 to 576 vias) of the via effect of the fine-grid reference; the number of modes of G needs no rule; the Lumped well has no cheap fix for a lone via (limit and warning), and a macro cap of 0.75 passes the decision rule for the arrays and cuts the worst row error.

## 0. Questions

**S3 (Young's omega of the SOR).** `research/sor-with-via-couplings` found that the relaxation factor of the board without vias is 1.9613 against 1.8609 from the program's formula
`2 / (1 + sin(pi / n))` on the 3 x 3 array board, 6.0 times fewer sweeps, but it computed `rho_J` with an eigenvalue solver. Is there an estimate of the Jacobi spectral radius that is cheap
compared with the solve and robust on boards with vias, partial copper, outlines and many layers (power iteration, a few Lanczos steps, a closed form with the layer and via terms, a measured
fit, the decay of the SOR itself)? **Stop rule:** if the estimate needs a factorisation or as many matrix products as the solve costs, the item is dropped (the direct solver is the default and
SOR is a comparison solver; a change is recommended only if clearly worth it).

**S4 (tile of the Analytic via correction; the Lumped well).** `research/lumped-analytic-vias` proposed the self-term of the tile Green function with 1 mm tiles around vias (within 4 % everywhere
tested) but the result is sensitive to the tile (1.5 mm up to -40 %, 2 mm +21 %) and `G` is built from `min(M, 64)` modes (`M >= 2W/tile` is needed on large boards). Which automatic rule
for the tile (a function of the via radius, pitch, cell and board size) keeps the error small, where does it break, what does it cost in unknowns, and what of the Lumped well (the Krogh well per
plane; the known limits: a lone via or a row outside the footprint, 9 to 31 % of a small effect and ring dependent; dense arrays of open barrels 8 to 24 % under) can be fixed cheaply and what stays
a limit with a warning?

## 1. Situation (drawings)

![jacobi and sor](figures/fig_01_jacobi_and_sor_iteration.png)

*Figure 01, `fig_01_jacobi_and_sor_iteration.png`: left, the chain from K to the sweeps (where `rho_J` enters, where the estimate sits and what it costs); right, the red-black colouring of the stencil.*

![spectrum and omega curve](figures/fig_02_spectrum_and_omega_curve.png)

*Figure 02, `fig_02_spectrum_and_omega_curve.png`: left, the symmetric spectrum of the Jacobi matrix of the textbook plate (n = 42); right, the SOR radius against omega from Young's relation with `rho_J` = 0.999806 (README of `sor-with-via-couplings` 8.3), with the program's omega and Young's.*

![rayleigh and lanczos](figures/fig_03_rayleigh_and_lanczos_picture.png)

*Figure 03, `fig_03_rayleigh_and_lanczos_picture.png`: ILLUSTRATION on a 1D chain: the uniform trial vector against the dominant eigenvector of an unevenly cooled plate, and the Ritz values rising from below.*

![via lattice cell](figures/fig_04_via_lattice_cell_constriction.png)

*Figure 04, `fig_04_via_lattice_cell_constriction.png`: the cell of a via lattice: heat converging on the barrel in a plane, the section with the constriction in series with the barrel, and the closed-form profile.*

![tile grid](figures/fig_05_tile_grid_over_a_via_array.png)

*Figure 05, `fig_05_tile_grid_over_a_via_array.png`: a 5 x 5 array under the program's tiles and under 1 mm tiles; right, a source edge on a tile line and across a tile.*

![krogh well in the rings](figures/fig_06_krogh_well_in_the_lumped_rings.png)

*Figure 06, `fig_06_krogh_well_in_the_lumped_rings.png`: the rings of the Lumped model, a lone via outside the footprint in one ring, and the well per plane in series with the barrel.*

![green function chain](figures/fig_07_tile_green_function_chain.png)

*Figure 07, `fig_07_tile_green_function_chain.png`: the chain of the Analytic correction and where the tile and the 64 modes act.*

The formulas are in `docs/theory-text.md`.

## 2. S3 results: Young's omega

Tables are the scripts' output, shortened to the columns that carry the argument (the full printed tables are reproduced by the commands of section 6).

![sweeps against omega](figures/fig_08_sweeps_against_omega.png)

*Figure 08, `fig_08_sweeps_against_omega.png`: measured sweeps of an independent red-black SOR against omega on a 4-layer plate, the asymptotic rate from Young's relation, the program's omega and Young's.*

![lanczos error](figures/fig_09_lanczos_error_against_steps.png)

*Figure 09, `fig_09_lanczos_error_against_steps.png`: error of 1 - rho_J of Rayleigh and Lanczos against the steps, even and uneven losses.*

![estimate error by board](figures/fig_10_estimate_error_against_board_type.png)

*Figure 10, `fig_10_estimate_error_against_board_type.png`: error of every estimate on the boards of the program.*

![cost of the estimate](figures/fig_11_cost_of_the_estimate.png)

*Figure 11, `fig_11_cost_of_the_estimate.png`: seconds of the estimate against the solve and the sweeps, with the grid.*

**2.1 Textbook case** (`study_s3_exact.py` A). Poisson matrix, fixed edges, n = 6, 8, 10, 12: the eigenvalues give `rho_J = cos(pi/(n+1))` (0.900969, 0.939693, 0.959493, 0.970942), Young's `omega_opt` = 1.3948, 1.4903, 1.5604, 1.6138
equals `2/(1+sin(pi/(n+1)))` to four digits, and the dense SOR iteration matrix at n = 8 has radius 0.490291 at 1.4903 and 0.883022 / 0.822946 / 0.703189 / 0.500000 / 0.700000 / 0.900000 at omega 1.0 / 1.2 / 1.4 / 1.5 / 1.7 / 1.9, identical to
Young's relation to six digits (the dense matrix uses nothing of the relation). The program's formula `2/(1+sin(pi/n))` is that optimum for a plate with *fixed edges* and the node count as n (1.3333 against 1.3948 at n = 6): a plate that loses heat only at its edges. A cooled
board has `rho_J` set by its loss `a`, so the formula is below the optimum, on the safe side but slow (section 2.4).

**2.2 Exact cases** (B). Periodic plate with uniform loss: `rho_J = 4g/(4g+a)` agrees with the eigenvalues to 8 digits on four tori (0.97560976 at 16 x 16, a = 0.1, to 0.99997500 at 64 x 64, a = 1e-4) and the Rayleigh bound with one product is
exact there (the trial vector is the eigenvector); `omega_opt` 1.64000 to 1.98596.

**2.3 Plates of the program's stencil** (C, relative error of 1 - rho_J, positive = safe side):

| plate | Rayleigh | Lanczos 3 | Lanczos 10 | Lanczos 20 | power 200 |
| :-- | --: | --: | --: | --: | --: |
| 1 to 6 layers, even loss | +0.01 % | +0.00 to +0.01 % | +0.00 % | +0.00 % | +0.00 % |
| one face only | +0.72 % | +0.12 % | +0.00 % | +0.00 % | +0.00 % |
| patch-cooled (heatsink-like) | +9.45 % | +6.11 % | +2.17 % | +0.31 % | +1.43 % |
| edge-cooled (edge column only) | +70.25 % | +56.93 % | +34.05 % | +15.88 % | +29.01 % |

Where the loss is not uniform the uniform trial vector is a poor eigenvector and every estimate converges slowly; it never overshoots (it is a Rayleigh quotient, a lower bound, for a matrix with non-negative entries). The power method on `J_s` itself oscillates in sign
(the spectrum is symmetric): 200 products gave +0.242 and 800 gave -0.832 on the 4-layer plate (error of rho_J, exact 0.999570), the iteration on `(I + J_s)/2` reaches 0.997831 after 800 products; Lanczos with a random start 0.997918 after 50. So the power method needs
hundreds of products and a shifted matrix; it is not proposed.

**2.4 Sweeps against omega** (D, the same plates, independent red-black SOR, tol 1e-9): program 1450 to 3380 sweeps against 390 to 820 at Young's omega (3.7 to 4.1 times), equal for Rayleigh on the even-loss plates; on the uneven plates program / Young / Rayleigh / Lanczos 8 =
4650 / 690 / 1250 / 1070 (edge-cooled) and 11650 / 1100 / 1330 / 1200 (patch-cooled): the Rayleigh estimate needs 1.2 to 1.8 times the sweeps of Young's optimum there but still 3.7 and 8.8 times fewer than the program's.

**2.5 The boards of the program** (`study_s3_boards.py` part 1; the point treatment of the vias, pure stencil; tolerance 1e-9; sweeps at the program's omega, Young's exact omega, Rayleigh, Lanczos 10, the adaptive one and the measured best):

| board | cell mm | N | rho_J | program | Young exact | Rayleigh | Lanczos 10 | adaptive | measured best |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| plate 1 layer 40 mm | 1.0 | 4800 | 0.999650 | 2362 | 505 | 541 | 505 | 570 | 463 |
| plate 2 layers | 1.0 | 3200 | 0.999814 | 4425 | 692 | 692 | 692 | 900 | 670 |
| plate 4 layers | 1.0 | 6400 | 0.999908 | 8845 | 983 | 998 | 983 | 1480 | 915 |
| plate 6 layers | 1.0 | 9600 | 0.999939 | 13359 | 1212 | 1236 | 1212 | 1260 | 1209 |
| plate 4 layers, forced air h = 50 | 1.0 | 6400 | 0.999546 | 1748 | 429 | 457 | 429 | 470 | 392 |
| 4 layers + 5 x 5 vias (point) | 0.5 | 25600 | 0.999977 | 18392 | 2024 | 2054 | 2024 | 2010 | 1777 |
| partial copper 4 layers | 1.0 | 6400 | 0.999876 | 6623 | 848 | 877 | 862 | 1250 | 811 |
| round board 40 mm | 1.0 | 3200 | 0.999814 | 4459 | 696 | 696 | 696 | 920 | 674 |
| example board 2 mm | 2.0 | 8000 | 0.999466 | 1149 | 390 | 406 | 392 | 410 | 363 |
| example board 1 mm | 1.0 | 32000 | 0.999860 | 2247 | 781 | 812 | 787 | 790 | 728 |

The Rayleigh bound needs 2.8 (example board) to 11 (6 layers) times fewer sweeps than the program's formula and needs 0 to 7 % more sweeps than the exact Young's. Error of 1 - rho_J of the Rayleigh bound on these boards: +0.00 % (2 layers, round board) to +2.26 % (1 layer), +1.16 / +1.17 % on the example board; every entry non-negative (safe side). Lanczos 10 brings it to +0.00 to +0.44 % (+0.13 / +0.22 % on the example), which saves 2 to 7 % of the sweeps and costs 10 products (5 sweeps' worth by
the two-product count of the script). The omega of the adaptive estimate (from the decay of the SOR iteration itself) is above the optimum on several boards (for example 1.9757 against 1.9621 on the 2-layer plate, 900 against 692 sweeps) and is never better than Rayleigh by more than 1 %: not proposed.

**Defect found in this study and fixed.** The first Rayleigh bound summed over every node. On the round board the cells off the outline are pinned to the ambient and decoupled (no link), so they are eigenvectors with mu = 0 and dilute the quotient: the error of 1 - rho_J was +436 641 % and omega 1.009. `young.rho_rayleigh` now sums
only the nodes with a link (`linked_only=True`); the column "Rayleigh all nodes" of the study keeps the old behaviour for comparison and `test_rayleigh_ignores_decoupled_nodes` fails on the old code. The same applies to the closed form from the totals (`g_amb.sum()` and the diagonal sum): it collapses on a board with an outline (the same +436 641 % in the printed table), so the proposal uses the masked
Rayleigh product, not the totals.

**2.6 With the mean-potential vias, block SOR** (`study_s3_boards.py` part 2, the block SOR of `sor-with-via-couplings`). The stencil part of K has `rho_J` of 0.999452 / 0.999652 / 0.999787 on the 3 x 3 array, the 5 x 5 array and the example board, but the full K has 0.999977 / 0.999977 / 0.999860 (the via couplings make the
board much stiffer to iterate): an omega from the stencil part is far from the optimum. Omega / sweeps:

| board | program | Young (stencil) | Lanczos 10 (stencil) | Young (full K) | Lanczos 10 (full K) | Rayleigh (full K) | measured best |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| 3 x 3 array, 0.5 mm | 1.8609 / 34530 | 1.9359 / 15730 | 1.9337 / 16290 | 1.9864 / 1960 | 1.9864 / 1970 | 1.9864 / 2010 | 1.9866 / 1960 |
| 5 x 5 array pitch 1.2, 0.5 mm | 1.9005 / 23810 | 1.9486 / 12250 | 1.9347 / 15600 | 1.9865 / 1890 | 1.9865 / 1890 | 1.9865 / 1940 | 1.9871 / 1940 |
| example board 1 mm | 1.9391 / 2250 | 1.9596 / 1320 | 1.9546 / 1560 | 1.9671 / 780 | 1.9670 / 790 | 1.9669 / 810 | 1.9694 / 740 |

With the Rayleigh bound of the **full** K the block SOR needs 17.2, 12.3 and 2.8 times fewer sweeps than the program's formula, and at most 9.5 % more than the measured best (2010 against 1960, 1940 against 1940, 810 against 740). The full K has positive entries inside a footprint, so its Jacobi matrix is not non-negative and Young's relation is not guaranteed there: this rests on three boards
only (the measured sweeps decide, not the theory), and the proposal must be checked on more boards when the block SOR is implemented.

**2.7 Cost** (part 3, 2-layer plate, tol 1e-9; seconds on this machine):

| grid | N | omega_opt | sweeps program / Young | Rayleigh s | Lanczos 10 s | direct s | SOR with Young s |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| 40 x 40 x 2 | 3200 | 1.9621 | 4425 / 692 | 0.0006 | 0.001 | 0.007 | 0.04 |
| 80 x 80 x 2 | 12800 | 1.9624 | 2143 / 678 | 0.0008 | 0.001 | 0.027 | 0.13 |
| 120 x 120 x 2 | 28800 | 1.9624 | 1304 / 668 | 0.0028 | 0.006 | 0.109 | 0.38 |
| 160 x 160 x 2 | 51200 | 1.9625 | 751 / 661 | 0.0035 | 0.007 | 0.211 | 0.54 |

On the ten boards the Rayleigh bound takes 0.0004 to 0.0017 s (one product; under 1 % of the SOR seconds it saves, 0.1 to 6 s). The program's formula gets closer to the optimum as the grid refines (its `n` grows while `rho_J` of a plate with a fixed loss stays at 0.99982): the gain
is 6.3 times at 40 x 40 and 1.2 at 160 x 160. The direct solve is faster than the SOR with Young's omega on every board (0.147 s against 0.72 s on the 5 x 5 board), which is the reason SOR stays a comparison solver.

**2.8 Decision rule (written before the runs) against the numbers.** (a) lower bound or within 1 % of 1 - rho_J on every board: the Rayleigh bound is a lower bound on every case of 2.3 to 2.6 (met); Lanczos 10 is within 0.44 % on the boards of the program. (b) cost under 5 % of the sweeps it saves: under 1 % (met). (c) SOR no slower than the program's on every
board: 10 of 10 boards, the plates of 2.4, the 160 x 160 plate (Young's; Rayleigh not run on the scaling plates) and the three block-SOR boards (met). **The Rayleigh bound with the linked-node mask is the estimate to adopt if the maintainer wants the item; Lanczos, power method and adaptive estimate are dropped.** The result of the solve does not change (the stopping rule is the residual); only the sweeps do.

## 3. S4 results: tile rule and the Lumped well

![error against the tile](figures/fig_12_error_against_the_tile.png)

*Figure 12, `fig_12_error_against_the_tile.png`: error of the Analytic via effect against the tile on the unit cells and the simple boards.*

![tile rules](figures/fig_13_tile_rules.png)

*Figure 13, `fig_13_tile_rules.png`: the tile each rule chooses against the nearest-neighbour distance, and mean / maximum error of every rule.*

![modes](figures/fig_14_modes_against_board_size.png)

*Figure 14, `fig_14_modes_against_board_size.png`: modes of the tile Green function against the board size.*

![cost against vias](figures/fig_15_cost_against_the_number_of_vias.png)

*Figure 15, `fig_15_cost_against_the_number_of_vias.png`: unknowns, seconds and memory of the correction against the number of vias.*

![error against vias](figures/fig_16_error_against_the_number_of_vias.png)

*Figure 16, `fig_16_error_against_the_number_of_vias.png`: error of the via effect against the number of vias, Lumped and Analytic, before and after (grey band: 5 %).*

![lumped lone via](figures/fig_17_lumped_lone_via_against_distance_and_rings.png)

*Figure 17, `fig_17_lumped_lone_via_against_distance_and_rings.png`: Lumped lone via, error against the distance and the number of rings.*

![copper fill gain](figures/fig_18_copper_fill_gain_example_board.png)

*Figure 18, `fig_18_copper_fill_gain_example_board.png`: copper-fill gain of the example board and its denser arrays in every model.*

The reference is the fine-grid layered solver `resolved_boards.full_board_2d` (barrels drawn at their real size, 1/16 mm grid, 1/8 mm on boards above 60 mm; 0.05 mm on the dense set). "Error" is the error of the *via effect* (the drop of the maximum temperature the vias produce), not of the total.

**3.1 Unit cell** (`study_s4_tile.py` 1; lattice, 2 layers, 0.3 mm drill, copper fill; percent):

| pitch mm | E_ref K | closed form with Krogh wells | Analytic, program | tile 0.5 | tile 1.0 | tile 2.0 | tile 2.5 |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| 0.8 | 7893.87 | +0.0 | +0.2 | -0.1 | -0.1 | -0.1 | -0.1 |
| 1.5 | 2181.09 | +0.1 | +1.4 | +0.0 | -0.3 | -0.3 | -0.3 |
| 3.5 | 329.94 | +0.8 | +1.8 | -0.0 | -0.4 | -1.3 | -1.3 |
| 5.0 | 129.16 | +1.6 | +5.6 | -0.1 | -0.1 | -0.3 | -1.9 |
| 8.0 | 29.97 | +4.1 | +34.9 | -0.1 | -0.4 | -1.0 | -1.0 |

The one-cell closed form (Krogh well in series with the barrel) reproduces the fine grid to 0.0 to 4.1 %; the program's Analytic is 34.9 % off at 8 mm pitch, and every tile of 0.4 to 2.5 mm is within 1.9 % on the lattice (the cell has no source edge to meet).

**3.2 Simple boards** (part 2; 64 modes against 2 per tile: identical within 0.2 points at the tiles shown; at the tile 0.4 mm, not shown, the 2-per-tile series is 2.3 points worse on the lone via):

| board | tile 0.5 | 0.75 | 1.0 | 1.25 | 1.5 | 2.0 | 2.5 |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| lone via 2 mm from the source | -4.2 | -3.6 | -3.0 | -35.0 | -39.7 | -5.4 | -54.9 |
| lone via 4 mm | -3.7 | -3.3 | -2.7 | -1.9 | -1.1 | -4.0 | +2.9 |
| row of 5, pitch 1.5 | +0.3 | +0.6 | +1.0 | +1.1 | +5.5 | +9.0 | +8.1 |
| 3 x 3 pitch 3.5 | -0.4 | -0.6 | -0.2 | -0.9 | -2.5 | -1.6 | -1.0 |
| 3 x 3 pitch 1.0 | +0.0 | +1.0 | -0.4 | +3.9 | -4.9 | +21.3 | -6.6 |
| pad 5 x 5 pitch 1.2 | -0.8 | -2.3 | -2.2 | -0.2 | -0.9 | -7.5 | +0.2 |

The error jumps with the tile (a source edge falling on a tile line or across a tile, figure 05): -35 % at 1.25 mm and -55 % at 2.5 mm for a lone via 2 mm from the source. A tile of 1 mm or less is within 5 % everywhere; the sensitivity of the earlier review (1.5 mm up to -40 %, 2 mm +21 %) is reproduced.

**3.3 Modes against board size** (part 3; 5 x 5 pad, pitch 1.2 mm; the series needs M = 300, and 408 at 100 mm with 2 modes per tile at the 0.5 mm tile):

| board mm | tile 0.5: 64 modes | 1 W/t | 2 W/t | tile 1.0: 64 modes | 2 W/t |
| :-- | --: | --: | --: | --: | --: |
| 30 | -0.82 | -0.82 | -0.92 | -2.21 | -2.21 |
| 60 | -0.58 | -0.94 | -1.05 | -2.54 | -2.55 |
| 100 | -0.62 | -0.99 | -1.10 | -2.54 | -2.62 |

Going from 64 modes to 2 per tile changes the error by at most 0.5 points (at 100 mm it is slightly worse); the cap of 64 modes of G is not what limits the accuracy on these boards, and no mode rule is proposed (the decision rule asked for an error that more modes remove: there is none).

**3.4 Rules** (`study_s4_rule.py`; mean / maximum absolute error of the via effect, percent; the tile each rule chose is in the printed table):

| rule | simple (16 boards) mean / max | dense (10 boards) mean / max |
| :-- | --: | --: |
| program tile (5 mm) | 4.7 / 15.9 | not run |
| fixed 1 mm | 0.8 / 3.0 | 1.0 / 6.3 |
| **cap 1 mm / 0.75 d_nn** | **0.8 / 3.0** | **0.4 / 1.8** |
| 0.5 d_nn | 1.7 / 6.8 | 0.3 / 1.0 |
| 0.75 d_nn | 2.5 / 9.1 | 0.4 / 1.8 |
| 1.0 d_nn | 2.5 / 8.8 | 0.6 / 2.1 |
| 6 a | 0.8 / 4.9 | 0.4 / 1.8 |
| 8 a | 0.9 / 4.9 | 0.6 / 2.6 |
| 10 a | 2.4 / 22.7 | 1.3 / 10.6 |

(a the drill radius; a multiple of the radius sets the tile with no regard to the pitch; the script's automatic pick by lowest mean over both sets is 6 a, tied at the printed precision with the cap rule, whose maximum is lower on the simple boards: 3.0 against 4.9 %.) The rules that follow the pitch only
(0.5 to 1.0 d_nn) have no cap for a lone via or a wide pitch and fail where the tile grows to 2.6 or 3.5 mm (9.1 and 8.8 %); the fixed 1 mm fails on the dense pad of pitch 0.6 mm (+6.3 %, the tile is larger than the spacing); the cap rule `tile = min(1 mm, 0.75 d_nn)` is the simplest that is at or near the best on both sets. **The floor** (0.25, 0.4 and 0.6 mm, tested with the rule 6 a, tiles 0.47 to 1.87 mm) changes only the drill-0.2 board (tile 0.47 to 0.60 mm, error -0.1 to -0.0 %); the floor of 0.25 mm is a guard, not a tuned value, and was not exercised.

**3.5 Where the rule breaks** (dense set): pitch 0.6 to 1.0 mm with the 0.3 mm drill and drills 0.2 to 0.8 mm at pitch 1.5 stay within 1.8 % (+0.7 to -1.8). A unit cell of pitch 0.45 mm was dropped from the plan after the first quick run failed with a ZeroDivisionError in the reference builder for a case (not investigated); nothing below 0.6 mm was tested.

**3.6 Many vias and cost** (`study_s4_arrays.py`; full copper, four layers, copper-filled barrels, source over the array; error of the via effect, percent; the rule is the cap rule):

| vias | pitch mm | E_ref K | Analytic program | Analytic fixed 1 mm | Analytic rule | Lumped program | Lumped proposal (cluster) |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| 4 | 2.0 | 22.15 | +24.0 | -2.1 | -2.1 | +28.3 | +6.0 |
| 25 | 2.0 | 19.41 | +0.3 | -1.6 | -1.6 | +11.8 | +2.8 |
| 400 | 2.0 | 16.13 | +4.0 | -0.7 | -0.7 | +13.7 | -53.8 |
| 4 | 1.0 | 30.76 | +0.8 | -4.9 | -4.2 | +12.8 | -5.0 |
| 100 | 1.0 | 33.00 | +2.9 | +0.0 | +0.1 | +5.9 | -1.2 |
| 576 | 1.0 | 45.27 | +1.9 | +0.1 | +0.2 | +9.1 | +1.5 |
| 4 | 3.5 | 13.28 | +35.3 | -0.5 | -0.5 | +56.3 | +18.8 |
| 100 | 3.5 | 6.76 | +18.3 | -0.3 | -0.3 | +23.6 | +8.9 |

All 17 rows are in the script's table. The Analytic with a tile (fixed or rule) is within 4.9 % on every one (maximum 4.9 % fixed, 4.2 % rule), the program's within 35.3 %; the Lumped program is 5.0 to 56.3 % high and the cluster proposal is within 8.9 % except at pitch 2.0 with 100 to 400 vias (-32.3 to -53.8 %) and 4 vias at 3.5 mm
(+18.8 %). Cost of the Analytic correction (tile mm / unknowns of the dense system / seconds / peak MB): 4 vias 1.00 / 64 / 0.24 / 36; 100 vias at 2.0 mm 1.00 / 1600 / 0.59 / 141; 225 vias 1.00 / 3600 / 2.06 / 573; 400 vias at 2.0 mm 1.15 / 6400 / 3.96 / 1029 (the tile grows from 1.00 to 1.15 mm under the program's coarsening of the active tiles);
576 vias at 1.0 mm 1.04 / 6400 / 1.33 / 256 against 1.18 / 4900 / 0.91 / 165 with the fixed 1 mm and 0.29 s for the program's own. The rule costs the same as fixed 1 mm for pitch above 1.33 mm; at pitch 1.0 mm the tile is 0.75 mm, 1.3 to 1.9 times the seconds and up to 2.1 times the memory (for example 225 vias: 0.68 against 0.37 s, 165 against 78 MB).
The dense matrix grows as the square of the unknowns: 1 GB at 6400.

**3.7 The example board** (`study_s4_example.py`; change of the maximum temperature from the open via, K; the open-board maximum is 85.81 degC FVM 1 mm, 85.15 degC FVM at 0.25 mm, 83.54 Lumped, 84.69 Analytic, 85.22 Analytic with the tile):

| row | FVM 1 mm | FVM 0.25 mm | Lumped program | Lumped cluster | Analytic program | Analytic fixed 1 mm | Analytic rule |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| conductive paste | -0.20 | -0.19 | -0.28 | -0.20 | -0.25 | -0.19 | -0.19 |
| copper | -4.49 | -4.20 | -6.79 | -4.47 | -6.32 | -4.27 | -4.27 |
| no vias | +8.86 | +9.57 | +11.15 | +9.25 | +10.02 | +9.50 | +9.50 |

The copper-fill gain of the program's Lumped and Analytic (6.79 and 6.32 K) falls to 4.47 and 4.27 K, within 0.27 K of the FVM at 0.25 mm (4.20 K); the rule and the fixed tile give the same number here (the pitch is 3.5 mm, the tile 1 mm). Denser arrays on the example board (gain / open effect, K): 5 x 5 at 1.2 mm
FVM at 0.25 mm 2.27 / 18.24, Analytic rule 2.30 / 18.35, Analytic program 4.78 / 16.24, Lumped cluster 2.59 / 12.81 (the Lumped proposal underestimates the open effect by 30 %); 7 x 7 at 1.0 mm 0.97 / 21.32, Analytic rule 0.97 / 21.16, Lumped cluster 1.96 / 16.22 (24 % under). The FVM at the program's 1 mm cell over-states the gain of a dense array by 34 to 87 %
(3.05 against 2.27 K and 1.81 against 0.97 K): the cause is not established here (the vias are point sinks at that cell; see `point-via-convergence`), and nothing is corrected.

**3.8 The Lumped well** (`study_s4_lumped.py`; error of the via effect, percent). Lone via (3 mm source, 30 mm board, copper fill): the program is +29.8 to +286.6 % high; the proposed cluster well is -21.6 to +65.3 % at 10 rings and depends on the ring count at the same distance (for example at 4.0 mm: +15.5, -9.8, +6.4, +2.7 for 6, 10, 16, 24 rings; at 10 mm: -5.0, +65.3, +51.0, +21.5).
The micro ring, micro nn and the zones variant of `lumped-via-groups` give the **same number** as the cluster at every distance and ring count, and the lone caps 1, 2 and 3 differ by at most 6 points (at 6 rings, 6 to 10 mm): a lone via contributes at most 3.5 % of the source rise from 3 mm on (0.4 % at 10 mm), so the model error shows up only as a ring artefact. Distance of the via from the footprint edge: error +0.1 % at 0 mm (inside the footprint
rings), -1.0 % at 1.0 mm, then -9.8 to -21.6 % at 0.5, 1.5, 2.5 and 3.5 mm, +6.1 % at 4.5 mm, +11.5 % at 6.5 mm and +65.3 % at 8.5 mm. No cap or scale factor removes this: **it stays a limit, with a warning** for a via outside every footprint.

Rows (1 mm gap, 16 mm board, pitches 1.0 and 1.5): the program is +49 to +104 % high; the cluster well is -10.4 (1 via), +15.4 / +5.9 (2), within 5 % only at 3 vias (pitch 1.5, +1.4 %) and 5 vias (+3.7 and -2.8 %), and **-36.3 % and -50.7 % at 9 vias**; with the macro cap of 0.75 the 9-via rows become -1.9 % and -7.8 %, the 7-via -15.7 / -32.0 become +2.5 / +6.5,
but the 5-via rows get worse, +8.2 and +12.1 instead of +3.7 and -2.8; the largest row error falls from 50.7 to 15.4 %.
Dense arrays (copper fill): the program is +6.2 to +54.1 % high; the cluster well is +0.9 / +2.6 (3 x 3 at pitch 3.5 open / Cu), -21.2 / -13.0 (pitch 1.0) and -4.4 to -7.4 % on the 5 x 5 pads; with the macro cap 0.75 the largest is 8.6 % (+0.9, +2.6, -7.3, +8.6 on the 3 x 3, -2.1 to -6.2 on the 5 x 5 pads). The scale factors (macro x0.5, x1.5, all x0.8, all x1.2) move the error by up to 23 points, in either direction: no single factor helps the three families, so they are not proposed.
The zones variant of `lumped-via-groups` is better on dense arrays (within 5.4 % on all eight) and equal to the cluster for the lone via and the rows.

**Decision rule (written before the runs) against the numbers.** (i) Tile rule: every simple board within 5 % of the via effect (3.0 % cap rule, 4.2 % on the arrays; the fixed 1 mm tile is also within 5 % on these), no tile constant for the user (met; the 0.75 and the 1 mm are fixed numbers in the code), cost no more than fixed 1 mm **(met except at pitches below 1.33 mm, where the rule uses 1.3 to 1.9 times the time and up to 2.1 times the memory,
and the fixed 1 mm is 6.3 % off on the 0.6 mm pad)**; the mode rule: not added. (ii) Lumped fix: the macro cap of 0.75 passes for the arrays (no array error rises by more than 3 points in absolute value; the worst falls from 21.2 to 8.6 %) and cuts the worst row error (50.7 to 15.4 %) at the price of worse 5-via rows (+8.2 / +12.1 %); the lone-via errors
are not cut by any cap: they stay a limit with a warning.

## 4. Limits

* **S3.** The Rayleigh bound is 70 % off in 1 - rho_J on a plate cooled only at its edge column (omega 1.9547 against 1.9651, 1250 sweeps against 690) and 9.5 % on a patch-cooled plate: the omega is safe but not optimal, still 3.7 to 8.8 times fewer sweeps than the program's. The block SOR result (2.6) rests on three boards and a full K that is outside Young's theory. The measured sweeps are for tolerance 1e-9 on the residual; the times are of this machine; the direct
  solver is faster than any SOR on every board tested.
* **S4.** The reference is a 2D layered model with the barrels drawn at their size; it is not a 3D solver or a measurement (no published via-array case was obtained, see the last section). The tile rule was chosen on the 26 boards of the rule study (pitches 0.6 to 8 mm, one drill and one copper-fill family in most) and checked on the 17 boards of the array study, not on a set kept apart from the choice; arrays below 0.6 mm pitch are untested; boards without vias are unchanged (the rule is not called). The sensitivity to the tile remains (a bad tile gives -55 %): the rule keeps the tile in the region
  that was measured to be safe. The Lumped well remains uncorrectable for a lone via or a row beyond 2 to 3 mm from the footprint (warning), and the proposal under-estimates the open effect of dense arrays under a footprint by 24 to 30 % on the example board (3.7).

## 5. Independent references

* S3: the textbook Poisson matrix and Young's theory (Saad 2003, section 4.2.5); the dense eigenvalues and the dense SOR iteration matrix (nothing of Young's relation used); `young.sor_rb_matrix`, a red-black SOR written from the matrix alone, against the program's `solve_sor` (test).
* S4: the fine-grid layered solver `resolved_boards.full_board_2d` (the layered model of the program with the barrels drawn at their real size; nothing of the program imported), the one-cell closed form with Krogh wells, the axisymmetric and Cartesian references and the 3D solver `tests/helpers/layered3d.py` of `lumped-analytic-vias` where a case needs them.

## 6. Reproducing (from the repository root; run times on this machine: `study_s3_exact.py` 40 s, `study_s4_tile.py` 40 minutes, `study_s4_arrays.py` 19 minutes, `study_s4_example.py` 2 minutes, the others from seconds to minutes; the fine-grid references dominate; results go to the git-ignored `out/`)

```
.venv/bin/python -m pytest -q research/young-omega-tiles/tests
.venv/bin/python research/young-omega-tiles/scripts/study_s3_exact.py
.venv/bin/python research/young-omega-tiles/scripts/study_s3_boards.py [--quick]
.venv/bin/python research/young-omega-tiles/scripts/study_s4_tile.py [--quick]
.venv/bin/python research/young-omega-tiles/scripts/study_s4_rule.py [--quick]
.venv/bin/python research/young-omega-tiles/scripts/study_s4_arrays.py [--quick] [--rule cap_nn|fixed|nn_radius]
.venv/bin/python research/young-omega-tiles/scripts/study_s4_example.py [--rule ...]
.venv/bin/python research/young-omega-tiles/scripts/study_s4_lumped.py [--quick]
.venv/bin/python research/young-omega-tiles/scripts/make_diagrams.py
.venv/bin/python research/young-omega-tiles/scripts/make_figures.py
```

## What was read and what was not verified

* **Read (R)**: Saad, *Iterative Methods for Sparse Linear Systems* (2nd ed.), sections 4.1 and 4.2 including Theorems 4.10 and 4.16 and eq. 4.47 (read in the folder `sor-with-via-couplings` and relied on here); Saad, *Numerical Methods for Large Eigenvalue Problems* (revised ed.), section 4.1.1 (power method, Algorithm 4.1, Theorem 4.1, printed pp. 86-87) and section 6.6 (Lanczos convergence, Theorems 6.3 and 6.4, printed pp. 147-150): open copies of the author, extracted to text in the scratch area, nothing stored in the repository (`research/theory/BIBLIOGRAPHY.md` section 20). The README, INTEGRATION and review chapters of `sor-with-via-couplings` and `lumped-analytic-vias`, `pcbthermal/fvm.py` (`solve_sor`) and `pcbthermal/analytic.py` (the tile and the correction).
* **Not obtained (N)**: Young (1971), Varga (1962), Hageman and Young (1981): the adaptive estimate here is our own use of Young's relation, not their algorithm; no published numerical case of a via-array constriction.
* **Run in this folder**: all the studies of section 6 (the S3 tables, the S4 rule, tile, arrays, example and Lumped tables) and the 24 tests of `tests/` (pass), once each, on one machine; the numbers are the printed ones. No repeat of any study on another machine.
* **Not verified**: no measurement and no published via-array case; the references are our fine-grid layered solver (independent of the program's models, but the same 2D layered idealisation) and, for S3, dense eigenvalues; the 3D solver check of `lumped-analytic-vias` was not repeated here; the block-SOR omega (2.6) on three boards; the 0.45 mm pitch; the review.
