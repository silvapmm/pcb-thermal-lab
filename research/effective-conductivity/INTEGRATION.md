# What could enter the program from this investigation (the investigation is closed)

Nothing here was needed for the program to be right on the boards it is made for: the five models agree with an independent 3D solver on a Cu / FR4 / Cu coupon (FVM, 3D solid and Analytic within 0.2 %, FDM within 1.2 %, Lumped within 0.3 %) and the published cases are reproduced. Three optional proposals (sections 1, 2 and 4) have since been **adopted on `develop`** (branch `feature/effective-conductivity-adoption`, `docs/validation.md` section 22); section 3 is adopted too, and the problem of section 5 is corrected in the program in another form. Nothing is left to implement from this folder; the sections below keep the proposals as they were measured and say where each one lives.

## 1. An input check for a thick, poorly conducting plate (adopted)

**Status: implemented** as `checks.check_thick_plates` (`pcbthermal/checks.py`), tested in `tests/test_thick_plate.py`, documented in `docs/validation.md` section 22. The text below is the proposal; the differences of the version in the program are in the next paragraph.

**What the program does differently from the proposal.** The proposal took `q''` from the power of the heater over a pad or footprint. The review of the adoption measured the flux that **really enters the block** in the FVM solution and found it is 8 to 22 % of the footprint flux on the 74 metal-block cases of `research/block-and-fins`, and only 1 to 3 % under a 2 or 3 mm part (a block under the board is fed through the laminate and the copper, which spread the heat). The footprint flux fired on ordinary designs (a 3 x 3 mm, 2 W part over a 3 mm steel block: 9.5 % of the rise), so the check takes, for a block, the largest flux into the block under the footprint from the FVM or FDM result (a quiet auxiliary FVM run with a cell of at least 2 mm when only the Lumped, Analytic or 3D solid ran) and keeps the footprint flux for the copper layer of the part. Criterion over the 74 block cases (2 mm cells): median 0.07 %, maximum 0.34 %, none above 5 %, against 0.04 / 0.42 % for the pad flux of this research and 0.50 / 1.78 % for the footprint flux. The research's pad flux at a rise of 90 K is not conservative (the peak flux into the block is 1.6 times the pad mean at the median). Against the 3D solid the bound with the flux into the block is above the real effect in the seven cases of `docs/validation.md` section 22 (by 2 to 10 times); three of them warn.

**Problem.** The layered models keep one temperature per layer, the mean through its thickness. For a plate of thickness `t` and conductivity `k` under a source of flux `q''` the surface under the source is hotter than that node by at most `q'' t / (2 k)` (README 4.6; less when the heat spreads sideways): measured 1.6 % of the rise for 10 mm of `k` 50 (bound 2.25 %), for 10 mm of `k` 10 (case 1 of Muzychka and others) 4.7 and 7.1 K against bounds of 8 and 12 K, where the models fall short of the surface by 9 to 10 % of the rise (README 4.6), against 0.0001 K for 35 um of copper. The program has no layer of that kind among the copper layers, but it does have heatsink blocks of 1 to 6 mm and the user can type any conductivity.

**Proposal.** A warning in `checks.py` when, for a heater on a block or on a layer, `q'' t / (2 k)` exceeds 5 % of the rise of the heater (computed after the run, from the heater power per area, the thickness and the conductivity of the layer or block under it). The text would say that the surface temperature under the source can be higher than the model shows, by up to that amount (the bound is reached when all the heat crosses the layer under the source; with sideways spreading the measured gradient was 0.6 to 0.8 of it).

**What does not change.** The models, the results and the interface.

**Measured impact** (`README.md` 4.8 C; this is the research's criterion with the pad flux, the program's flux into the block gives 0.34 % and 0.07 %): on the 74 metal-block cases of the program the criterion is at most 0.42 % (a 3 mm steel block), median 0.04 %, so the check **never fires on the cases the program is built for**; it is a safety net for a thick, poorly conducting layer typed by the user.

**Risk.** A false alarm on a thick copper block (the criterion is then tiny, so none); the criterion is a bound, not a correction, and must not be added to the result.

## 2. The laminar form of Churchill and Chu as an option (adopted as an option, default unchanged)

**Status: implemented** as `Board.natural_form` (`pcbthermal/convection.py`, `docs/validation.md` section 22, `docs/theory.md` section 8). The default stays `general`, which reproduces the earlier results bit for bit; `laminar` is the option. On the example board turned vertical (computed h, FVM, 1 mm cells) the maximum is 86.72 C with the general form and 86.50 C with the laminar one (-0.22 K, -0.4 % of the rise), inside the -0.7 to +0.2 % measured here; the option reproduces every row of the table of `README.md` 4.8 B to 0.01 K. Above Ra 1e9 the laminar form warns. Churchill and Chu (1975) itself is still not opened, which is why the default was not changed; the proposal text follows.

**Problem.** The program uses the general correlation for a vertical board over the whole range. The same authors' laminar form (for Ra below 1e9, recommended by textbooks for laminar flow) differs from it by +7 % at Ra 1e4, +2 % at 1e6, -5 % at 1e7 and -25 % at 1e9 (README 4.7); for a board of 50 to 200 mm at 10 to 80 K the coefficient differs by +6.5 % to -10 %.

**Measured impact** (`README.md` 4.8 B): on the example board and bare two-layer boards turned to the vertical, with computed coefficients, the laminar form changes the maximum temperature by -0.7 to +0.2 % of the rise (-0.43 to +0.14 K).

**Proposal.** Keep the general form as the default and leave the choice for a later `Board.natural_form` option, or change nothing: the difference is inside the +-30 % that the uncertainty of the calculator assigns to `h`, and neither paper was opened (the forms are taken from the compilation of sources and the library `ht`; the general form reproduces the library's worked example to the digit). **Recommended at the time: change nothing until Churchill and Chu (1975) is read** (superseded: the option was adopted with the default unchanged, see the status above).

## 3. The documented numbers of the plate check (documents only, no code): adopted

Adopted on the branch `fix/model-corrections` (merged into `develop`): `docs/theory.md`, `docs/research.md` and `docs/validation.md` now give +0.6 %, -0.8 % and -4.6 % with Seri Lee (1998) as the source, and the plate check script rounds halves up.


The documents say that the plate model is `+4.5 %` from Seri Lee's centre value; that was a 24 mm source (`round()` rounds halves to even, so on 1 mm cells the edges 37.5 and 62.5 mm went to 38 and 62). With the 25 mm source the model is within +0.6 %, -0.8 % and -4.6 % of the article at the centre, the edge and the corner (`README.md` 4.8 A). The text to put in the documents is in `docs/for-the-project-documents.md`.

## 4. The independent solver as a reference in the program's tests (adopted)

**Status: implemented** as `tests/helpers/layered3d.py` with the comparison `tests/test_layered_vs_3d.py` (`docs/validation.md` section 22: Cu / FR4 / Cu coupon and one-layer board, five models, 1 mm cells). `lib/layered3d.py` here (about 140 lines, SciPy only, with its own tests against a series circuit, two energy balances, a uniform layer and three published numbers) stays as the record of the investigation; the copy in `tests/helpers/` is the one the program's tests use.

## 5. The laminate under the bottom film of a one-layer board (superseded: corrected in the program in another form)

**Status (after the review).** The problem is corrected in `0ea5f07` (`pcbthermal/laminate.py`, `docs/validation.md` section 21): the FVM, FDM and Lumped give a one-layer board two laminate nodes under the copper, and the Analytic puts the laminate in series with the bottom film, which is this candidate. Against the independent solver (README 4.11) the FVM is now -0.0 % with full copper and -2.5 % with the 20 mm pad; the FDM, Lumped and Analytic are 7.4, 14.7 and 28.8 % low on the pad. The text below is the candidate as it was measured on the program before the correction; the series coefficient must not be typed on the corrected program, which already has the laminate (it would count it twice: +0.8 to +2.7 % with full copper).

**Problem (before the correction).** On a one-layer board the layered models put both films on the copper node, so the laminate between the copper and the bottom face is missing: against the independent solver the FVM is 0.9 to 4.4 % low with full copper (0.8 to 3.2 mm) and 10 % low with a 20 mm pad (README 4.11).

**Idea.** For a one-layer board, put the bottom film in series with the laminate: `g_bottom = A / (1/h_bottom + t_lam / k_th)`. It does not catch the lateral spreading in the laminate under a small pad, only the series resistance.

**Measured impact** (README 4.11, on a copy: the equivalent coefficient typed): full copper -0.9 / -1.9 / -4.4 % become -0.1 / -0.3 / -1.1 % (0.8, 1.6 and 3.2 mm); the 20 mm pad -10.0 % becomes -7.6 %. It would apply to the FVM, FDM, Lumped and Analytic (the bottom film of a one-layer board), not to the 3D solid, which has the laminate.

**Risk.** A one-layer board in the simple stack-up shares the thickness with nothing else, so the laminate is the whole board minus the copper; in the advanced stack-up a one-layer board has no gap and would need its laminate thickness stated. The maintainer decides.

## What this investigation does not propose

* **No effective conductivity in the program.** The paper shows that a single averaged conductivity of a laminate depends on the layer order (15.0 to 5.0 W/mK for the same copper and FR4), on the size and position of the source and on the film coefficient, and that none of the means is good (the geometric mean can be 70 % off). The program never homogenises a stack: every copper layer is a node and every gap a resistor, so the layer order is represented. The homogenised conductivity should stay out of the program.
