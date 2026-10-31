# The via near an edge and on a real board (studies S1 and S2)

**Status: in preparation.** The code, the tests and the figure scripts are written and syntax-checked; no study has been run, so this README holds the plan and the empty result tables, and no number. The tables are filled from `out/` (`scripts/run_all.sh`) in the second phase.

This folder closes the open points that `point-via-convergence` (A5), `sor-with-via-couplings` (A13) and the roadmap items A14/A15 left before the via correction can be implemented as a fix: the point via (mean-potential coupling, centred footprint, Peaceman well of target radius `0.78 r_v`), the block SOR (c') and the single footprint rule of the 3D solid. The program is not touched; everything is measured on in-memory copies (`lib/edge_patch.py`).

## 1. Questions

1. **S1.** A via near the board edge or an outline is +12 to +15 % in the via effect at 1 mm cells because the lattice kernel has no image of the edge (`point-via-convergence` 8). Is it worth putting the image in the kernel, or do we document a limit? How does the error depend on the distance to the edge, the cell and `h_side`? What does the footprint restricted to the cells on the board change at an outline?
2. **S2.** On a real board with at least 100 vias: how do the size and the fill-in of the matrix grow with the number of vias; how many sweeps does the block SOR (c') need against the direct solution; what does the 3D solid do with the single footprint rule; what does the Lumped model keep (`gz_via`); how much does the temperature move against the current program; where does it break (thousands of vias)?
3. **Delivery.** Exactly what to change in the program (functions and files), the tests, the numbers of `docs/validation.md` that move, new warnings and documented limits (`INTEGRATION.md`).

### 1.1 Pictures of the situation

![A plated barrel through the planes and the heat paths](figures/fig_01_barrel_section_heat_paths.png)

*Figure 01 (`figures/fig_01_barrel_section_heat_paths.png`): the section of a plated barrel through four planes: heat spreads sideways in each plane towards the barrel (`ln(r/r_v)/(2 pi S)`), goes down the barrel (`G_v` per gap) and leaves through the films (illustration).*

![The point via as a Peaceman well](figures/fig_02_point_via_peaceman_well.png)

*Figure 02 (`figures/fig_02_point_via_peaceman_well.png`): left, the footprint weights of a via on the cells, the drill and the target radius `0.78 r_v`; right, the network added to the matrix (wells `G_c`, barrel `G_v`, plane means) (geometry of the drawing, weights from the footprint routine).*

![A via near an edge and its image](figures/fig_03_via_near_edge_image.png)

*Figure 03 (`figures/fig_03_via_near_edge_image.png`): a via 0.16 mm from an insulated edge on 1 mm cells: the true image at `D_true = 2 delta`, the image the grid has at `D_lat` (mirror of the cell centre), and the term `c = ln(D_lat/D_true)` that the well would carry.*

![The footprint on the cells of the board](figures/fig_04_footprint_on_board_cells.png)

*Figure 04 (`figures/fig_04_footprint_on_board_cells.png`): three treatments of the cells that an outline cuts or the grid border leaves out: kept (prototype), restricted to the board with the cover as weight, folded to the mirror cell.*

![Block SOR colouring](figures/fig_05_block_sor_colouring.png)

*Figure 05 (`figures/fig_05_block_sor_colouring.png`): the red-black colours of the stencil, the via cells skipped by them, and the via blocks coloured in groups of blocks that K does not couple (illustration).*

## 2. Method

* **Reference for S1** (`lib/edge_reference.py`): the layered model of the program written again in `sheets2d` (imports nothing of the program) on a 1/16 mm grid, the barrel at its real size; 1/32 mm for a check (`--check-fine`). Board: 10 x 10 mm, four planes, 0.5 W in a 3 x 2 mm source, one 0.3 mm copper-filled via at 0.16 to 4 mm from the right edge; optional edge film, corner, and outline cuts at x = 7 and 7.03125 mm. The layered idealisation against a 3D barrel is `point-via-convergence` 3.2/3.3 (not repeated; the spread of -2.1 to +3.9 % of the target radius stays in the error budget).
* **Candidate for the image** (`lib/edge_image.py`, `docs/theory-text.md`): `G_c = 2 pi S / (ln(r_eff/r_t) + c)`, `c = sum ln(D_lat/D_true)` over the images of the walls near the via. Decision rule written before the run (`scripts/study_edge_distance.py` header): adopt only if the error at 1 mm and d <= 1 mm falls under 3 % for every distance and `h_side` 0 and 10, the cost is under 1 ms per via and the code is under 60 lines; otherwise the limit is documented.
* **Variants** (`lib/runs.py`): program (develop), `mw` (the prototype), `mw+board` (footprint on the board), `mw+image`, `mw+fold`.
* **Boards for S2** (`lib/real_board.py`): the Allegro four-layer board (283 plated holes, 241 of 0.30 mm; licence not stated: numbers only, no picture), the Stormduino (MIT, 109 plated holes, two layers, figures allowed) and an own via field (100 and 900 vias; scalable to thousands), full copper on every layer and the source on the densest window, so that the via effect is isolated; the real copper pattern (`gerber-models`) is a second stage. The files are read in place from the git-ignored data folder (`scripts/fetch_boards.py`); nothing of a third party is stored here.
* **Matrix** (`lib/matrix_stats.py`): unknowns, `nnz(K)`, via blocks, dense coupling entries, `nnz` of the LU factors with the program's ordering, memory estimated from them (12 bytes per non-zero); the spy patterns are coarse counts per block. Timings are not results.
* **SOR** (`scripts/study_sor_real.py`): `sorvia.solve_variant(net, "block_over")` against the direct solution and against the program's rule; block structure after merging overlapping footprints (a few huge blocks would make the dense inverses the limit).
* **Validation rows** (`scripts/study_validation_rows.py`): the generators of `docs/validation.md` 2, 2.1 and 18 run on develop and in the patch; the cells that move are listed.
* Tests (`tests/`, 23 tests written, none run yet): the algebra of the image, restriction and fold; identity of the hook with the prototype when its options are off; vias as pure couplings (symmetry, zero row sum); `gz + gz_via` equal to the program's `gz`; the walls; the block structure; the board builders.

## 3. S1: the via near an edge (to be filled)

### 3.1 Insulated box edge, distance and cell (`out/edge_distance.txt`)

| d (mm) | reference E (K) | variant | 1 mm | 0.5 mm | 0.25 mm | 0.125 mm |
| --: | --: | :-- | --: | --: | --: | --: |
| 0.16 ... 4 | not run | program, mw, mw+image, mw+fold | | | | |

*Figures 06 and 07 (`fig_06_edge_error_against_cell.png`, `fig_07_edge_error_against_distance.png`): the error against the cell and against the distance, with and without the image.*

### 3.2 Edge film `h_side` 0 and 10 W/m2K, and the corner (`out/edge_distance.txt`, `out/edge_corner.txt`)

Not run.

### 3.3 An outline off the grid lines and the footprint restricted to the board (`out/edge_outline.txt`)

Not run. *Figure 08 (`fig_08_outline_footprint_variants.png`).*

### 3.4 Decision

Not taken. The rule is in section 2; the result and the text of the documented limit (if the image is not adopted) go here.

## 4. S2: boards with 100 or more vias (to be filled)

### 4.1 The vias of the boards (`out/real_stats.txt`)

Counts, diameters, nearest neighbours, shared cells and overlapping footprints at 2, 1, 0.5, 0.25 mm. Not run.

### 4.2 The matrix against the number of vias (`out/fillin.txt`)

Unknowns, `nnz(K)`, `nnz(LU)` and memory against 25 to 4900 vias at three cells, program against couplings; where the estimated dense entries exceed the guard the configuration is reported as skipped (that is the place where it breaks). *Figures 09 and 10 (`fig_09_sparsity_against_vias.png`, `fig_10_unknowns_nnz_against_vias.png`).* Not run.

### 4.3 Temperature (`out/real_effect.txt`)

`T_max` and the via effect against the cell, program against recommended, FVM and FDM; copper-fill gain; maps of the Stormduino and the own field. *Figures 12 and 13.* Not run.

### 4.4 Block SOR (`out/sor_real.txt`)

Sweeps against the direct solution and against the board without vias; blocks, largest block, inverse memory, colours. *Figure 11.* Not run.

### 4.5 3D solid with the single footprint rule (`out/solid3d_real.txt`)

Not run.

### 4.6 Lumped and Analytic (`out/lumped_gzvia.txt`)

The Lumped T_max with `gz_via` must be identical to the program's; the Analytic model does not read the FVM arrays. Not run.

### 4.7 Which numbers of `docs/validation.md` move (`out/validation_rows.txt`)

Sections 2, 2.1 and 18 and the via rows of Lumped and Analytic; section 5 (SOR on the example board). Not run.

## 5. Limits already known

* Uniform copper on the real boards (the isolated via effect); the real copper pattern and its interplay with the vias is not in this folder.
* The image is derived for straight walls parallel to an axis; a diagonal or curved outline gets none; the FDM edge nodes are half volumes and get none.
* No measured board; no independent reference for the real boards (the convergence with the cell is the evidence, the references are the simple boards of S1 and `point-via-convergence`).
* The Allegro board has no stated licence: no figure of it.

## What was read and what was not verified

**Read in full or in the part that matters.** The code and documents of `point-via-convergence` (README 8, 9, INTEGRATION.md), `sor-with-via-couplings` (INTEGRATION.md, `lib/sorvia.py`), `fvm.py` (edge, cover and pin handling), `solid3d.py` (the via fraction), `lumped.py` (what it reads from the network), and the Excellon header of the Allegro board (tool table: 241 holes of 12 mil, 36 of 45 mil, plated).

**Seen as a summary only.** The image-well method (a search snippet) and a paper on the Peaceman well block near a boundary (title only; see `research/theory/BIBLIOGRAPHY.md` section 18).

**Not obtained.** Peaceman (1978, 1983) full texts; any source that gives a well-block radius next to a boundary. The image term is derived here from the lattice kernel, not taken from a source.

**Not run.** Everything in sections 3 and 4: no number of this folder has been measured. The expected direction of the image (a smaller via effect near the edge) is a derivation, not a result.

**Doubts of the researcher.** (1) For an outline that does not lie on a cell face the mirror of the cell centres about the true wall is only an approximation of what the partially covered cells do; the study may show the image works only for walls on cell faces. (2) The sign and size of `c` for a footprint of several cells is untested. (3) The dense block inverses of the block SOR may be the real limit on boards where footprints merge. (4) The Allegro board is a layout of unknown origin; the heater is put where the vias are densest, which is the worst case for the model and not a typical use.

## Reproduce

`sh research/via-real-board/scripts/run_all.sh` from the repository root (needs the network once for `fetch_boards.py`, or the data in `research/gerber-import/data`); tests: `.venv/bin/python -m pytest -q research/via-real-board/tests`.
