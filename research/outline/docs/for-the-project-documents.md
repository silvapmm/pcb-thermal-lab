# Text for the project documents (review of 2026-10-24)

The review of `research/outline/` (README section 7) found numbers and statements in the project documents that the re-run does not support. `docs/` and `pcbthermal/` are not edited on a research branch; this is the replacement text, to be applied on `develop` by the maintainer.

## 1. `docs/validation.md`, section 13

Replace four rows of the table (re-run on the program at `0ea5f07`):

| Outline | Parts | Area ratio | FVM Tmax | bounding box | same area (used) | 1.1 × box |
| :-- | :-- | --: | --: | --: | --: | --: |
| ellipse | centre | 0.783 | 114.3 | -7.4 / -5.8 | +0.8 / +2.9 | -9.9 / -11.5 |
| T | centre | 0.667 | 123.4 | -15.9 / -14.5 | -1.7 / -0.4 | -18.2 / -19.7 |
| chamfer | centre | 0.964 | 110.1 | -2.9 / -1.2 | -3.4 / +0.4 | -5.5 / -7.2 |

(The fourth change is the T centre bounding-box cell, already in the row above.) The other rows are unchanged.

Replace the first three bullets under the table with:

* Enlarging the box (the idea of growing outwards) is the worst choice in 29 of the 30 model-and-layout cells (5 to 35 % too cool: more area means more convection); the exception is the Lumped model on the rounded board with the parts at the centre. Shrinking to the same area is the best on average (mean absolute error, Lumped / Analytic: bounding box 9.2 / 7.7 %, same area 5.7 / 2.9 %, 1.1 × box 14.2 / 13.3 %). Its error is mostly on the cool side, not always: up to +2.9 % (ellipse, parts at the centre).
* For a strongly cut shape (ellipse, L, T; area ratio below 0.8) the bounding box ignores 22 to 33 % of the board and is 6 to 29 % cool; the same-area rectangle brings parts away from the edge to within 0.4 to 2.9 %.
* Where it fails: a part near the edge of the real board or in the arm of a T has less board to spread into than the scaled rectangle gives it: Lumped 6 to 18 % cool, Analytic 0 to 16 %. For nearly rectangular outlines (chamfer, rounded: area ratio above 0.95) the three boxes differ by a few percent either way and the same-area box is not better than the bounding box (Lumped 3 to 5.5 % cool away from the edge). Scaling about the area centroid of the outline instead of the box centre gave no consistent gain (tried, not kept).

Add after the bullets:

* Independent check (`research/outline/scripts/study_disc_reference.py`): on a round board 80 mm across with a centred round part, a radial solution of the same layered model puts the FVM within 0.5 % of the maximum rise at 1 mm (0.1 % at 0.5 mm), the 3D solid within 0.01 %, and the Lumped and Analytic models on the same-area square at +2.2 % and +0.5 %.

## 2. Docstring of `Problem.equivalent_rectangle` (`pcbthermal/model.py`)

"within 0.2 to 3 % of the temperature rise for a circle with parts away from the edge, against 6 to 10 % too low with the bounding box" -> "within 0.4 to 2.9 % of the temperature rise on an ellipse or a T with the parts away from the edge, against 6 to 10 % too low with the bounding box on the ellipse".

## 3. Edge loss of an outline side on a grid line (defect, for a `fix/` branch)

**What is wrong.** `geometry.edge_length_per_cell` gives every sample of the outline to the cell that contains it (`x // dx`, `y // dy`); a sample on a cell border goes to one side by the floor and by floating-point rounding. `fvm.Network` (lines 119 and 169) and `solid3d` (line 236) multiply the result by `active`, so a side that lies on an interior grid line with the board on the other side loses its edge loss. The FDM is not affected (it shifts the outline by half a cell, onto its node lines).

**Measured** (`research/outline/scripts/study_edge_on_grid_lines.py`): a T on a 60 mm box with all its sides on grid lines keeps 170 of its 240 mm of perimeter in the FVM (210 mm upside down); the board time constant reads 106.72 s against 104.85 s in closed form; the FVM and the 3D solid give 0.31 K (0.5 % of the rise) between the T and its mirror image, the FDM gives the same number for both. On the outline study only the L row moves (0.19 K).

**Proposed correction.** Nudge every sample a small distance (for example 1e-3 of a cell) towards the inside of the polygon before it is given to a cell (the inside is on the left of every side of a counter-clockwise polygon); the prototype in the study restores the closed-form time constant exactly and makes the mirror images agree to the last digit. Regression test: the T and its mirror image give the same FVM and 3D-solid maximum, and the FVM edge conductance of an outline equals `h_side · slab · perimeter`. `docs/theory.md` needs no change (it already states the edge length inside the cell).

**Not done here:** the correction itself (research branch), and any check of the GUI or the plots, which do not use this function.
