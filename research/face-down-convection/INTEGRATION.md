# INTEGRATION: the law of the face turned down

Proposal for a `fix/face-down-convection` branch off `develop` (a change of numbers at computed h, so it is a decision of the maintainer; the program is not edited from the research branch).
Evidence: `README.md` sections 3 to 5.

## 1. Recommendation

Replace the face-down law `Nu = 0.27 Ra^(1/4)` by `Nu = 0.52 Ra^(1/5)` on `L = A/P`.

* Decision A (preferred): `0.52 Ra^(1/5)` (Incropera and DeWitt, later editions, `1e4 <= Ra <= 1e9`). **Condition**: someone opens the book (or the maintainer does) and confirms the constant and the range; it is status M here. Rises: -0.5 to -2.2 % of the hottest rise on the 17 boards at computed h.
* Decision B (if the constant cannot be confirmed): `0.475 Ra^(1/5)`, the mean of the Goldstein-Lau constants read on page 8 of Yovanovich and Jafarpur (1993). Rises: -0.3 to -1.4 %. It is 9 % below A at every Ra; both lie inside the 9.5 % cluster that includes VDI.
* Keep the program's law (decision C): the program is the hot side at the boards' Ra, 10 to 36 % lower in h at Ra 1e3 to 1e4 than every 1/5 law read; keeping it costs 0.5 to 2 % of the rise (up to 5 % without radiation), written as a limit already.
  A reason to choose C is conservatism, but a model that is 20 to 30 % low in h on one face with the wrong exponent is not an honest basis for "conservative", and the up face already carries the same level of uncertainty the other way.

Not proposed: a shape factor (Jaffer's square vs strip, +-17 %), a rule per Rayleigh range, or removing the 0.54 law of the face up (a separate decision in `research/convection-laws/INTEGRATION.md`).

## 2. The change in the program

`pcbthermal/convection.py`, function `h_natural_horizontal`: the line `nu = 0.27 * ra ** 0.25` (the `else` of the face up) becomes `nu = 0.52 * ra ** 0.2`, and the docstring says
"facing down: Nu = 0.52 Ra^(1/5)" with the source and the range. One constant (a named constant for the pair 0.52 and 0.2 is optional). The face of a surface colder than the air looking up takes the same law as in the program (the `up` swap is untouched).
No new warning: the existing low-Rayleigh warning (face Ra below 1e3 for vertical boards, `checks.check_low_rayleigh`) stays as it is; the law is used from 1e2 to 1e9 and a board at Ra above 1e9 on the face down does not exist at 400 mm and 80 K (4e6).
Extending `check_low_rayleigh` to the horizontal faces is a separate item.

## 3. Documents, user guide and tests that change

| where | change |
| :-- | :-- |
| `docs/theory.md` 8 (line "hot face down `Nu = 0.27 Ra^{1/4}`" and "Limit of the face turned down") | the new law with its sources and status (text in `docs/theory-text.md`); the limit paragraph keeps only the finite-size, edge-circulation and range statements; the 20 % and 10 % against Goldstein-Lau are history (to `docs/versions.md`) |
| `docs/models.md` 2 (line 192) and 5 (line 413) | the law, `Ra` range (1e4 to 1e9 as printed, used from 1e2), the "conservative side" sentence replaced by the edge-circulation limit |
| `pcbthermal/help/index.html` (the line on face down) and `tests/test_docs.py` (lines 111 to 121: `"exponent 1/5"`, `"Limit of the face turned down"`, `"conservative side"`) | the strings follow the new text; the test must keep that the law is not attributed to Lienhard |
| `tests/test_orientation.py::test_horizontal_board_matches_the_textbook_formulas_written_out_by_hand` | the only test of the program that fails (measured); the written-out coefficient for the bottom face becomes 0.52 with exponent 0.2 |
| `docs/versions.md` 'Planned' item "Horizontal-face laws revisited" | the face-down half is done; the face-up half (Raithby-Hollands) stays and moves with the measurement |
| `docs/validation.md` 22 and the table at line 334 (computed h) | the numbers of the examples that use computed h horizontal move (example board 60.06 -> 59.55 K) |
| `CHANGELOG.md`, Decisions Log | one entry |
| a test that fails on the old law | the face down at Ra 1e3 and 1e4 against Lienhard-style hand values and against `0.475 .. 0.524` Goldstein-Lau band (the program was outside it: 1.52 against 1.89 to 2.09) |

The Results-summary line that says the computed coefficients were never compared with a measured copper board **stays** (`api.CONVECTION_NOT_MEASURED_NOTE`): this change is a correction to the published literature, not a measurement.

## 4. Frozen numbers

None moves. The 17 harness boards use manual coefficients, so `h_natural_horizontal` is never called when the frozen records are built (counted: 0 calls on each board, `README.md` 5). No `data/pending/` file is needed.
Boards at computed h horizontal move by -0.5 to -2.2 % of the hottest rise (all cooler); vertical boards, the Lumped and the Analytic use the same board h and move the same way; the 3D solid takes the same h.
The harness has no computed-h board; adding one (the example board, horizontal, computed h, the five models) to `tests/regression` in the same branch would hold the new numbers for the next release (decision for the maintainer).

## 5. Effort

One line of code, one test edited, one test added, about six lines of text in four documents, one regression board optional: about half a day including the battery, much less than any of the other items of 'Planned'. The reviewer should open Incropera (or any edition 7 or later of Chapter 9) before the constant is committed.

## 6. Risks

* The constant is M. If the book says otherwise (for instance a different range or constant), decision B is the fallback and costs nothing else.
* A face with components, an enclosure or a wall below is below every law here (Lienhard: edge circulation); the correction moves the model **away** from that case by 0.5 to 2 % of the rise; this is the same limit as before, now written for both laws.
* The correction cools the boards by up to 2.2 % of the rise: a user who tuned the convection multiplier (`h_calibration`) to a measurement on the old law sees a small shift. Release note.
* At Ra above 1e6 the program's law is higher than the 1/5 laws, so large boards (400 mm at 80 K) become 0.1 to 0.3 K/K hotter: -10 % in h; it is the direction of safety and inside the scatter of the published forms.

## 7. What the measurement (board D) would add

The one thing nobody has for a printed circuit board: the size of the edge and obstruction effects on the face down (face free against a wall 20 mm below, with and without components on that face) and the ratio rise-up to rise-down (0.62 / 0.69 / 0.52 depending on law). If the measurement disagrees with the 1/5 level by more than the 9.5 % cluster, the convection multiplier is the right place (`h_calibration`), not another exponent.
