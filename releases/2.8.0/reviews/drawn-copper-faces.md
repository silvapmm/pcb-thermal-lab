# Review: `fix/drawn-copper-faces` (drawn copper read as imported copper, FVM and FDM)

**Verdict: GO**, with the two fixes below committed on the branch and the whole battery still to be run by the tester. Open questions for the maintainer at the end.

## What was checked

* **Code against the theory** (`docs/theory.md` 1.2, 1.7, 2.7; `research/drawn-copper-faces` README 1 to 11, INTEGRATION.md): the exact union fill (`copper._zone_union`: zones of one fill add and clip to one, different fills from the largest down; a hatch fill stays float), the flow-based faces on the reduced sheet built after the laminate rule (the same `CopperSource.lateral` and the same order as the imported copper, validation 38), the hook (`fvm.Network` only with `ladder` and `cut_cells`; `fdm.Network` with area sampling), the fallback (self-crossing zone or too many crossings: no source, the earlier path for the whole problem, silent, the live self-crossing warning stays the user's information), imported copper (no drawn source at all: its drawn layers keep the earlier path, stated in validation 51).
* **Frozen numbers**: `PCBT_FROZEN_CELLS=2,1,0.5 pytest tests/regression` without the pending file fails exactly the 8 FVM/FDM records and the 8 times to 63 % of `drawn-copper-faces.json` (16 failed, 301 passed); with it 317 passed, before and after the review's fixes. No Lumped, Analytic or 3D solid record moves; no record is in two pending files (`lumped-part-readout.json` holds Lumped records only). The harness copy and `releases/regression-harness/lib/regress_boards.py` are byte-identical.
* **Independent re-run**: the three harness boards at 1 and 0.5 mm in FVM and FDM reproduce `FROZEN` of `tests/test_drawn_copper_faces.py` to the digit; against the finite-element values (README 2.1 of the research folder, only READ: the scratch FEM environment is not available) FVM +0.1 / -1.4 %, -0.6 / -1.9 %, -0.0 / -2.5 %, FDM -1.0 / -1.2 %, -1.8 / -1.9 %, -4.0 / -3.1 %. Eight more boards of the review (random zones, hatch, overlapping fills, an outline through copper, two via boards, a metal block, four layers of partial copper, a heater over a copper edge), before and after against the FVM at 0.25 mm: validation 51.4. Heat balance below 4e-11 W, a board with no power stays at the ambient exactly with `h_side` 50 (outline, vias, block, four layers), a symmetric board symmetric to 1.5e-10 K.
* **Memory**: re-measured in fresh processes (100 x 75 mm, four layers, 0.5 mm, planes and stripes, FVM and FDM): estimate / peak 1.34 to 1.49, growth 140 to 180 MB under the term of 314 to 338 MB (validation 51.3).
* **Outline spread**: documented in validation 51.4 (one placement, the imported outline treatment); the worst board falls, so no warning is needed.
* **Numbering**: validation 51 is free on `development` (whose sections run 48, 50, 49: an older order, left) and in the other worktrees.

## Findings

1. **Defect in the program, fixed**: the search for the cell that fits (`memory.cell_that_fits`) left out the drawn raster term, so the cell named by a refusal or by Auto was refused again by `check` (50 of 68 limits tried on the 100 x 75 mm four-layer board; 0.4 mm, 1668 MB against 1650 MB). Now `extra=drawn_run_bytes` at every cell tried. Test `test_the_cell_that_fits_is_not_refused_again[fvm|fdm]` (fails before).
2. **Defect in the program, fixed**: cells that are not square (a board side that is not the same whole number of cells) got square pixels of dx / 10, which the import's rule took as 12 pixels per cell, sampled: cell fill off the exact share by up to 0.017 and 1.44 times the pixels the memory law counts. The raster is now built on the grid (`DrawnCopper(grid=)`, `face_coverage`, `fill`); the fill is exact to 3e-8; heater means move at most 0.26 %; square cells bit for bit unchanged. Test `test_cells_that_are_not_square_read_the_exact_fill_on_ten_pixels` (fails before). `CopperSource.lateral` reads the coverage through the new `face_coverage` (same code for imports; the imported-copper tests pass).
3. **Wrong document, corrected**: validation 51.4 said vias on a partly drawn plane are not changed. Vias on a drawn copper edge move a lot at a coarse cell: FVM +1.3 % -> +10.6 % at 1 mm when vias and edges sit on a cell line (+4.8 % at 0.5 mm), FDM -2.0 % -> +6.1 % at 1 mm with the copper shifted 0.37 mm; hot (safe) side, falls with the cell, the imported copper's own behaviour, and the partial-copper via warning fires on every such via. Recorded as a limit (A30 follows).
4. **Stale document, corrected**: validation 51.3 said the cell that fits is optimistic (finding 1); the pending file cited validation 49 (now 51); the review's numbers added to 51.3 and 51.4; the refreeze note in 51.2 (the new boards must be in `expected_shifts_<version>.json`).
5. **Limit kept**: overlapping zones of different fills are read largest fill first (the maximum rule only where two zones share a pixel in part; the earlier review measured 0.0044 of a cell).

## Not verified

The finite-element references (read from the research README, not re-run); boards above 100 x 75 mm for the memory law in this review; transients beyond the frozen times; a real display; the whole battery (the tester's).

## Open decisions for the maintainer

* A board with imported copper keeps the earlier (cooler, up to -8 % at 1 mm) path for its drawn layers, without a warning: accept as a stated limit, or add a warning or the drawn source for the non-imported layers later.
* The vias on a copper edge (finding 3): accept the hot first-order error with the existing warning until A30, as for imported copper.
* The refreeze of 2.8.0 must add the three new harness boards to the expected-shifts table (they are in `board_names()`).
