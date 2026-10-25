# Corrections for the project documents (from the review)

The reviewer may not edit `docs/` on a research branch. These are the changes the review of `research/power-calculator/` found necessary in the project documents, to be made on a `fix/` or `docs/` branch off `develop`. Every number is printed by a script of this folder (README sections 4.5 to 4.7).

## `docs/calculators.md`

1. **Section 2.1, table, last row.** "the same JEDEC board without the thermal vias | - | 67.4 | (0.48 W)": 67.4 K/W is printed by no script. `calculator_validation.py` now prints 68.1 K/W at 0.5 mm; the value depends strongly on the cell (83.6, 68.1, 72.9, 74.5 K/W at 1, 0.5, 0.35, 0.25 mm; `study_cell_size.py`). Replace with "68.1 (0.5 mm; 73 to 84 K/W at other cell sizes)".
2. **Section 2.1, second bullet.** "the 5 × 5 mm body, the 3.15 mm pad and the 3 × 3 via array are assumptions, so this row is an indication (−3 %), not a proof": the body and the pad are in the TPS7A47 package drawing RGW0020A (datasheet SBVS204G); only the via array is assumed; the sign is wrong (the table gives +3.0 %). Replace with "the 5 × 5 mm body and the 3.15 mm pad are from the package drawing RGW0020A; the 3 × 3 via array is an assumption, so this row is an indication (+3 %), not a proof." Same in the table: "TPS7A47-like, package data assumed" → "TPS7A47, via array assumed".
3. **Section 2.1, new bullet** (cell size and model error): "At 0.25 mm the two rows are −2.3 % (CSD17308Q3, 47.1 K/W) and +1.3 % (JEDEC, 32.1 K/W). On the CSD17308Q3 board the FVM's board resistance is 2.4 % below an independent 3D solver and the program's 3D solid is within 0.1 % of it, so part of the agreement is a model error: with the 3D solid the calculator would return about 0.96 W (−4 %; estimated, not printed: 46.8 × 48.3 / 47.2 = 47.9 K/W, 46 / 47.9 = 0.96)."
4. **Section 2.1, JEDEC bullet.** Add: "ROHM 64AN113E table 2 reads the backside copper of the 2s2p board as 74.2 × 74.2 mm of 70 µm (the study draws traces, as JESD51-7 is usually described); with that plane the model gives 26.4 K/W (+23 %), so the row holds only for the traces reading."
5. **Section 1.1b, last paragraph** (done in `develop`): the text now says that the numbers-only band holds only when the board is drawn right and points to the design uncertainty of 1.1c; nothing left to add. Numbers with and without the design term (`research/power-calculator`, README 4.7): without the term (level none) ring 2.00 / 1.62 / 2.31 W and top 2.00 / 1.69 / 2.27 W; with the default level (hand) ring 2.00 / 1.56 / 2.34 W and top 2.00 / 1.60 / 2.31 W; both reproduced.
6. **Section 1.1, Idea.** Add after "a secant iteration finishes it": "(on the CSD17308Q3 board the junction is 6 K below the two-run line at 2 W with computed convection)". Optional.
7. **Section 4, Reproduce.** Add `calculator_calibration_study.py` (table 2.4), `study_power_band.py [level]` (the example of 1.1b; level `none` is the numbers-only band) and `study_design_term_coverage.py` (the coverage table of 1.1c), which are not listed.
7b. **Section 1.1c, paragraph "What it covers"**: "the table was **measured with a script that is not versioned**" is out of date: the script is `research/power-calculator/scripts/study_design_term_coverage.py` (columns none, hand, estimated reproduce the table to the last digit; it also prints the column cad, not in the table: hatched 1.462–1.967 out, half-weight copper 1.275–1.725 out, no vias 1.492–2.024 in, no planes 1.096–1.531 out). Replace with "measured with `study_design_term_coverage.py`". The 1.1c sentence "the column *None* reproduces part 2 of that study" stays true (`study_power_band.py none`).

## `docs/validation.md`

8. **Section 19, fourth bullet.** "a JEDEC 2s2p board 31.6 against 32.5 K/W": add "(0.5 mm; 32.1 at 0.25 mm)".
9. **Section 19, fifth bullet.** "What would improve it (not implemented): a second measurement (the board ring and the top, or two known powers) to calibrate the copper": the calibration study found a second board point badly conditioned (±1 K moves the fitted copper multiplier from 1.05 to 3.9 and the power by ±17 %) and the known-power reference the good route (±5 %). Replace with "What would improve it (not implemented): a reading at a known power to calibrate the board (within ±5 % with ±1 K readings); a second board point is badly conditioned (±17 %); see `docs/calculators.md` 2.4."

## `pcbthermal/help/` (program, for the `maintainer`)

10. `help/index.html` and `help/calculator.html` say "within 2 to 3 %" on the datasheet boards: still true at every cell size studied; no change needed unless item 3 is adopted.

## Not stale

* Tables 2.2 (sensitivity), 2.4 (calibration), the band example of 1.1b (level none, and the ring and top values at the default level hand) and the coverage table of 1.1c are reproduced to the last printed digit on the current program (develop merged into this branch, with the edge fix, the 3D size limit and the inner-copper option).
* `docs/theory.md` has no section on the calculator; its formulas are in `docs/calculators.md` 1.1 and agree with `pcbthermal/inverse.py`.

## 11. `docs/validation.md`: the error of the 2-layer boards (decided: documented, not corrected)

Add to the one-layer section (21) a short subsection. Against the independent solver (current program, FVM; `research/REVIEW.md`, "Measured and not implemented"): CSD17308Q3 board with an empty bottom -2.3 % (as one layer: -1.3 %), 20 mm pad -3.8 % (-2.3 %), 10 mm pad -7.7 % (-4.8 %), full copper on top no difference; a 2-layer board with the same pad on both faces gives -3.9 %. The error belongs to every 2-layer board (two nodes through the gap), not to the bare bottom; the 3D solid is within 0.4 %. No variant for the Analytic model alone is offered (-32 % to -13 % with a 20 mm pad, still poor with smaller pads).
