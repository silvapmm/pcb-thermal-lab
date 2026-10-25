# Text for the project documents (from the review)

The review of `research/outline/` (README section 7) found numbers and statements in the project documents that the re-run does not support. `docs/` and `pcbthermal/` are not edited on a research branch; this is the replacement text, to be applied on `develop` by the maintainer.

## 1. `docs/validation.md`, section 13

The table of the section is already the corrected one (`develop` refreshed it with the edge fix; it equals what `outline_rectangle_study.py` prints now). The rows and the means quoted below are from that re-run (mean absolute error of the 1.1 × box: 14.1 / 13.3 %).

Replace the bullets under the table, except the one on the edge of the outline (already in the section and correct), with:

* Enlarging the box (the idea of growing outwards) is the worst choice in 29 of the 30 model-and-layout cells (5 to 35 % too cool: more area means more convection); the exception is the Lumped model on the rounded board with the parts at the centre. Shrinking to the same area is the best on average (mean absolute error, Lumped / Analytic: bounding box 9.2 / 7.7 %, same area 5.7 / 2.9 %, 1.1 × box 14.1 / 13.3 %). Its error is mostly on the cool side, not always: up to +2.9 % (ellipse, parts at the centre).
* For a strongly cut shape (ellipse, L, T; area ratio below 0.8) the bounding box ignores 22 to 33 % of the board and is 6 to 29 % cool; the same-area rectangle brings parts away from the edge to within 0.4 to 2.9 %.
* Where it fails: a part near the edge of the real board or in the arm of a T has less board to spread into than the scaled rectangle gives it: Lumped 6 to 18 % cool, Analytic 0 to 16 %. For nearly rectangular outlines (chamfer, rounded: area ratio above 0.95) the three boxes differ by a few percent either way and the same-area box is not better than the bounding box (Lumped 3 to 5.5 % cool away from the edge). Scaling about the area centroid of the outline instead of the box centre gave no consistent gain (tried, not kept).

Add after the bullets:

* Independent check (`research/outline/scripts/study_disc_reference.py`): on a round board 80 mm across with a centred round part, a radial solution of the same layered model puts the FVM within 0.5 % of the maximum rise at 1 mm (0.1 % at 0.5 mm), the 3D solid within 0.01 %, and the Lumped and Analytic models on the same-area square at +2.2 % and +0.5 %.

## 2. Docstring of `Problem.equivalent_rectangle` (`pcbthermal/model.py`)

"within 0.2 to 3 % of the temperature rise for a circle with parts away from the edge, against 6 to 10 % too low with the bounding box" -> "within 0.4 to 2.9 % of the temperature rise on an ellipse or a T with the parts away from the edge, against 6 to 10 % too low with the bounding box on the ellipse".

## 3. Edge loss of an outline side on a grid line (defect, now corrected in the program)

This section proposed a correction on a `fix/` branch. The program has it: `geometry.edge_length_per_cell` nudges every sample towards the inside of the board and `geometry.edge_length_on_board` also gives the edge of cells taken as off the board to the nearest cell on the board (`docs/validation.md` sections 13 and 20, `CHANGELOG.md` "Outline edge on grid lines and thin slices"). Nothing is left to apply here. `research/outline/scripts/study_edge_on_grid_lines.py` measures it on the current program: a T of 60 mm keeps 240 of 240 mm of perimeter (it kept 170 mm with the old rule, 210 mm upside down), its time constant is 104.85 s as in closed form (it was 106.72 s), and the T and its mirror image give the same FVM, FDM and 3D-solid maximum (93.009, 92.944 and 93.393 °C).

**One remaining point for `docs/validation.md` section 13**: its bullet on the edge says that the thin-slice loss is 2 to 6 % of the perimeter at every cell size; the outline folder's script measures 0.7 to 3.3 % on four shapes (a 128-gon disc, an ellipse, a square turned by 20 degrees), so the program's range comes from a wider sweep that this folder did not repeat.
