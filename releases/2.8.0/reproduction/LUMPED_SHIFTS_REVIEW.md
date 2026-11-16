# Review of the two shifts left "to confirm" by the reproduction pass (part B)

**Neither shift is a defect of the program.** Both are legitimate effects of 2.8.0 items, each from exactly one merge, and both are larger than the bands the item table states (the table describes the frozen boards only). One defect of a STUDY was found on the way: `research/solid3d-verification/scripts/copper_dissipation.py` passes the cell size as the positional `rings` argument of `lumped.solve_steady`, so its Lumped column has always been a one-ring network, which the program never runs. Its +22 % comes from that one-ring network, not from the program's Lumped.

Program trees: `development` 77ed4822 (2.8.0 candidate) and the tag v2.7.1, plus each first-parent merge between them that touches the models (each extracted with `git archive <commit> pcbthermal` into a scratch folder). Reviewer: the reproduction pass of 2.8.0, part B follow-up. Script: `scripts/study_lumped_shifts.py` (every number below is printed by it; the commands are in its `@file` block).

## 1. Shift 1: the Lumped column of `copper_dissipation` (652.7 to 795.0 °C on the 10 mm pad)

### 1.1 What the study runs

Line 51 of `copper_dissipation.py` calls `lumped.solve_steady(p, cell)` with `cell = 1.0`. The signature is `solve_steady(problem, rings=10, cell_mm=1.0)`, so the study builds a network with **one ring** around the footprint (the whole rest of the board as one node). The program never runs that network: `SolverOptions` refuses `lumped_rings < 3` and `api` passes `rings=10, cell_mm=lumped.cell_for(...)`. `lumped.solve_steady` itself accepts `rings=1.0` without a word (section 4, finding 3). No other call of this form exists in `research/`, `releases/`, `examples/` or `tests/` (grep for a two-argument positional call).

### 1.2 Bisect (Lumped peak, °C; FVM, FDM, 3D solid and Analytic do not move at any step)

| Tree | study call, 10 mm | 20 mm | 80 mm | program (10 rings), 10 mm | 20 mm | 30 mm | 40 mm | 60 mm | 80 mm |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| v2.7.1 | 652.7 | 517.4 | 151.1 | 494.5 | 249.7 | 190.4 | 165.4 | 147.5 | 142.6 |
| e2b3b069 (`fix/lumped-part-readout`) | 652.7 | 517.4 | 151.1 | 494.5 | 249.7 | 190.4 | 165.4 | 147.5 | 142.6 |
| ed6d9c99 (`fix/drawn-copper-faces`) | 652.7 | 517.4 | 151.1 | 494.5 | 249.7 | - | - | - | 142.6 |
| **43aeb1ad (`fix/lumped-edge-first-link`)** | **795.0** | **642.9** | **182.0** | **527.6** | **253.3** | **194.2** | **169.3** | **151.5** | **146.5** |
| 3a894c41 (`fix/face-film-half-slab`) | 795.0 | 642.9 | 182.0 | 527.6 | 253.3 | - | - | - | 146.5 |
| 77ed4822 (`development`) | 795.0 | 642.9 | 182.0 | 527.6 | 253.3 | 194.2 | 169.3 | 151.5 | 146.5 |

The whole shift is the merge of `fix/lumped-edge-first-link` (the first link of the network read as the logarithmic potential of the footprint and its mirror images, item M3). The part read-out (`e2b3b069`) does not move the board maximum (as designed: it already included the part's own peak), and the face film (M1) moves nothing visible at 0.1 K. The 2.7.1 column reproduces the PART-B "old" output to the digit, and the 77ed4822 column its "new" output.

### 1.3 Size of the shift, in % of the rise (ambient 25 °C)

| Pad | program's Lumped (10 rings) | the study's one-ring network |
| :-- | --: | --: |
| 10 mm (the heater's own pad only) | **+7.1 %** | +22.7 % |
| 20 mm | +1.6 % | +25.5 % |
| 30 mm | +2.3 % | +27.7 % |
| 40 mm | +2.8 % | +28.6 % |
| 60 mm | +3.3 % | +27.5 % |
| 80 mm | +3.3 % | +24.5 % |

### 1.4 Which version is closer to the reference

References: the FVM of the same layered board at 1 mm (`copper_dissipation.py` new output, the same on both trees); the program's finite-element model at 1 mm (`--case fem`, 77ed4822: 501.5 / 272.8 / 143.9 °C on the 10 / 20 / 80 mm pads; within 1.6 % of the rise of the FVM); the independent scikit-fem solid of `docs/validation.md` 3.1 (495.3 / 273.0 / 202.6 / 172.5 / 144.6 °C, quoted, **not re-run** here). Error of the program's Lumped on the rise:

| Pad | against FVM: 2.7.1 | 2.8.0 | against the program's FEM: 2.7.1 | 2.8.0 | against scikit-fem (quoted): 2.7.1 | 2.8.0 |
| :-- | --: | --: | --: | --: | --: | --: |
| 10 mm | -3.0 % | +3.9 % | -1.5 % | +5.5 % | -0.2 % | +6.9 % |
| 20 mm | -10.5 % | -9.0 % | -9.3 % | -7.9 % | -9.4 % | -7.9 % |
| 30 mm | -7.3 % | -5.2 % | - | - | -6.9 % | -4.7 % |
| 40 mm | -5.1 % | -2.4 % | - | - | -4.8 % | -2.2 % |
| 60 mm | -2.2 % | +1.0 % | - | - | - | - |
| 80 mm | -1.5 % | +1.8 % | -1.1 % | +2.2 % | -1.7 % | +1.6 % |

Mean absolute error against the FVM over the six pads: 4.92 % (2.7.1), 3.89 % (2.8.0). **The 2.8.0 Lumped is closer on the 20 to 60 mm pads and on average; on the 10 mm pad 2.7.1 was closer** (-3.0 against +3.9 % of the FVM, -1.5 against +5.5 % of the FEM): 2.8.0 reads it hot, the safe side. The one-ring numbers of the study (652.7 and 795.0 °C) are far from every reference (+29.7 % and +59.1 % of the FVM) and are not a measure of the Lumped model at all.

### 1.5 Why this pad moves more than the frozen boards

On the 10 mm case the footprint is all the copper of its layer: ring 1 is bare laminate, so its sheet conductance `S[l, 1]` is about a tenth of the footprint's. The first link that `fix/lumped-edge-first-link` replaced (`0.5 t_1 / (S_1 L_1)`, half of ring 1 as a strip) and the new one (`(U_1 - phi_boundary) / (2 pi S_1)`, the potential of the footprint and its images from its boundary to the mean of ring 1) are different geometric factors divided by that small `S_1`, so their difference is amplified; on the boards of `research/lumped-edge-link` (full copper, `S_1 = S_0`) and on the 17 frozen boards the same change is small. The images play no part here (the part is 35 mm from the nearest side); the investigation measured the same thing as 'most of the gain is the replacement of the strip by the potential difference' and recorded an interior shift of +3.8 points of the rise on average at 0.5 mm (+0.5 to +6.4) and +2.2 points at 1 mm (`research/lumped-edge-link` README 3.3, review 4.7). The 10 mm bare-laminate pad (+7.1 % at 1 mm) lies above that range. This explanation is read from the code and from the investigation; the two link resistances of this board were not printed separately. The input checks already warn that the Lumped is unreliable for a one-sided pad without vias (`docs/validation.md` 3.1).

**Verdict (shift 1): (b), a legitimate effect of M3 outside the band of the item table, plus a study defect that inflates it.** The program's Lumped moves +7.1 % of the rise, not +22 %.

## 2. Shift 2: the calculator's JEDEC board without vias (74.6 to 83.5 K/W)

### 2.1 The calculator does not use the Lumped

`inverse.power_from_temperature` runs `model="fvm"` by default and `calculator_validation.py` does not change it; the only 2.8.0 change to `inverse.py` (the own resistance `(T(P) - T(0)) / P`) is bit-identical with one heater (the code comment and this row: the junction at the found power is 57.498 °C on both trees). So M3 cannot move this row; the PART-B attribution to M3 was wrong.

### 2.2 Bisect (`--case calc`, model RθJA in K/W, 0.5 mm, computed h)

| Tree | RθJA | power for 1 W |
| :-- | --: | --: |
| v2.7.1 | 74.6 | 0.436 W |
| 9e2331a3 (`fix/horizontal-face-laws`, the merge just before) | 74.6 | 0.436 W |
| **ed6d9c99 (`fix/drawn-copper-faces`)** | **83.53** | **0.389 W** |
| 3a894c41 (`fix/face-film-half-slab`) | 83.53 | 0.389 W |
| 77ed4822 (`development`) | 83.53 | 0.389 W |

The whole shift (+12.0 %) is item M2, drawn copper read as imported copper. With the fixed default coefficients (`--case jedec`, one FVM run at 1 W) the part peak rise is 70.87 K (2.7.1) against 79.70 K (2.8.0), +12.5 %: the shift is not in the computed coefficients. Variants on the same two trees (`--case jedec --variant ...`, the same board otherwise): inner planes over the whole board 70.20 / 79.03 K (the plane edges do not matter); no top land 180.512 / 180.514 K (0.003 K apart, the size of M1). So the change is the reading of the 4.15 mm land, whose edges cut cells of the 0.5 mm grid (the grid is 114.3 / 229 by 76.2 / 152 mm, so no edge lies on a cell line).

### 2.3 Which version is right: grid convergence of the cut land

A window of 41 x 40 cells of the same grid (20.46441 x 20.05263 mm, the same pad and land at the same sub-cell position, inner planes over the window, `--case window`) reproduces the local shift of the whole board (+8.81 K against +8.83 K at 1 W). Part peak rise:

| Cell (mm) | 2.7.1 | 2.8.0 |
| --: | --: | --: |
| 1.0 | 173.20 | 170.35 |
| 0.5 | 155.09 (-5.2 %) | 163.91 (+0.2 %) |
| 0.25 | 158.02 (-3.4 %) | 163.34 (-0.2 %) |
| 0.125 | 161.81 (-1.1 %) | 163.30 (-0.2 %) |
| 0.1 | 161.11 (-1.6 %) | 163.66 (0.0 %) |

(percentages against 163.66 K, the 2.8.0 value at 0.1 mm). The 2.8.0 FVM is converged within 0.4 % of the rise from 0.5 mm down; the 2.7.1 FVM was 5 % low at 0.5 mm and still 1 to 2 % low at 0.1 mm. On an aligned control (`--case aligned`, 20 x 20 mm, 3 mm pad on a 5 mm land with edges on the lines of a 0.125 mm grid) the two trees agree to the digit at 0.125 mm (151.1945 K) and 2.7.1 is -3.0 % at 0.5 mm, 2.8.0 +0.1 %. So **the 83.5 K/W of 2.8.0 is the converged FVM answer for this board and the 74.6 K/W of 2.7.1 was a grid error of about -11 %** (the land's local term, 8.8 K/W of about 80, was under-read). The whole board at 1 mm: 90.00 K (2.7.1) and 87.03 K (2.8.0) against 70.87 / 79.70 K at 0.5 mm: the 'strongly grid-dependent' no-via row of `research/power-calculator` README 4.5 (88 to 71 K/W from 1 to 0.5 mm) was mostly this error of the old faces. An independent solver was not run on this board here; `docs/validation.md` 51.7 holds the independent checks of M2 (not re-run).

**Verdict (shift 2): (b), a legitimate effect of M2 (a correction: the new number is the converged one), outside the M2 text of the item table**, which names only frozen boards at 2 mm.

## 3. What the item table (`releases/2.8.0/REFREEZE_PLAN.md` section 2) needs

The study diff (`study_diff.py`) checks only the frozen records, so neither shift changes a limit of `expected_shifts_2.8.0.json`; the table is also the reference of the reproduction pass, so its text should name these effects. Proposed additions (column 'Moves'):

* **M2**: '... Outside the frozen boards: FVM and FDM wherever a drawn copper edge cuts a cell at any size; the calculator's JEDEC board without vias **+12.0 %** (74.6 to 83.5 K/W at 0.5 mm; the part peak +8.8 K at 1 W, the converged value, `reproduction/LUMPED_SHIFTS_REVIEW.md` 2); the other rows of `calculator_validation.py` +0.9 to +1.1 % (46.7 to 47.1, 45.6 to 46.1, 31.6 to 31.9 K/W; attributed to M2 by `docs/validation.md` 418, not bisected here).'
* **M3**: '... Outside the frozen boards: a lone part whose footprint is all the copper of its layer (`copper_dissipation.py`, 10 mm on bare laminate) **+7.1 %** of the rise on the board maximum at 1 mm; pads 20 to 80 mm +1.6 to +3.3 % (`reproduction/LUMPED_SHIFTS_REVIEW.md` 1).'
* **M0**: 'calculator' stays in the list of items with no frozen record (the calculator's own items move nothing), but a calculator row may move through M1 and M2 (it runs the FVM).

A band for the reproduction pass: Lumped board maximum -0.5 to +7.5 % of the rise; FVM where a drawn edge cuts a cell up to +12.5 % of a part's rise at 0.5 mm (the measured +12.47 % of the fixed-coefficient run, rounded up). The one-ring column of `copper_dissipation.py` gets no band: it is a study defect (4, finding 1).

## 4. Findings

1. **Defect in a study** (`research/solid3d-verification/scripts/copper_dissipation.py:51`): `lumped.solve_steady(p, cell)` passes the cell (1.0) as `rings`. Every Lumped number of that script, in every version, is a one-ring network. **Wrong documents that follow from it**: `docs/validation.md` 3.1 (the Lumped column of the pad sweep, lines 171 to 176, and 'Lumped up to +107 %' at line 193) and `research/solid3d-verification/README.md` (lines 32, 136 to 137, 156). With the program's Lumped against the FVM the pad sweep reads -10.5 to -1.5 % (2.7.1) and -9.0 to +3.9 % (2.8.0), not 'up to +107 %'; the conclusion 'unreliable for a one-sided pad without vias' becomes '-9 % on a 20 mm pad, +4 % on the heater-sized pad'. Fix: `lumped.solve_steady(p, cell_mm=cell)` (10 rings) or the API path, re-run the script, rewrite the Lumped column and the sentence. **Corrected on this branch** (maintainer's decision): the script asks for `rings=10, cell_mm=cell`, with `research/solid3d-verification/tests/test_copper_dissipation.py`; the re-run (77ed4822, 24 s) prints the program's column 527.6 / 253.3 / 194.2 / 169.3 / 151.5 / 146.5 °C and every other column to the digit of PART-B; `docs/validation.md` 3.1, the folder README (2 and 4.2.1), its diagram (figure 8) and `research/theory/topics/05-lumped-rings.md` 5 are rewritten with the corrected claim.
2. **Stale documents** (calculator): `docs/calculators.md` 2.1 (line 118), `research/power-calculator/README.md` (lines 64, 75, 151) quote 74.6 K/W and the 88-to-71 K/W grid dependence; on 2.8.0 the row is 83.5 K/W at 0.5 mm and 87.0 K at 1 mm (fixed coefficients 79.7 K at 0.5 mm), and the earlier grid dependence was the old faces. The calculator help does not quote the row (grep). **Corrected on this branch**: both documents give 83.5 K/W as the converged value and the reason (the grid error of the old faces).
3. **Limit to record, small program robustness item** (maintainer: not in 2.8.0; item e12 of `releases/2.9.0/PLAN.md` 1.1): `lumped.solve_steady` accepts `rings` below 3 and a float without a word while `SolverOptions` refuses it; a check `rings >= 3` (integer) in `solve_steady`, `step_responses` and `run_profile` would have caught finding 1. Proposal for a `fix/` branch after 2.8.0 or within it, maintainer's decision; it moves no number.
4. **Correction of the PART-B attribution**: the no-via row was attributed to M3 (Lumped); it is M2 (the calculator runs the FVM).

## 5. Decisions for the maintainer

1. Accept the two shifts as explained (M3 and M2) and widen the text of the item table as in section 3. Recommended: yes; neither is a regression, the calculator row is a correction and the Lumped column moves within its model's documented error on the safe side.
2. Correct `copper_dissipation.py` and the documents of finding 1 before the documentation review closes (the corrected column is already measured here at 1 mm; `docs/validation.md` 3.1 quotes the FVM and FDM at 0.5 mm, so the script should be re-run as a whole). Recommended: yes, in 2.8.0, since the '+107 %' is a claim about the program that is false.
3. The guard on `rings` (finding 3): in 2.8.0 or later.

## 6. What was not verified

* The program's FEM at a cell finer than 1 mm on the pad cases, and the scikit-fem column (quoted from `docs/validation.md` 3.1, not re-run: the machine was busy with the reproduction testers).
* The whole JEDEC board below 0.5 mm (about 5 GB at 0.25 mm); the convergence was measured on the window that reproduces the local shift to 0.02 K.
* An independent solver on the JEDEC board (the M2 checks of `docs/validation.md` 51.7 were not re-run).
* The two link resistances of section 1.5 were not printed; the mechanism is read from the code and from `research/lumped-edge-link`.
* The other three calculator rows were not bisected (their attribution to M2 is that of `docs/validation.md` 418).
* The 3D solid (finite volumes) column of `copper_dissipation.py` (530.2 °C on the 10 mm pad, +4.4 % of the rise above the FVM and +6.0 % above the program's FEM) was not investigated.
