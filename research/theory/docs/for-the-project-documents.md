# Text for the project documents (from the review of `research/theory`)

Corrections for `docs/` of `develop` (checked at `3e90a7f`) found while the topics were compared with the program and the documents. Nothing here is applied: a research branch does not edit the project documents. Each item gives the place, what is wrong, the evidence and a suggested text.

## 1. `docs/validation.md` section 4, item 1, and `docs/theory.md` (the explanation of the FVM-Analytic agreement)

**Wrong explanation.** Item 1 says the FVM and the Analytic model "agree, within the FVM's mesh error (0.2 to 1 %)". Measured (`research/theory/scripts/study_fvm_analytic_edges.py`, the same digits on `research/gerbers` and on `develop` `3e90a7f`), on the four uniform scenarios of section 2:

| Scenario | Analytic against the FVM at 1 / 0.5 / 0.25 mm, `h_side` 10 W/m2K | the same with insulated edges in both |
| :-- | :-- | :-- |
| reference board (centred 20 mm heater) | +0.33 / +0.30 / +0.30 % | -0.07 / -0.09 / -0.10 % |
| example, uniform | +0.66 / +0.59 / +0.58 % | -0.20 / -0.27 / -0.28 % |
| example, only U1, uniform | +0.49 / +0.42 / +0.41 % | -0.22 / -0.28 / -0.29 % |
| reference board, 8 layers | +1.00 / +0.97 / +0.96 % | -0.04 / -0.06 / -0.07 % |

The FVM moves by 0.03 to 0.08 points from 1 to 0.25 mm; the gap is the edge loss that the cosine series (insulated edges) leaves out. Suggested text for item 1: "... the FVM is its **numerical** solution; on a uniform board they differ by the edge loss that the Analytic leaves out (insulated edges): +0.3 to +1.0 % with the default `h_side` of 10 W/m2K, -0.04 to -0.29 % when the FVM's edges are insulated too; the FVM's own mesh error is under 0.1 point from 1 mm." The same sentence in `docs/validation.md` section 2 ("0.3 to 1.0 %; the FVM has its own mesh error") should read "(0.3 to 1.0 %: the edge loss the Analytic leaves out, not the FVM's mesh)". `docs/theory.md` 6, "Where it fails", could add: "even the default edge coefficient (10 W/m2K) makes the Analytic 0.3 to 1 % warm on a uniform board".

## 2. `docs/theory.md`

* **Section 11, table**: "Linear solvers ... agree to 10⁻⁸ K" -> "agree to 2·10⁻⁸ K" (`validation.md` 5: 1.7e-8 K on the 8-layer board); "Mesh and model comparison: 20 scenarios" -> "19 scenarios" (the table of `validation.md` 2 has 19 rows; also listed in `research/REVIEW.md`).
* **Section 2, "Accuracy"**: "within 0.2 % from 1 mm" -> "within 0.25 % of the 0.25 mm value from 1 mm" (`validation.md` 2.1).
* **Section 2, vertical conductance**: "this costs about 0.5 % against the 3D rods on the example board" is true at 0.5 mm, but the point via does not converge with the cell (via-array board, gain of a copper fill -4.78 / -4.38 / -3.98 / -3.34 K at 1 / 0.5 / 0.25 / 0.0625 mm against -4.45 K with resolved barrels, `research/via-fill/README.md` 7.3); see `research/via-fill/docs/for-the-project-documents.md`.
* **Section order**: 1.4 (one-layer board) comes before 1.3 (sources and geometry). Move 1.4 after 1.3, or renumber.

## 3. `docs/models.md`

* **Two sections numbered 8** ("8. The application" and "8. Stack-up: simple and advanced"); the numbers after them are therefore shifted against the references in the other documents. Renumber, keeping the anchors that `theory.md`, `validation.md` and the topics of `research/theory` use.
* **Section 3, input checks**: the list lacks warnings that `checks.py` gives: plate fins closer than still air allows, a footprint of zero area, more than half of a zone outside the board, part of a metal block outside the board, two heatsinks that overlap (only the later one is used in the overlap); and the after-run thick-plate warning (section 4b). Suggested: add "fins closer than still air allows, a zero-area footprint, zones or blocks partly outside the board, overlapping heatsinks; after the run, the thick-plate check of section 4b".
* **Section 18**: "At the same Rayleigh number the facing-down coefficient is half the facing-up one" holds up to Ra 1e7; above it the facing-up law is `0.15 Ra^(1/3)` and the ratio falls (0.32 at 1e9). Suggested: "... half the facing-up one up to Ra = 1e7".

## 4. `docs/research.md` R2

* "The default paste costs only 0.6 to 1 K against a good paste": the table it comes from (`research/component-heatsink/README.md` 4.5, table E) gives 0.1 to 0.6 K on the four parts (MOSFET 0.6, LDO 0.2, buck 0.1, diode 0.1 K).
* "1 mm 76.8, 3 mm 74.3, 6 mm 71.7 °C with fins" and "71.7 to 72.2 °C": printed by no script; `study_notes_r2.py` prints 76.4, 73.8, 71.2 and 71.2 to 71.8 °C (`research/component-heatsink/NOTES.md`, which already has the printed values).

## 5. `docs/versions.md` "Planned"

* The text of `research/theory/docs/roadmap-entry.md` ("Open points of the research branch") is not in `docs/versions.md` "Planned"; the file said it had been added. Updated there for what changed since (the 3D one-layer laminate is corrected in the program; Culham and Yovanovich 1998, Lush 2004, Milton chapters 3 and 23 and the multigrid primer's byline were read or confirmed).
