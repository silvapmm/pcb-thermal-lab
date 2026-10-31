# Young's omega for the SOR (S3) and a tile rule for the Analytic via correction (S4)

**Status: in preparation.** The library, the studies, the tests, the diagrams and the figure scripts are written and syntax-checked; no study has been run yet, so this file holds the questions,
the plan and the structure of the results, and every number is still to be filled from the printed output of the scripts (section 6 lists what each script prints). Nothing below is a finding.

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

## 2. S3 results (to be filled)

Plan, simple first. Scripts print Markdown tables; the numbers go here unchanged.

* **2.1 Textbook case** (`study_s3_exact.py` part A): the Poisson matrix `rho_J = cos(pi/(n+1))`, Young's relation against the dense SOR radius, the optimum against a scan, the program's formula as the optimum of the fixed-edge plate.
* **2.2 Exact cases** (part B): the periodic plate, `rho_J = 4g/(4g+a)`, the Rayleigh bound exact.
* **2.3 Plates of the program's stencil** (part C): the error of 1 - `rho_J` of the Rayleigh bound, Lanczos 2 to 20, the power method, for 1 to 6 layers and for even and uneven losses (edge, patch, one face).
* **2.4 Sweeps against omega** (part D, `study_s3_boards.py` part 1): sweeps at the program's omega, Young's, the estimates, the adaptive one and the measured best, on the plates, partial copper, the round board, the 5 x 5 via array (point treatment) and the example board at 2 and 1 mm.
* **2.5 With the mean-potential vias** (`study_s3_boards.py` part 2): omega of the stencil part against the measured best of the block SOR (c').
* **2.6 Cost** (`study_s3_boards.py` part 3): products and seconds of the estimates against the sweeps and the direct solve, with the grid.
* **Decision rule written before the runs:** adopt only an estimate that (a) is a lower bound or within 1 % of `1 - rho_J` on every board, (b) costs under 5 % of the sweeps it saves and (c) leaves SOR no slower than the program's SOR on every board; otherwise the item is dropped and the result is recorded as a limit.

## 3. S4 results (to be filled)

* **3.1 Unit cell** (`study_s4_tile.py` part 1): lattice cell of pitch 0.8 to 8 mm, the one-cell closed form with the Krogh wells (`study_causes.one_cell`), the program, and the corrected Analytic with tiles 0.4 to 2.5 mm.
* **3.2 Simple boards** (part 2): lone via, row, arrays, pad: error against the tile with 64 modes and with 2 per tile.
* **3.3 Modes against board size** (part 3): 5 x 5 pad on 30, 60 and 100 mm boards.
* **3.4 Rules** (`study_s4_rule.py` part 1): fixed 1 mm, multiples of the nearest-neighbour distance and of the target radius, and combinations, with the tile chosen and the mean and maximum error.
* **3.5 Where the rule breaks** (part 2 and 3): pitch 0.45 to 1.0 mm, drills 0.2 to 0.8 mm, the floor of the tile, the modes.
* **3.6 Many vias and cost** (`study_s4_arrays.py`): 4 to 576 vias, error of Lumped and Analytic (program, patch under review, rule), tiles, unknowns, seconds, peak memory, the coarsening above 1200 tiles.
* **3.7 The example board** (`study_s4_example.py`): the rows of `docs/validation.md` section 18 and the gain of the copper fill (program: 6.3 to 7.0 K; reviewed proposal: about 4.3 to 4.5 K; FVM, FDM and 3D solid: 3.9 to 4.5 K) with the rule.
* **3.8 The Lumped well** (`study_s4_lumped.py`): lone via against distance and ring count, rows, dense arrays open and filled, the cell and macro caps and the scale factors as candidate cheap fixes, and the distance of the via from the footprint edge at which a warning belongs.
* **Decision rule written before the runs:** the tile rule is adopted if it keeps every simple board within 5 % of the via effect with no tile constant that has to be chosen by the user, costs no more than the fixed 1 mm on the boards tested, and the mode rule is added only if the sweep of 3.3 shows an error that it removes; a Lumped fix is kept only if it cuts the lone-via and row errors without raising the array errors by more than 3 points, otherwise it stays a limit with a warning.

## 4. Limits (to be written from the results)

## 5. Independent references

* S3: the textbook Poisson matrix and Young's theory (Saad 2003, section 4.2.5); the dense eigenvalues and the dense SOR iteration matrix (nothing of Young's relation used); `young.sor_rb_matrix`, a red-black SOR written from the matrix alone, against the program's `solve_sor` (test).
* S4: the fine-grid layered solver `resolved_boards.full_board_2d` (the layered model of the program with the barrels drawn at their real size; nothing of the program imported), the one-cell closed form with Krogh wells, the axisymmetric and Cartesian references and the 3D solver `tests/helpers/layered3d.py` of `lumped-analytic-vias` where a case needs them.

## 6. Reproducing (from the repository root; the runs are phase 2)

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

* **Read (R)**: Saad, *Iterative Methods for Sparse Linear Systems* (2nd ed.), sections 4.1 and 4.2 including Theorems 4.10 and 4.16 and eq. 4.47 (read in the folder `sor-with-via-couplings` and relied on here); Saad, *Numerical Methods for Large Eigenvalue Problems* (revised ed.), section 4.1.1 (power method, Algorithm 4.1, Theorem 4.1, printed pp. 86-87) and section 6.6 (Lanczos convergence, Theorems 6.3 and 6.4, printed pp. 147-150): open copies of the author, extracted to text in the scratch area, nothing stored in the repository (`research/theory/BIBLIOGRAPHY.md` section 18). The README, INTEGRATION and review chapters of `sor-with-via-couplings` and `lumped-analytic-vias`, `pcbthermal/fvm.py` (`solve_sor`) and `pcbthermal/analytic.py` (the tile and the correction).
* **Not obtained (N)**: Young (1971), Varga (1962), Hageman and Young (1981): the adaptive estimate here is our own use of Young's relation, not their algorithm; no published numerical case of a via-array constriction.
* **Not yet done**: every study and every test of this folder; the review.
