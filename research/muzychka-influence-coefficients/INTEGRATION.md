# Plan: reproduce a published case, then run the models

Nothing here was run. The program is not touched by this folder; a proposal for the program, if any, would come only after the steps below.

## 1. Obtaining the paper (blocking for step 3 b)

The maintainer downloads the journal version (IEEE Trans. CPT 29 (3) 636-643, doi 10.1109/TCAPT.2006.880477) or the ITherm 2004 version through an institution into `papers/pdf/Muzychka2004Influence.pdf`. The OCR tool converts it; the reviewer compares the pages used with the page images; `[Muzychka2004Influence]` in `research/theory/BIBLIOGRAPHY.md` then gets equations, page numbers and the printed numbers (values read from a plot marked "plot").

## 2. Independent solver (`lib/`, to be written)

* `lib/influence.py`: the influence coefficients `f_ij` of Razavi (2016) eq. 2.72 built from the eccentric-source series of [Muzychka2003] (status R, eq. 11 to 31), adiabatic edges first; the edge-cooled form only after the paper is read.
* Checks of the solver itself (tests in `tests/`): reciprocity `f_ij = f_ji` to 1e-10 relative; the energy balance (bottom-face flux equals the total power) to 1e-9; the single-source self term against [Muzychka2003] eq. 27 as already reproduced in `research/gap-subdivision`; the whole field against the independent 3D solver `tests/helpers/layered3d.py` (the one that reproduced case 2 to 0.03 K in `research/muzychka-case2-analytic`) at a converged grid, within 0.5 % of the rise.

## 3. Cases and acceptance

* (a) Available now: [Muzychka2003] case 1 (a), two sources on a 300 x 300 x 10 mm plate (printed centroid and mean 84.97 / 80.56 and 108.43 / 101.81 C), and case 3, the cross of five sources (maximum 80.61 C, mean 78.87 C). Acceptance: the influence-coefficient sum within 0.05 K of each printed value (the precision of the table) and equal to the direct superposition of the single-source series to 1e-9 K.
* (b) After step 1: one case of the paper itself, preferably with edge cooling or a source-plane film. Acceptance: within the printed digits, or the difference explained.
* Then the program on the same board (FVM at 1, 0.5 and 0.25 mm, FDM, Lumped, Analytic with the Robin edge): the program reads the layer mean, the paper the surface; compare with the column mean of the 3D reference and with the surface, as `research/muzychka-case2-analytic` README 3 does (through-thickness term and face-film term apart). The independent hexahedral FEM of `research/independent-fem-edge` is the third reference.

## 4. What would be proposed

If the neighbour term `f_ij` is a cheaper or more accurate neighbour term than the Lumped superposition, a proposal with its measured impact; otherwise the case enters `docs/validation.md` as a published case. Decision for the maintainer: whether to open the study now with case (a) only, or to wait for the paper.
