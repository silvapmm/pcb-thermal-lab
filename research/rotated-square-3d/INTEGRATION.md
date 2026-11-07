# Entering the program: the cells that the outline cuts in the 3D solid

Nothing in `pcbthermal/` was edited. The proposals were measured on a copy of `pcbthermal/solid3d.py` made in memory by `lib/rotsq.py` (a text replacement of four expressions, refused when the source changes). Numbers are in `README.md`; the maintainer decides.

## Decision asked for 2.5.0: the cut cells of the layered FVM (README 11)

**Recommendation: 2.6.0.** It fits 2.5.0 technically; it is not worth the refreeze and the risk of landing it with the Gerber import. If the maintainer decides for 2.5.0 nevertheless, this is the exact change, the numbers that accept it, and what stays out.

### Recommendation of the review (README 11.8)

No-go for 2.5.0, go for 2.6.0 **in two steps, the exact cover first**:

1. **`fix/` item, the exact cover** (*done on `fix/exact-board-cover`: `geometry.exact_coverage` by column sums, not by clipping each cell; the numbers of this paragraph were reproduced, `scripts/study_exact_cover.py`, `docs/validation.md` 23.1; the turn spread at 1 mm is 0.076 K, the pending files moved the records as listed, plus the FDM, the 3D solid and the Analytic read-out*) (`Board.cover` by clipping; `lib/cutcell_exact.py::exact_cover`, about 15 lines in `geometry.py`). It is the only part that helps the default `h_side` 10 (turn spread of the 20 mm square at 1 mm 1.0 K to 0.08 K against the frame reference of `scripts/study_turn_frame_reference.py`) and it corrects the area of an edge that runs along a lattice direction of the 8 x 8 samples (+0.64 % of the area of a 20 mm square at 45 degrees and 1 mm, -0.38 % at slope 1/3). It enters the FVM and the 3D solid (both read `Board.cover`); `geometry.part_weights` then loses the exact `n_pb / 64` identity of the sampled cover (to be measured), and `analysis.py` masks that test the cover against 0.01 read the new values. Frozen FVM records that move (measured): `part_across_outline` -0.55 / -0.45 / +0.12 K at 2 / 1 / 0.5 mm, `round_outline` +0.005 / +0.010 / +0.004 K; `t_outline` and `example_cut_to_T` unchanged; the 3D solid records not measured. Acceptance: polygon area to 1e-9 at 45 degrees; the turn spread of README 11.8 at `h_side` 10 and 1 mm at most 0.3 K; the battery and a pending file.
2. **`feature/` item, the lateral links, after a choice of scheme.** The evidence does not yet pick `links`: on the closed form of a sheet with a film on its rim (`docs/literature.md` 4) the face aperture with the nodes at the centres (`aperture`) is twice as accurate as `links` and the aperture with the boundary film of Bochkov and Gibou ten times, while on the layered boards of README 11.2 `links` is better than `aperture`. Before the implementation: run the three on the boards of 11.2 against the frame reference and on the fill at a cut edge (11.5). On the most-moved harness record (`part_across_outline`) `links` errs by -0.73 / -0.38 / -0.16 K against 0.125 mm, the program by +0.70 / +0.79 / -0.08 K: the frozen number moves by about the same size to the other side at 2 mm.
3. Not proposed: `links+strip` (changes the edge of every board), the FDM and the 3D solid variants.

### Why not 2.5.0

* The gain at the defaults is below 1 % of the rise: at `h_side` 10 the dependence on where the outline cuts the grid is 0.1 to 0.7 % of the rise and the cut-cell links do not change it (an exact cover does); at 100 W/m2K it is 0.6 % (links: 0.08 %) and at 2000 W/m2K 5 % (links: 0.6 %), a typed coefficient for a board clamped to a chassis (README 11.2).
* It moves frozen records: of the 17 harness boards four have an outline; the FVM records of `round_outline` (-0.009 K at 2 mm), `example_cut_to_T` (-0.028 K at 2 mm) and `part_across_outline` (-1.43 K at 2 mm, -1.17 at 1, -0.08 at 0.5, 0.7 % of the rise at 2 mm) move, `t_outline` does not (README 11.6). A `pending/<topic>.json` and a refreeze in the release of the Gerber import.
* The FDM and the 3D solid keep their own treatment of the same edge, so `docs/validation.md` 13 and 23 change for the FVM only; the FDM (dual cells) was not prototyped.
* The case that matters for a real outline, vias and partial copper on a cut edge, has no clean verdict: with copper held 1.2 mm inside the outline every scheme spreads 3 to 9 K and `links` sits 0.9 to 3.7 K cool at 1 mm (README 11.5); the cause (the fill of a cut cell is sampled over the cell, the copper edge moves against the grid with the outline) is untested.

### The change (variant `links`, FVM only; `pcbthermal/` untouched here)

1. `pcbthermal/geometry.py`: new `cut_cell_geometry(poly, nx, ny, dx, dy)` returning `cover`, `xc`, `yc`, `ax` (ny, nx-1), `ay` (ny-1, nx) and `cut` by exact clipping (`research/rotated-square-3d/lib/cutcell_exact.py::cut_geometry_exact`, about 70 lines: the cut cells are the cells whose corners are not all on the same side of the outline or that `edge_length_per_cell` marks; area and centroid from `clip_polygon` against the cell box; the aperture of a face is the length with board on both sides from the crossings of the outline with the face line). Today a Python loop over the cut cells (15 ms for 100 cut cells): vectorise it before a board with tens of thousands of cut cells, or use the 16 x 16 sampled `cutcell.cut_geometry_fast` (0.07 s at 800 000 cells; the sweeps of README 11 show the two give the same links to 0.3 K in the worst case, the exact one is cleaner at 45 degrees only for the cover).
2. `pcbthermal/fvm.py`, `Network.__init__`: after the cover, `self.cut = geometry.cut_cell_geometry(...)` when `b.has_outline()` and the problem has no metal block (a board with a block keeps the program's links; `blocks.py` cuts its layer by `coverage_fraction * cover`, not handled).
3. `pcbthermal/fvm.py`: one new method `_lateral_links()` returning `(gx, gy)`: the program's harmonic expression `harmonic(S1, S2) * dy / dx` everywhere, replaced **only for a pair in which a cell is cut** by `g = a * L_face / (d1 / Sp1 + d2 / Sp2)` with `a` the aperture (and both cells active), `L_face` = `dy` (x link) or `dx` (y link), `d1`, `d2` the distances from the face to the two centroids along the normal (at least 1e-3 of a cell side), `Sp = S / cover` the physical sheet of each node layer (the prototype shows laminate nodes and via footprints keep their cover scaling); then the imported layers' faces as today. `_assemble` and `solve_sor` call it and drop their two copies of the block (`solve_sor`'s copy was the reason the section-10 prototype ran the SOR on the program's links). Capacities, films, vertical links, vias, laminate nodes are not touched. The matrix stays symmetric positive definite; `factor_reuse`, CG, block SOR and the direct solver are unchanged. Reading the result: the temperature of a cut cell is at the centroid of its board part (the map and `t_max_location` keep the cell centre, up to half a cell).
4. Restricting the replacement to pairs with a cut cell should make boards without an outline and outlines on the grid lines **bit-identical**; this restriction is a design step that the prototype does not have (it applies the formula everywhere, which equals the program's to rounding, 1e-8 K, and is what the tests of the folder check), so the bit-identity is **not yet measured** and the first test of the implementation.
5. Not changed: the exact cover is **not** part of this change (it is a separate, smaller item: `Board.cover` by clipping, about 15 lines in `geometry.py`; it fixes the 45 degree artefact of -0.85 K at `h_side` 10 and cuts the turn spread at the default coefficient from 1.5 to 0.35 K at 1 mm, README 11.3; it moves the same records and needs `analysis.py`'s masks, which test the sampled cover against 0.01, to read the network's cover instead); the edge conduction of the strip (`links+strip`, README 11.6 item 5); the FDM and the 3D solid.

### Acceptance tests (numbers)

1. A rectangle without an outline and an outline on the grid lines: fields **bit-identical** to the program (the prototype's test: matrix equal to 1e-9 and temperatures to 1e-8 K; equality to the bit needs item 4 above and is the first test to write).
2. 20 mm square, 2 W in a 3 mm part, `h_side` 2000, 1 mm cells, the part fixed on a cell centre, the outline moved by k/8 of a cell (references: the same board at 1/8 mm, where the shifted edge lies on grid lines; for the turns, the frame reference of `scripts/study_turn_frame_reference.py`, no cut cell): spread of the hottest point **at most 0.5 K** (program 2.8 K, `links` 0.34 K, maximum 0.43 K on the three boards of README 11.2); at `h_side` 100 at most 0.2 K (program 0.80 K, `links` 0.11 K); turned 0 to 45 degrees at 2000: at most 0.5 K (program 1.7 K, `links` 0.29 K).
3. Round board of 40 mm against the axisymmetric reduction of the layered model, 1 mm, `h_side` 1000: peak error **at most +0.3 % of the rise** (program +0.69 %, `links` +0.22 %), rim loss within 0.25 % (program -0.27 %, `links` +0.17 %).
4. Heat balance of every case 1e-9 or better (measured 1e-13); K symmetric, diagonal positive; the largest link at most 2 times a whole pair (measured 1.33 to 1.79 for covers 1/2 to 1/64).
5. SOR equals the direct solve to 1e-6 of the maximum on a turned square with vias; sweeps not more than 5 % above the program's (measured 127 to 130 against 130 to 148); CG iterations not more than 20 % above (measured 0 to 15 %).
6. Transient: the slowest time constant and the capacities unchanged to 1e-4 (measured 6.6e-5, `scripts/study_cutcell_capacity.py`); the implicit step response within 1 % (test of the folder).
7. Frozen numbers: the pending file lists exactly the FVM records of `round_outline`, `example_cut_to_T` and `part_across_outline` (and their times to 63 %); every other record equal; `make_pending.py` and the refreeze at the release.
8. The whole battery, `docs/validation.md` 13 and 23 re-run and quoted, `docs/theory.md` 1.3 and the FVM section (with Figures 9, 10 and 15) rewritten, `docs/versions.md`.

### What would change the recommendation

* A study of the fill of a cut cell with the outline (copper edge across a cut cell, laminate nodes at the edge) that shows `links` no worse than the program there, or a fix of the sheet used in the link (`S / cover` for a partly covered cell with fill): README 11.5.
* The maintainer wanting the edge conduction (`links+strip`) in the same change: it makes the shift spread 0.03 to 0.1 K and lands nearest the fine value at 0.5 mm but moves every board with a typed `h_side` unless the rectangle without an outline gets the same strip; that is a decision about the edge of every board, not about cut cells.

## The earlier proposal for the 3D solid (sections 2 to 6 of the README)

(Only the 3D solid; kept as written.) 

### What changes in the program, if P1 is adopted

Only `pcbthermal/solid3d.py`, only for a board with an outline (`Board.has_outline()`); the rectangular branches (no outline) are untouched and give bit-identical results (README 6).

1. **The cover and the geometry of the cut cells.** `bcov = b.cover(nx, ny, dx, dy)` is replaced by a sampling of every cell on a 16 x 16 lattice that returns, besides the cover, the centroid of the board part of the cell and the board fraction ("aperture") of every face between two cells (`lib/cutcell.py`, `cut_geometry`; about 40 lines using `geometry.points_in_polygon`).
2. **No scaling of the in-plane conductivity by the cover.** The line `slabs[-1]["kx"] = np.maximum(slabs[-1]["kx"] * bcov, ...)` keeps the physical conductivity; the cross-section of a link is carried by the aperture.
3. **The links between cells** (the loop over slabs): between two board cells the conductance is `min(dz) * face_length * aperture / (d1/k1 + d2/k2)`, with `d1`, `d2` the distances from the face to the centroids of the two board parts (a whole pair of cells: `dx/2 + dx/2`, the program's value); a face off the board has no link.
4. **The edge term** of a cell on the outline: `1 / (1/(h L dz) + d / (k L dz))` with `d = c dx dy / (2 L)`, half the depth of the strip of board behind the outline in the cell (a whole edge cell: `dx/2`, the program's value), the physical `k`, instead of `0.25 (dx + dy)` through `k * cover`.

The code of the copy is in `lib/rotsq.py` (`CUT_COVER`, `CUT_LINKS`, `STRIP_EDGE`) and is what the measurements below ran. A tidy implementation would vectorise the sampling and keep the documentation, tooltips and tests of the program; the cost of the sampling was not measured.

## Measured impact

| where | program | copy (P1) | README |
| :-- | --: | --: | :-- |
| 40 mm square turned 20 degrees, 1 mm cells, `h_side` 1000, board only | +3.12 K above aligned | -0.18 K | 2 |
| same, `h_side` 100 | +1.28 K | -0.04 K | 2 |
| same, `h_side` 10 (default) | +0.06 K | -0.00 K | 2 |
| 20 mm square, half-cell shift, `h_side` 2000, 40 / 80 / 160 cells per side | +5.78 / +3.58 / +2.03 K | -0.23 / -0.04 / -0.01 K | 4 |
| same, turned 20 degrees | +5.59 / +3.72 / +2.32 K | -0.27 / -0.00 / +0.03 K | 4 |
| same, turned 45 degrees | +4.81 / +3.78 K at 40 / 80 | +0.69 / +0.49 K | 4 |
| round board 40 mm against the (r, z) reference, 1 mm, `h_side` 1000 / 5000 | +6.6 / +5.9 % | +0.5 / +0.6 % | 5 |
| round board, 0.25 mm, `h_side` 1000 / 5000 | +3.2 / +2.7 % | +0.1 / +0.2 % | 5 |
| round board, `h_side` 10 (default), 1 mm | -0.3 % | -0.3 % | 5 |
| example board with the five outline presets, `h_side` 10 | | within 0.20 K (T), 0.01 K (the others) | 6 |
| same, `h_side` 100 | | within 0.38 K (ellipse), 0.11 K (T), 0.05 K (the others) | 6 |
| rectangular board, no outline | | bit-identical | 6 |

What changes for the user: results of the 3D solid on a board with an outline that is not on the grid lines, at an edge coefficient from about 100 W/m2K up, move by 1 to 12 K at the cells in use towards the grid-independent value; at the default 10 W/m2K and on a rectangle nothing moves by more than 0.4 K. The 3D solid is a comparison model; the FVM, FDM, Lumped and Analytic are not touched.

## Risks and what to check before adopting

* The scheme is a standard cut-cell finite-volume idea written from scratch; no source was opened for it when it was written (README 12; the reading done for the layered FVM, section 10, is in `research/theory/BIBLIOGRAPHY.md`). Its energy balance is exact (checked on a turned square to 1e-9) and it reproduces an independent axisymmetric reference on a round board, but patterned copper, vias and metal blocks on the outline were only run in the regression (no independent reference).
* The T board at the default coefficient moves by +0.2 K. *Review*: the cause is not the edge term but a part that crosses the outline (P0 below); with the power of the part on the board part of each cell the program and the copy agree on the T.
* The 45 degree turn keeps +0.5 to +0.7 K at 40 to 80 cells per side; *review*: part of it is the 3D solid's 4 x 4 sampling of the footprint of a part (README 9.3), the rest (+0.44 / +0.18 K at 80 / 160 cells per side against the continuum value, README 9.2) is the board turn and stays with P1.
* A change of the 3D solid changes the numbers of `docs/validation.md` for the outline cases and of the tests that compare the 3D solid with the other models on an outline; the whole battery has to run.
* The 16 x 16 sampling grows the set-up by a sampling pass over every cell (measured nowhere here).

## Alternatives

* **P2, a documented limit instead** (no code change): `docs/validation.md` and `docs/theory.md` say that the 3D solid on an outline that is not on the grid lines depends on the position of the edge by up to 1 to 3 K at `h_side` 100 to 1000 W/m2K and 1 mm cells (and 2 K at 160 cells per side), 0.3 K or less at the default coefficient; the layered models do not show it to that size. The text for the documents is in `docs/for-the-project-documents.md`.
* **P1a, the minimum change** (the edge term only, no new links): the physical conductivity and the distance of the strip (`strip` in the copy) remove about 70 % of the error at 40 cells per side and 60 % at 80 (README 4: 5.78 -> 1.67 K at 40, 3.58 -> 1.43 K at 80), but not the shift invariance; it needs the cell cover only and is a two-line change. Not recommended alone.

## P1 for the layered FVM (and what it means for the FDM, the 3D solid, the Lumped and the Analytic): the design

Evidence: `README.md` section 10 (prototype `lib/fvm_cutcell.py`, measured on copies, light cases; nothing in `pcbthermal/` was edited). **Recommendation: no-go for 2.5.0, go as a low-priority item for 2.6.0, variant `links`, FVM only**, after the heavy checks of README 10.8 (the maintainer decides).

### The scheme (variant `links`)

1. **Geometry of the cut cells** (new, about 40 lines, `cutcell.cut_geometry_fast` of the prototype): the cells the outline crosses (`geometry.edge_length_per_cell > 0` or corners on both sides) are sampled 16 x 16 with `geometry.points_in_polygon`; for each, the cover, the centroid of the board part `(xc, yc)` and the aperture of the four faces (board fraction of the face length, a face counts where both sides are board). A face next to no cut cell has aperture one between two board cells and zero otherwise. 8 samples were visibly worse than 16 (README 10.4, `sens`); the cover used for volumes, capacities, films and part weights stays the program's 8 x 8 `Board.cover` (the two lattices are not the same: a cell the 8 x 8 cover calls empty keeps no link). Cost: 0.07 s at 800 000 cells, 0.2 s with a 128-sided outline at 176 000 cells.
2. **Lateral links** (replace `gx`, `gy` of `fvm.Network._assemble`): `g = a * L_face / (d1 / Sp1 + d2 / Sp2)`, with `a` the aperture, `L_face` the face length (`dy` for an x link, `dx` for a y link), `d1`, `d2` the distances from the face to the two centroids along the normal (at least `1e-3` of a cell side), and `Sp = S / cover` the physical sheet conductance of each layer node (the arrays `S`, `C`, `gz`, the films, the vias and the laminate nodes keep their cover scaling, so nothing else is rewritten). For a whole pair (aperture 1, `d1 = d2 = d/2`) this is the program's expression bit for bit; for a board without an outline the matrix is the program's (test).
3. **Edge film**: kept on the node (the program's convention). The variant that also puts the conduction from the centroid to the outline in series (`links+strip`, half the depth of the strip) moves aligned boards and rectangles (+0.1 to +0.2 K at `h_side` 2000, 20 mm square) and is **not** proposed until a finer reference says which is nearer the continuum.
4. **Small cells**: no flux redistribution or cell merging is needed (steady state and the implicit transient have no small-cell time-step limit; Berger and Helzel's problem is the explicit step). The conductances stay bounded (largest x link 1.2 to 1.6 of a whole pair on the boards measured; two slivers straddling one face are the only way to a large value and the 1e-3 floor and a floor of a quarter cell gave identical results to 0.04 K). The scheme is symmetric positive definite (two-point fluxes), unlike Johansen and Colella's (non-symmetric, interpolated gradients, Dirichlet boundary stencil), so the direct, CG and block SOR solvers and `factor_reuse` keep working; the price is a first-order flux error at a cut cell (their analysis, report p. 6 and 10, says it is of third order in the solution when the error is a dipole; we did not verify that for the film boundary).
5. **Read-outs**: the unknown of a cut cell is the temperature at the centroid of its board part; `t_max_location` and the plots keep the cell centre (up to half a cell off, no effect on a value). Capacities and the transient are unchanged (time to 63 % within 0.3 % in the prototype).

### Where it goes, and what changes

* `pcbthermal/fvm.py` only (`Network.__init__`: the geometry when `Board.has_outline()`; `_assemble`: the two lateral links) and a function of `pcbthermal/geometry.py`. The Lumped and Analytic models are **unaffected** (they run on the equivalent rectangle, there is no cut cell). The FDM and the 3D solid are separate items.
* **Numbers that move**: every result of a board whose outline cuts cells (by 0.1 to 0.5 K in the cases measured, up to 0.75 % of the rise at 1 mm on a round board with `h_side` 1000 or more); boards with the outline on grid lines, and rectangles, are bit-identical (test). The frozen-number harness has boards with an outline: **count and measure them** (README 10.8, item 2) before deciding; `releases/regression-harness/INTEGRATION.md` 2 is the procedure for a deliberate move. Documents: `docs/validation.md` 13 and 23, `docs/theory.md` 1.3 and the FVM section (with a picture: Figures 9 and 10 are ready), `docs/versions.md`; tests to re-measure: `tests/test_outline.py`, `tests/test_part_across_outline.py` and any test that fixes an outline temperature.
* **FDM** (node-centred, `fdm.py`): the unknown is on a grid point and the control volume is the dual cell, cut by the outline like a cell; the same two ingredients apply (aperture of the dual-cell faces, distance between the centroids of the cut dual cells), and its edge-shift scatter (2.02 K on the small T at 1 mm, `docs/validation.md` 23) is larger than the FVM's, so it may gain more. **Not prototyped.** A separate item after the FVM.
* **3D solid**: `solid3d.py` has the same defect in a much larger form (README 2 to 6) and its cut-cell copy exists (section above); with the P2 recommendation of the review (document the limit) it waits for the maintainer's choice; the layered links of this section would be written the same way there.
* **Vias, laminate nodes, metal blocks**: the prototype leaves them as they are; `S / cover` is the physical sheet conductance for every node layer built by the program's rule (laminate sub-gap nodes carry the same cover scaling: **not tested** on a patterned-copper board at a cut edge); a metal block layer is cut by `coverage_fraction * cover` and is **refused** by the prototype; a via whose Kron footprint sits at a cut edge uses the cells' `S` and cover, with its footprint centred on cell centres (a 1 to 3 cell distance study is in README 10.8). These three are the risks; none has an independent reference yet.

### Risks and limits

* The residual of the small T (1.0 K at 1 mm, README 10.4) is **not** removed and its cause (re-entrant corner) is untested; the claim is "reduces the dependence on the cut where the cut is a straight edge", not "makes the answer independent of the grid".
* The measured benefit is 0.2 to 0.5 K (0.3 to 0.5 % of the rise) at 1 mm on boards with an outline off the grid lines and up to 0.7 % on a round board with an edge cooled hard; the program's other model-form differences are 5 to 10 %.
* The prototype's tests (copy them when adopting): the fast geometry equals the full sampling; a half-cell edge has centroid a quarter cell inside and aperture one; a rectangle gives the program's matrix; an outline on grid lines gives the program's temperature; the energy balance of every variant on a turned square; shift dependence removed on a 20 mm square at `h_side` 2000; the closed form of an insulated rectangle and the axisymmetric reduction of a round board (`tests/test_fvm_cutcell.py`).

### Decisions for the maintainer

1. Version: not 2.5.0 (below 1 % of the rise, partial gain, one more thing to refreeze while the Gerber import enters), 2.6.0 as a low-priority `feature/` item of the FVM, or a documented limit only (P2).
2. If adopted: `links` only (bit-identical away from cut cells), the FDM and 3D solid as later items, the edge conduction (`links+strip`) only after a finer reference.
3. Whether to run the heavy checks first (README 10.8: about 3 GB and 10 minutes for the small-T sweep, one process at a time; the harness boards; vias and patterned copper at a cut edge).

## P0, found by the review: the power of a part that crosses the outline (FVM, FDM and 3D solid)

Not part of A3, and a defect of the reference model at the default edge coefficient (README 9.4). The FVM (`fvm.py`, `cov = coverage_fraction(h.polygon, nx, ny, dx, dy, samples=8) * self.active`), the FDM (`fdm.py`, the heater weights around line 246) and the 3D solid (`solid3d.py`, `w = cover(h.polygon, 4) * self.active`) weight a board cell by the part's cover of the whole cell, so where a part crosses the outline the board part of a cut cell gets 1 / cover of the power density. Measured on copies (`rotsq.fvm_part_on_board`, variant `program_part_on_board`) with the weight "part cover times board cover": the example board cut to a T at 1 mm and `h_side` 10 goes from 109.06 to 107.56 degC in the FVM (value at 2/3 mm, where no cell is cut: 106.85) and from 109.31 to 107.79 in the 3D solid (107.08); a small T with the part over the re-entrant corner goes from +0.5 to +7.7 K above its grid-line value to within 0.1 to 0.9 K. The clean form is the sample-wise intersection of the part and the board (one lattice, both tests per sample); a `fix/part-across-outline` branch with a regression test (a part over a re-entrant corner, cut against grid-line cells) and the re-run of `docs/validation.md` 13 (its "T, example" FVM reference 109.1 degC is about 2.2 K high). The FDM was not run with the correction. Smaller, same branch or a separate one: sample the footprint of a part 8 x 8 in the 3D solid, as the FVM does (README 9.3).

## Recommendation of the review

P2 for A3 (README 9.5): the effect needs an outline off the grid lines and a typed `h_side` of about 100 W/m2K or more (default 10, where it is 0.3 K or less); at 1 mm it is +1.1 to +1.8 K (1.6 to 2.7 %) at 100 and about 7 % at 1000 in a comparison model, while the FVM, the reference, is within 0.6 % of its own reference there; P1 rewrites four expressions of the 3D solid, moves every 3D outline number and still leaves 0.2 to 0.5 K at 45 degrees. Keep P1 in 'Planned' as an option. Do P0.

## Decisions for the maintainer

1. P1 (the cut-cell scheme in `solid3d.py`, on a `fix/` branch, with the 3D tests re-measured), P2 (document the limit) or both in order; the review recommends P2.
2. P0 (the power of a part that crosses the outline, in the FVM, FDM and 3D solid): a `fix/` branch, recommended by the review.
3. Whether the FVM and the FDM keep their treatment of the edge (no change proposed: README 7; P0 is a different matter).
4. If P1: a regression test of the program equal to `test_shift_invariance_is_restored_by_the_cut_cells` and the disc against the axisymmetric reference (both exist in `tests/test_rotated_square.py` of this folder and can be copied).
