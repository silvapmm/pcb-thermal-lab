# Integration: the plate level of the vertical faces

What would enter the program, the measured impact, what does not change and the risks. The program is not touched from this branch; every number is in `README.md` (section numbers in brackets) and was measured on a copy in memory (`lib/levels.py`). Decisions are the maintainer's (section 6).

## 1. What the study found, for the decision

* The exact laminar boundary layer of an isothermal vertical plate in air is `Nu = 0.5157 Ra^(1/4)` (own solver; Ostrach's Table I reproduced to 0.02 %) [3]. The `Ra^(1/4)` term of the Churchill and Chu **laminar** form is 0.28 % below it, and its `0.68` is the leading-edge term: the program's `laminar` form already **is** "the exact boundary layer plus the leading edge" [3, 4].
* A full 2D numerical plate (own solver, grid and domain checked, energy balance 0.96 to 1.01) says the real mean `Nu` is, against the program's two forms [6]:

| Ra | numerical / laminar form | numerical / general form | numerical / 0.59 Ra^(1/4) |
| --: | --: | --: | --: |
| 1e4 | 0.978 | 1.048 | 0.965 |
| 1e5 | 0.982 | 1.048 | 0.920 |
| 1e6 | 0.987 | 1.010 | 0.896 |
| 3e6 | 0.989 | 0.980 | 0.890 |
| 1e7 | 0.992 | 0.941 | 0.885 |
| 3e7 | 0.994 | 0.900 | 0.882 |

  (the last two rows are good to 3 to 4 %, from the energy balance). So over the range of the boards (`Ra` 6e4 to 3e7 for 40 to 200 mm at 10 to 60 K) the laminar form is the closest level (high by 0.6 to 2.2 %), the all-range form is 5 % low at the small boards and 6 to 10 % high at the large ones, and `0.59` is 4 to 12 % high.
* The published air measurements (three sets, plot values) scatter by +-15 % and cannot tell the forms apart [5].
* **The choice matters little for the rise**: at most 2 % between the two forms of Churchill and Chu on a 40 mm board (0.4 % from 100 mm up), 2 to 4 % for `0.59` (7.5 % convection only), 2.2 to 3.6 % on the finned block of `fin-channel` [7, 8]. The radiation, which does not depend on the level, is about half of the total coefficient.

## 2. Proposal A: two options for the vertical face (a change of the program's choice; small)

**What.** `Board.natural_form` keeps its two values, with names and a default that follow the evidence:

| Option | Value | Name in the interface | What it is |
| :-- | :-- | :-- | :-- |
| 1 | `laminar` | "Boundary layer (Churchill and Chu, laminar)" | the exact laminar boundary-layer coefficient plus the leading-edge term; within 0.6 to 2.2 % of the 2D numerical plate over `Ra` 1e4 to 3e7; right below `Ra` 1e9; the recommended default |
| 2 | `general` | "All Rayleigh numbers (Churchill and Chu)" | the single formula that joins the laminar and the turbulent regime; 5 % lower `h` than the numerical plate at `Ra` 1e4 to 1e5 (conservative for the rise), 6 to 10 % higher at 1e7 to 3e7; the right one above `Ra` 1e9 |

`0.59 Ra^(1/4)` and the composite's plate limit are not offered: it is 14 % above the exact boundary layer and 4 to 12 % above the numerical plate, and it is not a boundary-layer result.

**Default.** Two defensible choices, for the maintainer: (a) **change the default to the laminar form** for new projects (the closest to the numerical plate; changes the rise of a vertical board with computed `h` by -0.1 to -2 % (small boards) and +0.3 % at most for large ones); (b) keep `general` (no change of any number; conservative for boards under 100 mm; 6 to 10 % high in `h` above `Ra` 2e6, that is for 150 mm faces and taller, where it makes the board cooler than the numerical plate). The study recommends (a), with the old files (no key `natural_form` in the JSON) read as `general` so that their results do not change (`model.py` reads `b.get("natural_form", "general")` today and keeps doing so).

**Automatic switch (optional).** Above `Ra` 1e9 the laminar form is -25 % at 1e9 against the all-range form and lacks the turbulent rise; a value `auto` (laminar below `Ra` 1e9, all-range above) would remove the need to choose. Not measured here (no board of the program has `Ra` above 5e7); the program already warns above 1e9 for the laminar form.

**Measured impact** [7]: example board (100 x 80 mm, vertical, computed): -0.4 %; reference board: -0.1 %; two-layer 40 mm boards -2.0 / -1.8 %, 60 mm -1.2 / -1.0 %, 100 mm -0.4 / -0.2 %, 150 mm -0.1 / +0.1 %, 200 mm +0.1 / +0.3 %. Horizontal and manual-`h` boards: unchanged (they do not use the correlation).

**Test cases for the adoption** (values to the digit printed by `lib/levels.py`, Pr and properties of the program, convection only): face 40 mm at 10 / 30 / 60 K above 20 degC: `Ra` 6.19e4 / 1.59e5 / 2.56e5, `h` general 5.36 / 6.94 / 8.14, laminar 5.74 / 7.36 / 8.57 W/m2K; face 100 mm: `Ra` 9.67e5 / 2.49e6 / 3.99e6, general 4.29 / 5.69 / 6.75, laminar 4.39 / 5.67 / 6.63; face 200 mm: `Ra` 7.74e6 / 1.99e7 / 3.19e7, general 3.79 / 5.11 / 6.11, laminar 3.63 / 4.71 / 5.51. The Nu of the 2D plate (`study_plate2d.py`) at `Ra` 1e4 / 1e5 / 1e6 (5.694 / 9.651 / 16.72) as a regression for the laminar form (within 2.5 %).

**Warnings.** The program's warning for the laminar form above `Ra` 1e9 stays. Add (a) below `Ra` about 1e3 (a face about 10 mm high at 10 K has `Ra` 1e3) the note "boundary-layer regime ends: conduction and the edges dominate" (the laminar form is +4 % over the general one at 1e3 and no study here covers it); (b) nothing for 1e4 to 3e7 (the range of the boards).

**Risk.** Small: the rises move by 2 % at most; any saved result of a vertical board with computed `h` changes by that when the default changes (a note in the changelog); the form is chosen per board, so a user who wants the old numbers selects the all-range form.

## 3. Proposal B: the channel correction multiplies the level in use (an answer to `fin-channel`)

The channel effect measured against the plate limit of the same level is +24 / +11 / +4.3 / +1.7 % of the rise at 3.5 / 4.5 / 5.5 / 6.5 mm with the 0.59 limit and +22 / +8.8 / +3.3 / +1.3 % with the exact limit [8]: it does not depend on the level to the precision of the study, and it vanishes from 14.5 mm. So `fin-channel/INTEGRATION.md` proposal B (the factor `phi(Ra_b)` on the coefficient the program already has) **stays as proposed and applies to whichever plate level the board uses**; the composite itself must not replace the program's coefficient, because its plate limit (0.59) would lower the rise of the block by 5 % at wide gaps (71.4 K against 75.5 K at 6.5 mm) for a reason that is not the channel. The "10 to 30 % of the typed coefficients" remembered in `block-and-fins` is not touched by this study.

## 4. Documents that would change on adoption

`docs/theory.md` section 8 (the two forms: say that the laminar form is the exact boundary-layer coefficient plus a leading-edge term, and which one is right where; the sentence "the laminar form is +7 % ... -25 %" is kept), `docs/models.md` (the names of the two options), `docs/validation.md` (section 22, the laminar check: add the 2D numerical plate), the user guide (`pcbthermal/help/index.html`, the natural-convection form), the tooltip of the form (`pcbthermal/gui/tips.py`: what each option is and where it applies), `tests/test_help.py`, `tests/test_tooltips.py`, `CHANGELOG.md`. The texts are in `docs/`.

## 5. What is not proposed

* A change of the horizontal-face correlations (not studied), of the radiation or of the film temperature (Sparrow and Gregg's 0.38 reference temperature for variable properties was only seen in a summary).
* The 2D solver or the similarity solver in the program (they are checks).
* A threshold or a check on the board edges (a 3D board entrains air from the sides: a narrow board has a higher mean coefficient than the 2D plate, not studied).

## 6. Decisions for the maintainer

1. The two options and their names (section 2), and whether the default of new projects becomes the laminar form (the study recommends it) or stays the all-range form.
2. Whether an `auto` value (laminar below `Ra` 1e9, all-range above) is wanted.
3. The warning below `Ra` 1e3 (small faces) and where to put it (post-run, with the other plate warnings).
4. Confirm that the composite's 0.59 is not offered, and that the channel correction (proposal B of `fin-channel`) multiplies the level in use.
5. Whether the 2D numerical plate, which is a result of this investigation and a check of the form, should be listed as a source in `docs/validation.md`; it is not validated against a published finite-plate value (none was found).
