# What could enter the program from this investigation (the investigation is closed)

Nothing here is needed for the program to be right on the boards it is made for: the five models agree with an independent 3D solver on a Cu / FR4 / Cu coupon (FVM, 3D solid and Analytic within 0.1 %, FDM and Lumped within 1.2 %) and the published cases are reproduced. Three optional proposals remain; none is implemented, and each one needs the maintainer's decision and a `fix/` or `feature/` branch off `develop` with the whole battery.

## 1. An input check for a thick, poorly conducting plate (small)

**Problem.** The layered models keep one temperature per layer, the mean through its thickness. For a plate of thickness `t` and conductivity `k` under a source of flux `q''` the surface under the source is hotter than that node by at most `q'' t / (2 k)` (README 4.6; less when the heat spreads sideways): measured 1.6 % of the rise for 10 mm of `k` 50 (bound 2.25 %), 8 to 9 % for 10 mm of `k` 10 (bound 14 to 15 %), against 0.0001 K for 35 um of copper. The program has no layer of that kind among the copper layers, but it does have heatsink blocks of 1 to 6 mm and the user can type any conductivity.

**Proposal.** A warning in `checks.py` when, for a heater on a block or on a layer, `q'' t / (2 k)` exceeds 5 % of the rise of the heater (computed after the run, from the heater power per area, the thickness and the conductivity of the layer or block under it). The text would say that the surface temperature under the source can be higher than the model shows, by up to that amount (the bound is reached when all the heat crosses the layer under the source; with sideways spreading the measured gradient was 0.6 to 0.8 of it).

**What does not change.** The models, the results and the interface.

**Measured impact** (`README.md` 4.8 C): on the 74 metal-block cases of the program the criterion is at most 0.42 % (a 3 mm steel block), median 0.04 %, so the check would **never fire on the cases the program is built for**; it is a safety net for a thick, poorly conducting layer typed by the user.

**Risk.** A false alarm on a thick copper block (the criterion is then tiny, so none); the criterion is a bound, not a correction, and must not be added to the result.

## 2. The laminar form of Churchill and Chu as an option (small, a decision)

**Problem.** The program uses the general correlation for a vertical board over the whole range. The same authors' laminar form (for Ra below 1e9, recommended by textbooks for laminar flow) differs from it by +7 % at Ra 1e4, +2 % at 1e6, -5 % at 1e7 and -25 % at 1e9 (README 4.7); for a board of 50 to 200 mm at 10 to 80 K the coefficient differs by +6.5 % to -10 %.

**Measured impact** (`README.md` 4.8 B): on the example board and bare two-layer boards turned to the vertical, with computed coefficients, the laminar form changes the maximum temperature by -0.7 to +0.2 % of the rise (-0.43 to +0.14 K).

**Proposal.** Keep the general form as the default and leave the choice for a later `Board.natural_form` option, or change nothing: the difference is inside the +-30 % that the uncertainty of the calculator assigns to `h`, and neither paper was opened (the forms are taken from the compilation of sources and the library `ht`; the general form reproduces the library's worked example to the digit). **Recommended: change nothing until Churchill and Chu (1975) is read.**

## 3. The documented numbers of the plate check (documents only, no code)

The documents say that the plate model is `+4.5 %` from Seri Lee's centre value; that was a 24 mm source (`round()` rounds halves to even, so on 1 mm cells the edges 37.5 and 62.5 mm went to 38 and 62). With the 25 mm source the model is within +0.6 %, -0.8 % and -4.6 % of the article at the centre, the edge and the corner (`README.md` 4.8 A). The text to put in the documents is in `docs/for-the-project-documents.md`.

## 4. The independent solver as a reference in the program's tests (medium)

`lib/layered3d.py` (about 140 lines, SciPy only, with its own tests against a series circuit, two energy balances, a uniform layer and three published numbers) could become a test helper in `tests/` for the comparison of the layered models with a 3D solution on a laminate, next to the finite-element script that needs scikit-fem. This would need its own review for the program's documentation rules.

## What this investigation does not propose

* **No effective conductivity in the program.** The paper shows that a single averaged conductivity of a laminate depends on the layer order (15.0 to 5.0 W/mK for the same copper and FR4), on the size and position of the source and on the film coefficient, and that none of the means is good (the geometric mean can be 70 % off). The program never homogenises a stack: every copper layer is a node and every gap a resistor, so the layer order is represented. The homogenised conductivity should stay out of the program.
