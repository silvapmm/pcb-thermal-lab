# Integration: drawn copper read as imported copper (FVM and FDM)

**What enters the program now: nothing.** `git diff development --stat -- pcbthermal tests examples ico` stays empty; the copy lives in `lib/patched.py` (subclasses of `fvm.Network` and `fdm.Network`) and in `lib/dc_cases.py`. This file is the design for a `fix/drawn-copper-faces` branch if the maintainer decides to adopt (README 8), with the measured impact of every proposal.

## 1. Recommendation

**Adopt in 2.8.0, FVM and FDM, as one fix** (item 5a of `docs/versions.md`), first in the serial order of the fixes (5a, A30, A18, A32/A40): it is the widest in the boards it touches and the others should be measured on top of it.

* Why: the drawn reading is the only unsafe-side FVM error above 3 % with no warning (README 3.1: -1.2 to -11.2 % at 1 mm and -3.3 to -6.6 % at 0.25 mm on the strong-edge boards; FDM -5 to -18 % at 1 mm), the cause is one rule (the faces, README 3.1 and 3.2), and the repair is code that already exists, tested and reviewed, for the imported copper (`copper.face_conductances`, mapping `faces`): no new numerical method.
* What it repairs: the faces of a layer cut by a copper edge (README 3: stripes -8.0 -> -0.6 % at 1 mm, inset square at 1000 W/m2K -2.6 -> -0.0 %, L -1.4 -> -0.0 %; FDM stripes -12.9 -> -1.8 %); on turned and shifted boards with an outline the mean error of the inset square at 1 mm and 200 W/m2K goes from -3.15 to -1.26 % and the stripes board from -11.8 to -2.6 % (README 4).
* What it does NOT repair (stated limits, to be kept in the documents): the laminate at the inset edge (1 to 3 % cool at fine cells, A16/A18/A34: with eight sub-gaps the same boards read -0.1 to -1.3 %), a small pad on bare laminate (4 to 5 % cool), the FDM at copper to the wall (-2.5 to -6.1 %), the hot first-order cut cell at 1 mm (+1 to +2 %).
* **What it costs** (README 4, 6): 2.5 to 4 times the time and +20 to +60 % memory on a 100 x 75 mm board with a cut-cell layer; **the scatter of the ten turned and shifted boards rises on 15 of 30 outline rows** (0.64 -> 1.25 % at `sq_in` 200 W/m2K 0.5 mm, 3.40 -> 6.38 % at `sq_pad` 1 mm), while the worst board falls on 24 and rises on 2 (`L_wall` 1 mm 1.16 -> 1.41 %).
* **Fall-back** if the maintainer does not want to move numbers: a warning (section 5 below).

## 2. What changes in the program

| File | Change | Measured / tested |
| :-- | :-- | :-- |
| `pcbthermal/copper.py` | new `source_from_zones(problem, nx, ny, width, height)`: for the layers of the problem that have a zone and at least one cell cut by a zone edge (`geometry.exact_coverage` summed over the zones, neither 0 nor 1 in some cell), a float32 coverage raster (0 to 255 scale, not stored, not quantised) at 10 pixels per cell side (even, at most `MAX_PIXELS_PER_CELL`), wrapped in a `CopperSource` whose `raster()` returns it (the `FloatSource` of `lib/patched.py`). Union of zones: the exact shares summed and clipped to the largest fill, as the copy does; the program's own zone rule is the maximum per sample, so overlapping zones of different fill need the maximum per pixel (to be written and tested: the copy does not do it) | README 4.1, 5; `tests/test_drawn_faces.py` |
| `pcbthermal/fvm.py` (`Network.__init__`) and `pcbthermal/fdm.py` | when `faces is None` and the problem has no imported mask: `faces = copper.source_from_zones(...)`; the zones stay in the problem (the via rim test, the checks and the metal blocks read them) | the copy equals a real import of the same zones to 5e-3 K (the 8-bit quantisation of the import) |
| `pcbthermal/memory.py` | the estimate for the FVM and FDM adds `FACES_BYTES_PER_PIXEL` x the pixels of the largest layer that needs a raster (the law of an import, already measured at 26 to 38 bytes per pixel) and the working set of one window batch; the verdict `ok / slow / refuse` stays the guard | to be measured on a large board (README 6: only 100 x 75 mm done) |
| `pcbthermal/laminate.py`, `viawell.py`, `api.py`, the Lumped, the Analytic, the 3D solid | NOT changed. They read the cell fill from `copper.problem_fill` (the 4 x 4 samples of the zones); the exact fill alone moves the FVM by 0.0 to 0.3 point (README 3.1) so it is left | not run in these models |
| `docs/theory.md` 1.7, `docs/validation.md` 40.4, `docs/versions.md` 5a, user guide (copper), tips | the text that says drawn copper reads cool: replaced by the new numbers and the limits of section 1; 40.4's gap is removed | by the maintainer agent |

**Choices that carry the numbers** (README 3, 5, 7):

1. **The mapping is `faces`** (flow on the reduced sheet, the imported default), not `lambda` (+2.4 to +4.5 % hot at 1 mm) and not `fill` alone (no change in the FVM, worse in the FDM: -31.9 % stripes at 1 mm against -18.3 % drawn).
2. **Ten pixels per cell side**: 16 differ by 0.1 to 0.5 point and cost twice, 4 keep about half of the gain at 0.5 mm.
3. **A raster only for the layers that have a cut cell.** A layer whose every cell is full or empty keeps the program's path (identical faces; no float32 rounding of 1e-7 K, which would move every frozen record past the 1e-8 K tolerance). This is the rule that keeps 94 of 102 FVM and FDM records bit for bit.
4. **The raster is float and never stored** (a hatch fill is exact; the 8-bit coverage of a stored import moved `hatched_copper` by 0.10 K).
5. **The imported layers win** over zones (as today); a mixed board (some layers imported, the others drawn) takes the zone raster only for the drawn layers.

## 3. Frozen numbers (pending file `drawn-copper-faces.json`)

Measured on the copy against the program as it is (`study_harness_shift.py`, `study_harness_t63.py`, README 7): **steady records that move, all at 2 mm**:

| record | change |
| :-- | :-- |
| `two_layer_partial|fdm|2` | +1.8655 K (U mean), +1.37 % of the rise |
| `two_layer_partial|fvm|2` | +0.1861 K |
| `example_cut_to_T|fdm|2` | +0.1360 K (U2 hottest) |
| `example_board|fdm|2`, `profile_board|fdm|2` | +0.1118 K (U1 mean) |
| `example_cut_to_T|fvm|2` | -0.0039 K |
| `example_board|fvm|2`, `profile_board|fvm|2` | -0.0015 K |

Times to 63 % that move by more than 1e-6 relative (14 of 40 part curves): `example_board` and `profile_board` FVM U1 +0.019 %, U2 -0.013 %, FDM U1 +0.31 %, U2 +1.12 %; `example_cut_to_T` FVM U1 +0.027 %, U2 +0.002 %, FDM U1 -0.105 %, U2 +0.58 %; `two_layer_partial` FVM +0.165 %, FDM -0.116 %. **No record at 1 and 0.5 mm moves**, and the 3D solid, Lumped and Analytic records do not move (not touched). Overlaps with other pending files (one record, one file): the example board and `example_cut_to_T` records at 2 mm are also moved by A30 (vias), A18 (small parts on bare laminate) and A32/A40 (FDM); the serial order 5a first means the later files are written after this merge and carry the records already moved.

**The frozen boards are blind to the effect** (copper edges on cell lines by design): the adoption should add to the harness the inset square (200 W/m2K), the stripes-and-pad board and the L-shaped copper at 1 and 0.5 mm, FVM and FDM, as new records (the harness is the release's, `releases/regression-harness/`; the maintainer decides).

## 4. Tests to write (on the `fix/` branch)

* The exact area of a zone raster against the polygon area (also an edge that cuts pixels) and the maximum-per-pixel union of overlapping zones of different fill; a hatch fill reads exactly.
* The adopted `Network` equals the same copper imported (FVM and FDM, to 5e-3 K at 1 mm) and conserves the heat to 1e-9 W; a constant field stays constant with `h_side` 10 to 1e5 (the matrix property of 40.3).
* Layers with no cut cell are bit for bit the program's earlier numbers (the 94 records), and a layer with one cut cell moves.
* The face across a copper edge equals the series of the copper and bare stretches of the window (the closed-form test of `tests/test_drawn_faces.py`).
* The stripes and inset-square errors against the finite-element values (frozen from README 2.1 with the reference stated; skip without the scratch environment) or against the converged program itself at 0.125 mm.
* The memory estimate holds on a 200 x 150 mm board with stripes at 0.5 mm (peak against estimate, the law of `memory.py`).
* A GUI stress scenario: a drawn board with stripes at 0.5 mm runs, with the warnings.

## 5. If the maintainer does not adopt: the warning

For the FVM and the FDM, live and after the run, when a drawn layer has a cell cut by a zone edge (the same test as `layers_with_cut_cells`): "Drawn copper whose edge cuts cells reads too cool (heater mean, against a finite-element reference): FVM 1 to 11 % at a 1 mm cell and 3 to 7 % at 0.25 mm with a strong edge film (200 to 1000 W/m2K), 0.2 to 1.3 % at 10 to 50 W/m2K; stripes 4 to 11 %; FDM 5 to 18 % at 1 mm and 3 to 8 % at 0.25 mm (README 3.1, 3.2). A finer cell does not remove it." The numbers are those of the boards of this study, a sample and not a bound.

## 6. Risks

* **The scatter** of the cut-cell outline boards rises (15 of 30 rows, README 4); an adoption that also changes the outline treatment (A32/A40) must re-measure it.
* **Memory and time on large boards** were measured only up to 100 x 75 mm (README 6); the guard must be fitted before the release (the law of imported copper is a starting point).
* **Overlapping zones with different fill** are approximated in the copy; the program's rule is the maximum per sample. A zone over a zone is rare, but a hatch zone drawn over a solid one on the same layer is possible: the implementation must use the per-pixel maximum.
* **Vias on a drawn partial plane**: the rim rule reads the zones (kept), but the via well reads the cell sheets built from the fill: no board of this study has vias, and the frozen via boards have aligned copper (they do not move). A30 comes after this fix for that reason.
* **The 3D solid, Lumped and Analytic keep the 4 x 4 fill**: a board read by all five models will differ by the faces in the layered models; the model-comparison documents must say so.
* **The finite-element references are extrapolated** (assumed second order, 0.1 to 0.35 % from the finest solve) and the four-layer board used 0.3 mm; the hatch has no resolved reference.
