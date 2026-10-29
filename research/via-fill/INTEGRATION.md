# Program defects found by the review of the via fill, and the corrections proposed

The via fill itself is in the program (2.4.0). The review (README sections 4.4 to 4.8 and "Review") found three defects around the via model; they are measured here and **not** corrected in `pcbthermal/` (this is a research branch). Each needs a `fix/` branch off `develop` (executor, reviewer, maintainer) and the maintainer's decision.

## 1. The FVM and FDM via is not grid-convergent (fine cells)

**What.** `fvm.py` adds the barrel conductance `k_Cu A / d` to the one cell that holds the via centre; `fdm.py` to the nearest node. A source or sink in one cell of a five-point stencil acts like a hole of radius `0.198 Δx` (Peaceman 1978). For a 0.3 mm via that radius equals the real one at Δx ≈ 0.76 mm; on finer cells the model adds a constriction `ln(r_v / 0.198 Δx) / (2π S)` per via end that does not exist, and the result drifts by a constant amount at every halving of the cell instead of converging.

**Measured** (`scripts/study_via_model_checks.py`, part 4, README 4.6): via-array board, gain of a copper fill −4.78, −4.38, −3.98, −3.64, −3.34 K at 1, 0.5, 0.25, 0.125, 0.0625 mm, against −4.46 / −4.44 K by the independent solver with resolved barrels; open-via rise 40.39 to 41.65 K (+3 %) against 40.4 to 40.5 K. Example board: gain −4.49, −3.89, −3.59 K at 1, 0.5, 0.25 mm; the board without vias settles (94.67, 94.71, 94.72 °C). `docs/validation.md` 2.1 reads the example board's 85.81, 85.87, 85.95 °C as converging; the growing increments are this effect.

**Who is affected.** Any board run at cells below about 0.5 mm with vias: the Gerber boards of `research/gerber-models` (fine cells), small parts with via arrays, the power calculator's datasheet boards. At the default 1 mm and at 0.5 mm the error is 0.1 to 0.3 K of a 4.5 K effect.

**Correction proposed (to choose).**

* (a) *Peaceman well index*: connect each via end to its cell through `G_c = 2π S / ln(r_eq / r_v)` with `r_eq = 0.198 Δx` while `r_eq > r_v`; for `r_eq ≤ r_v` (fine cells) spread the via over the cells its disc covers (area weights), so that the constriction is the real one. Cheap, one function, keeps the matrix structure.
* (b) Always spread the via over the cells of its disc (plus a minimum of one cell): simpler, correct on fine cells, but at 1 mm the via becomes a point again (no change there, the current behaviour is close to right).
* Test: the via-array board of `study_via_model_checks.py` against `layered3d.py` with resolved barrels, gain within 0.1 K from 1 mm to 0.0625 mm; and the existing example-board tables re-run (they move by up to 0.3 K at 0.5 mm).

## 2. The 3D solid cuts a via larger than its cell

**What.** `solid3d.py` sets `via_frac = min(Σ A_via / A_cell, 1)` per cell. A copper fill (or several vias in one cell) larger than the cell loses the excess copper: a 0.3 mm copper fill keeps 88 % at 0.25 mm cells, a 0.5 mm copper fill 32 % (README 4.7). The 3D solid is the reference of several studies; on fine cells it would read too hot with copper-filled vias.

**Correction proposed.** Spread the via area over the cells of its disc (as in 1 b) before clipping, and warn if a cell is still over 1 (vias closer than their diameter). Test: a 0.5 mm copper fill at 0.25 and 0.5 mm cells gives the same series conductance through the board.

## 3. "Finished hole diameter" is the wrong label

**What.** `Via.thermal_area` takes the diameter as the drill (plating inside it: `r_in = d/2 − t`), the convention of the thermal-via article used as the source of 192 K/W. The tooltip (`gui/tips.py`, key `diameter`) and the docstring of `Via.diameter` (`model.py`) call it the "finished hole diameter", which on a fabricator's drawing is the hole after plating. A user who types the finished hole of the drawing gets 18 % less copper than the board has (0.3 mm finished hole: 162.8 instead of 192.4 K/W open, 43.2 instead of 58.8 K/W copper-filled).

**Correction proposed.** Change the label to "Drill diameter of the via (the plating is inside it; finished hole = drill − 2 × plating)" in the tooltip, the docstring, the user guide (Via row) and `docs/models.md`; no change of the numbers. Alternatively take the finished hole and add the plating outside (changes every result with vias by up to 15 % of the via resistance; needs the reviewer and a note in the CHANGELOG). The Gerber reader gives drills, which supports keeping the drill.
