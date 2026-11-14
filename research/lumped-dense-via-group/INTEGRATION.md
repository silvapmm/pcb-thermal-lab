# Integration: the Lumped part over a dense via group

Nothing here is implemented in the program. Everything was measured on a copy (`lib/variants.py`, monkeypatches inside a context manager); `pcbthermal/`, `tests/` and the documents are untouched.

## 1. What the investigation says about the program as it is

1. **No defect of the zoned footprint for dense groups was found.** For pitch up to 1.0 mm (35 zoned cases of the sweep, two and four layers, 6 and 10 mm parts, 3, 5 and 8 vias a side, drill 0.3 and 0.6 mm, hollow and filled) the zoned Lumped reads the part peak -1.1 % on average (largest 5.2 %) of the FVM rise, against +4.6 % (largest 9.4 %) for one node; against the independent 3D reference, -1.4 to +2.2 % on the dense 40 x 40 mm boards. About one point of the zoned error is the no-via Lumped baseline against the FVM on a 100 x 80 mm board, not the via group (README 3).
2. **The definitions are consistent** (README 2): the part row is peak with peak; the Lumped board maximum equals the hottest part peak; the micro peak is 0.1 K and does not decide; the painted maximum under a footprint is a node, never a peak. Comparing a mean with a peak is what changes a conclusion (one node: +0.7 % mean, +5.1 % peak).
3. **Two regimes keep a larger error**, both a shape of the footprint field and not a via constant (README 3.3, 4, 6.2): an array that fills about three quarters of the footprint with vias on its edge (pitch 2.0 mm under 7.5 to 8.1 mm: zoned +5 to +8 %, one node about 0), and a footprint much larger than a sparse array (pitch 1.5 mm under 8.5 to 11 mm: zoned -3.8 to -5.0 %, one node +0.6 to +3.4 %). The factor on the A-C link that would cancel each case runs from 0.2 to 4.2, `CORE_R` and the raster only trade one regime for the other.

## 2. Candidate: `MAX_CORE` from 0.92 to 0.75 (`lumped.py` constant; decision for the maintainer)

| | program (0.92) | 0.75 | 0.6 |
| :-- | --: | --: | --: |
| zoned cases (of 66) | 46 | 43 | 33 |
| largest absolute part-peak error over the zoned cases | 7.3 % (pitch 2.0 under 8 mm) | 5.2 % | 4.7 % |
| mean absolute error | 1.89 | 1.83 | 1.57 |
| cases that change from zones to one node | - | 3 | 13 |
| frozen `plate_vias` Lumped | 136.523 degC | 136.523 (unchanged) | 140.417 (+3.9 K) |
| frozen example boards (core share 0.98: one node already) | unchanged | unchanged | unchanged |

* Effect: removes the +7.3 % case; the gain in the mean error is small (0.06 point). The three cases that change are the arrays that fill the footprint (core share above 0.75 on the fine grid).
* Frozen-number risk of 0.75: none on the 17 boards of the harness as far as measured (the two boards with zoned or near-zoned footprints, `plate_vias` and the example boards, are bit-identical; the other frozen boards have no two vias in a footprint). No refreeze would be needed. Documents to touch if adopted: `docs/theory.md` 5.2 (the 92 % sentence, the justification of README 9.7 of `research/lumped-zones-adoption`: 94 to 99 % read hot), `docs/validation.md` 18.2 and 42 (a line).
* Not recommended: 0.6 (moves a frozen record, gains one case more), a change of `CORE_R` (trades regimes), a scale on the A-C link (no single factor), the raster 0.25 mm (moves the zoned level down by 1.9 points and costs 4 times the cells).
* Recommended before any adoption: a check on boards with several groups in one footprint, groups that are not square arrays, a metal block and an outline, which this folder did not sweep; and the reviewer's go.

## 3. What would be a real fix, not measured here

The two regimes point to the lack of a spatial profile inside the footprint (the FVM field is a bell, hottest in the core; the zones put A and C within 0.6 K of each other). A model with the core temperature carrying a bump derived from the whole-footprint field (not only the A-field) would be the direction; it is a model change with its own investigation (it would move frozen records) and is not proposed here on this evidence. The position-based core mask (README 4.1, figure 2) is a hygiene item: it removes the dependence on the cell edge each via falls on but did not lower the error on the sweep.

## 4. What does not change

Nothing in the program, the tests, the examples or the documents. The research tests: `python -m pytest research/lumped-dense-via-group/tests -q` (5 tests).
