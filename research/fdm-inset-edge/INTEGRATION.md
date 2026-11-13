# Integration: faces of the FDM from the cell fill

**Status: implemented.** Adopted on `fix/fdm-copper-edge-faces` (reviewed: go, merged into `develop` for 2.7.0): `pcbthermal/fdm.py`, `Network._copper_face_sheets` and the
switch `face_fill` of `fdm.Network` and `fdm.solve_steady` (default on; `False` is the harmonic mean of the nodal sheets), `FACE_FILL_TOL`; `docs/theory.md` 3, `docs/validation.md` 47,
`docs/versions.md`, `CHANGELOG.md`; tests `tests/test_fdm_copper_edge_faces.py`; frozen numbers: the pending file `tests/regression/data/pending/fdm-copper-edge-faces.json` (21 FDM records,
7 times to 63 %). Differences from the prototype below: only the faces whose nodal fill differs from the face fill are replaced and only with the harmonic mean (uniform and hatched copper
bit-identical, the tiny full-copper moves of section 3 do not happen), negative faces clipped. The text below is the proposal as written, with the corrections of the review marked.

## 1. Recommendation (as proposed)

Adopt `face_fill` in `pcbthermal/fdm.py` on a `fix/fdm-copper-edge-faces` branch off `develop`, in 2.7.0 together with the planned refreeze, and keep the wording of the warnings (section 4)
until the reviewer has re-run the numbers. Evidence for the decision (README): against the finite-element limit of the 10 mm plate the copper-inset error falls from -3.5 / -7.7 % to -1.5 /
-3.0 % (200 / 1000 W/m2K, 0.25 mm) and from -5.1 / -12.2 % to -2.3 / -4.5 % at 0.5 mm; against the independent 3D solver every copper-edge board of validation 41 gets closer and none
overshoots (**corrected by the review**: true for those boards, not where the copper reaches a turned or curved outline, where the FDM moves 0.05 to 0.5 point further from the finite elements; README 3.3) (plate_pad -7.31 -> -5.36 % and -4.32 -> -2.86 % at 1 / 0.5 mm; gap board -5.49 -> -3.52 %); two independent references and the FVM agree on the sign. The correction is small
(about 25 lines), changes no unknown, matrix pattern, capacity, source or via, and is bit-identical for uniform copper.

## 2. What changes in the program

* `fdm.Network.__init__`: keep the cell fill (`self._cell_fill`) and, with the laminate rule and drawn copper, replace the in-plane face arrays of the copper layers by
  `(A_face + B f_face) x mean cover` (`research/fdm-inset-edge/lib/fdm_variant.py`, `_face_sheets`, a tested prototype). Laminate-node faces, imported-copper faces and boards with
  a metal block keep the earlier code. Clip negative faces to zero.
* `docs/theory.md` (FDM face section), `docs/validation.md` 41 (the residual -2 to -7 % becomes 'the copper-edge residual of the variant is ...'), the table of 41.2 (re-measure the three
  FDM rows), `docs/models.md`: the sentence on the FDM copper edge.
* The user guide and the warning texts that quote the FDM at a copper edge (the partial-copper via warning, the bare-pad warning).

## 3. Measured impact (`study_harness_shift.py`)

FDM steady records that move on the 17 harness boards (2 / 1 / 0.5 mm; with the prototype 36 of 48 runs, the 12 that stay are `plate_uniform`, `one_layer_full`, `finned_block`, `hatched_copper`;
**with the adopted code 18 of 48 runs, 21 records with the three skipped ones**, README 6):
`plate_pad` +8.19 / +6.55 / +4.81 K, `one_layer_pad` +1.00 / +1.08 / +0.91 K, `two_layer_partial` +0.117 / +0.393 / +0.314 K, `part_top_path` +0.128 / +0.249 / +0.212 K,
the example boards -0.0095 / +0.0077 K (2 / 1 mm), `example_cut_to_T` -0.0104 / +0.0083 K, the other full-copper boards 1e-5 to 2.6e-3 K with the prototype and 0 with the adopted code. Not measured: the three boards of about 150 000
FDM unknowns at 0.5 mm, and the times to 63 % (they use the same `Network`; the capacities do not change, so the shifts follow the resistances only, unverified). The frozen test must
be refrozen for these FDM records in the same commit (`make_pending.py`, then folded at the refreeze); no other model moves.

## 4. If it is not adopted: limit and warning text

Draw the limit as a stated limit of the FDM: with the copper edge inside the board the FDM reads the hottest rise 1 to 3 % cool at 10 W/m2K, 3 to 5 % at 200 and 6 to 12 % at 1000 W/m2K
(plate, 0.5 to 0.25 mm), the heater mean of a 20 mm square with the copper 1.2 mm in 3 to 7 % cool at 0.6 to 1 mm and 6 to 17 % at 1000 W/m2K (turned and shifted: 7 / 14 % at 1 mm), against
1 to 3 points less for the FVM; the via effect 4 to 24 % low at 0.25 to 0.5 mm (that is the colder base field). With the variant these become about half. The FVM is the model to use
with a strongly cooled edge.

## 5. Risks

* A hotter FDM on partial-copper boards: the FDM moves toward the FVM and the independent solver, never past them in the tests, but a board with a copper edge between two parts of
  different layers was not tried; several parts, imported copper and metal blocks were not run.
* The variant leaves the cut-cell mixing of a copper edge inside a cell (the FVM has it too, up to 10 points at 1000 W/m2K) and the wall term (laminate sub-gaps) alone.
* The finite-element reference was quoted, not re-run; the decision should not rest on it alone: the independent 3D solver numbers (README 5) and the FVM at 0.0625 mm (README 3.2) agree.
