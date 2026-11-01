# What could change in the program or the documents, depending on the results

Nothing in `pcbthermal/`, `tests/`, `examples/`, `ico/` or the project documents is touched by this folder, and nothing has been run: **the measured impact of every proposal below is unknown until the studies run**. Each row says what the result would have to be (the criteria of README 3) and what follows. A change to the program is measured on a copy first and implemented only after the maintainer decides, on a `fix/` or `feature/` branch off `develop` with the whole battery.

## 1. S1, measured vias

| Outcome | Proposal | Branch and cost | Documents |
| :-- | :-- | :-- | :-- |
| B1 fails (the solver differs from the closed form) | none: a defect of this folder, fixed with a regression test and the comparison repeated | this branch | none |
| B2 passes for a group and C1, C2 pass | a first row against a measurement in `docs/validation.md` (a table of the four arrangements: measured with its plot uncertainty, closed form, solver, five models, the boundary-condition ratio), with the limit "isothermal faces cannot be imposed; the translation uses the solver" | `docs/` | `validation.md` (new row), `theory.md` 2.6 (one sentence: checked against a measurement), bibliography status of [SoleymaniKoohbanani] |
| B2 fails for the straight 1.25 mm group (expected from the arithmetic, README 5) | report the group as not usable and why (Table 9 diameters of sample 7 give 10.02 against a measured 7.0 and the thesis's own curve at about 8); no change | none | the row says "three of four groups" |
| C1 fails for fvm and fdm on a sparse array (2.5 mm pitch) with the foil condition | the via footprint rule is the first suspect (`docs/theory.md` 2.6: 0.78 r_v target radius, footprint of cells at a cell of pitch/8); a `fix/` proposal only after the grid sweep shows the error does not fall with the grid; a note in the warning about a coarse cell otherwise | `fix/` or `docs/` | `theory.md` 2.6 limits |
| C1 fails for analytic or lumped | recorded as the known limits of those models (earlier folders: +3 to +5 % and +9 to +11 %); no change | none | `validation.md` row |
| C2 fails for every usable group with C1 passing | C2 is derived (B2 and C1 combined), so with C1 passing it can only fail where the measurement is far from equation 28/29 already: the thesis's samples (wall, foil, thickness not stated), not the program; a note, not a change | `docs/` | `validation.md` |
| D1 passes (not expected: the paper's own CFD contrasts are 2.2 to 6.3 times smaller than the measured ones, README 2.2) | Table II rows (the contrasts) in `validation.md` with the sweep stated | `docs/` | `validation.md` |
| D1 fails or the sweep changes the verdict (expected) | Table II is "not informative at this level"; not quoted; not evidence against the via rule | none | none |

## 2. S2, thick anisotropic laminate

| Outcome | Proposal | Branch and cost | Documents |
| :-- | :-- | :-- | :-- |
| L1 fails | the 3D reference is not a reference: find whether it is the pixel, the slabs or the equation (the tests of the limits are in the folder); the earlier laminate-nodes numbers are then re-examined | this branch, then `research/laminate-nodes` | the laminate-nodes README, `validation.md` 21.2 |
| L1 passes, L2 passes | the rule stays; theory 1.4 gets the published check (equation 50 against the reference, to the printed agreement) and the limit text of the thick laminate | `docs/` | `theory.md` 1.4, `validation.md` 21.2, bibliography [Muzychka2004Orthotropic] |
| L2 fails, L3 passes | change the defaults of `laminate_s_max_mm` / `laminate_n_max` (or make n depend on the thickness): the rule constants in `pcbthermal/laminate.py` (S_MAX 0.4 mm, N_MAX 4) and `SolverOptions`, with the cost (unknowns times n, memory estimate of the guard) measured by the study; it moves every board with patterned copper, so the frozen-numbers file is refrozen in the same branch | `fix/laminate-rule` | `theory.md` 1.4, `models.md`, `versions.md`, `validation.md` 21, the frozen record, `CHANGELOG.md` |
| L2 fails, L3 fails | only the limit text: the error map of the study (thickness, source size, anisotropy, film) goes into theory 1.4 and the warning for a part on bare laminate | `docs/` | `theory.md` 1.4 |
| L4: solid3d above 3 % or analytic above 15 % | recorded; a 3D solid defect would be a `fix/` after the reviewer | `fix/` | `validation.md` |

## 3. Impact on the existing documents when nothing fails

`docs/validation.md` gains at most two rows (a measurement; a published closed form on a laminate) and the bibliography statuses of [SoleymaniKoohbanani] and [Muzychka2004Orthotropic] go from "read" to "read and reproduced". The text for them is in `docs/validation-rows.md` (a template; the numbers are to be filled from the printed tables of the runs).

## 4. Risks

* A study that is not run on a quiet machine: the program's memory guard may refuse a board and the table prints the refusal; none of the runs exceeds 3 GB by the estimate of README 4.5, which is from earlier folders, not measured.
* A two-layer board with no copper drawn (S2 bare) is accepted by all five models (a trial of the review, README 4.3), so the closed-form anchor holds for the program.
* A verdict on the test-bed condition rests on the translation by the solver's ratio; a program value near the measurement after it is not proof that the program's condition matches the test bed (the solver puts the effect of the condition at 1.1 to 7.3 %, README 5).
* The reviewer's pre-run corrections (README 9) changed how S2 reads the temperature (at the face, in the reference and in the program) and how S1 part D turns a via contrast into a psi_ta contrast (the exact network); the outcomes above refer to the corrected scripts.
