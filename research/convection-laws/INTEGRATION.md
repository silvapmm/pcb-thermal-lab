# convection-laws: design for entering the program (proposals, nothing is edited here)

Everything below was measured on a copy of the program in memory (`research/horizontal-plate-h/lib/correlations.py` `use_horizontal`, called by
`scripts/study_board_effect.py`); `pcbthermal/` is untouched.

## 1. What would change

`pcbthermal/convection.py`, `h_natural_horizontal` only (and its docstring, `docs/theory.md` 8, `docs/models.md` 5, the frozen records that move).

| option | face up | face down | status of the sources |
| :-- | :-- | :-- | :-- |
| A (keep) | `0.54 Ra^(1/4)` (above 1e7 `0.15 Ra^(1/3)`) | `0.27 Ra^(1/4)` | up: Lloyd-Moran from memory, outside its range (2.2e4 to 8e6) for most boards; down: exponent 1/4 against 1/5 in every published form |
| B (recommended in the end, see section 3) | Raithby-Hollands, Lienhard eq. 8.37a/b with the correction 1.4/ln(1 + 1.4/Nu) below Nu = 10, for 1 < Ra < 1e7; eq. 8.35 `0.14 Ra^(1/3) (1 + 0.0107 Pr)/(1 + 0.01 Pr)` from 1e7 (a jump of +25 % at 1e7, no board of the harness is there) | `0.475 Ra^(1/5)` on A/P, the mean Goldstein-Lau value of Yovanovich and Jafarpur 1993 page 8 (read on the page image; the Goldstein-Lau paper itself not obtained), range `40 < Ra < 8e3` of their strip, extended by the Ra^(1/5) form | up: R (Lienhard pages 435 and 436, images), down: R second hand |
| C | B for the face up; the down face of Jaffer (2023) eq. 56 (a fit to water data with the shape metric `L_R`) | | R for the paper's text, data not opened |
| D | B plus a measurement-based multiplier per face | | after the measurement of `docs/measurement-plan.md` |

## 2. Measured impact (README section 6; FVM 2 mm, computed h, horizontal, the 17 boards of the regression harness)

Change of the hottest rise against the program (with radiation / convection only):

| pair | min | max | mean | min | max | mean |
| :-- | --: | --: | --: | --: | --: | --: |
| RH up, program down | +0.2 % | +1.7 % | +0.99 % | +0.4 % | +3.3 % | +2.44 % |
| **RH up, Goldstein-Lau down (B)** | **-0.9 %** | **+1.0 %** | **+0.26 %** | **-1.7 %** | **+2.9 %** | **+0.97 %** |
| RH up, Fujii-Imura strip down | -0.3 % | +1.5 % | +0.76 % | -0.2 % | +3.9 % | +2.16 % |
| Jaffer (C) | -0.7 % | +0.7 % | +0.28 % | -0.7 % | +2.7 % | +1.18 % |

(at double and half power the RH + GL extremes are -0.5 / +1.2 % and -1.5 / +0.9 %.) In kelvin: 0.1 to 1 K on the boards of 60 to 80 K rise and up to 2.4 K on the 300 K plate with a pad. The vertical board does not change.
Frozen numbers: **none moves** (review correction: the first version of this file said that every record of a horizontal board with computed h moves and asked for a pending file; the
17 boards of `tests/regression/regress_boards.py` all use the manual coefficients, `Board.h_mode` defaults to `manual` and `pcbthermal/data/defaults.json` keeps `manual` for new
projects, so the frozen file is untouched; the study forces `computed` on each board to measure the effect). What moves is every result with computed h on a horizontal board: the
program's tests of the convection functions and of computed h, `docs/validation.md` rows with computed h, and the user's own projects that chose computed h.

## 3. Recommendation (reviewed)

**The cost of each way** (estimates of work, not measured):

| way | cost | what it buys | risk |
| :-- | :-- | :-- | :-- |
| measure first (board D, then E) | boards about 100 to 150 EUR, a film heater, a logger the maintainer may already have; one to two days of bench work and one of analysis (`docs/measurement-plan.md`) | the only evidence that can choose the law of a board in free air: separates Jaffer and the program from Raithby-Hollands with Goldstein-Lau at the 0.03 resolution of the ratio (neighbouring laws are one resolution apart); board E tests the coupling of the faces that the 2D solvers suggest (+13 % on the rise if real) | draught, the back loss and the wire loss (the plan states them); one bench, one board size |
| option B now | one function (`h_natural_horizontal`), its docstring, `docs/theory.md` 8, `docs/models.md`, the user guide sentence, the tests of the convection functions; a `fix/horizontal-laws` branch with the whole battery; no frozen record moves | laws read in their source (face up within its range; face down with the exponent of every published form); results move by -0.9 to +1.0 % of the rise with radiation, -1.7 to +2.9 % without, on the 17 boards with h forced to computed | changes the numbers of the users' computed-h projects for a gain that no measurement shows; the 0.475 is a mean of shapes, not the board's |
| keep and write the limit (A) | the paragraph of `docs/theory-text.md` into `docs/theory.md` 8 (most of it is already there since `docs/convection-theory-fixes`) | honesty at no cost; the effect on a board is about 1 % of the rise | none on the numbers; the down-face exponent stays wrong in form |

**Reviewer's recommendation: keep the laws and write the limit now (A), and measure board D (and E) before any change.** The effect of B on a board (about 1 %, below the 2 to 3 % of a measurement and the 3 to 5 % of the models) does not justify moving users' numbers without evidence; the measurement is cheap and is the only way to choose. If the maintainer prefers a change without measuring, B is the defensible one.

## 3a. Recommendation of the first version (kept as written)

1. **The measurement is the decision, and it is cheap** (`docs/measurement-plan.md`, board D: the ratio of the rise with a bright face up and down is 0.62 for the program, 0.69 for B,
   0.66 for Raithby-Hollands with Fujii-Imura, 0.52 for Jaffer, a spread five times larger than the resolution). The numerical plate solved here cannot decide it (README section 5: the two-dimensional steady
   symmetric flow is not the flow above Ra of about 1e4, and the cold box adds cooling).
2. **If the maintainer wants to change before measuring, B is the option that rests on sources that were read**: the face up in its published range with a read equation, the face down
   with the exponent of every published form. The effect is -0.9 to +1.0 % of the rise (mean +0.3 %); no board gets worse than the old law is wrong (the old law is not proven conservative on either face).
3. If nothing is measured and nothing changes (option A): document the limit (the sentence is in `docs/theory-text.md` of this folder).

## 4. Acceptance tests for B (if adopted on a `fix/horizontal-laws` branch)

* `h_natural_horizontal` against the values of README table 3.1 (Raithby-Hollands at Ra 1e2, 1e3, 1e4, 1e5: 1.977, 3.064, 4.965, 8.324 at Pr 0.71, computed from eq. 8.37; the Goldstein-Lau column) within 1e-3, and continuity of the correction at Nu = 10.
* A cold surface swaps the faces (existing test); vertical boards unchanged bit for bit.
* The 17 boards of the harness at 2, 1 and 0.5 mm: every frozen record bit-identical (they use manual h); the effect of section 2 is checked by `scripts/study_board_effect.py` with h forced to computed (-0.9 to +1.0 % with radiation).
* `docs/theory.md` 8: the sentence on the laws and its sources by key, Ra range stated, the discontinuity at 1e7 stated; `docs/models.md` 2; `tests/test_docs.py` unchanged.
* Reproduction by the reviewer of the section 2 numbers (`scripts/study_board_effect.py`, one minute).

## 5. Risks and limits

* The Goldstein-Lau coefficient is the **mean of three shapes** (disk, square, strip) at Pr 0.71; its strip value is 0.524 (page 8), the range of C is 0.44 to 0.527: the choice of 0.475 is a mean, not a value for the rectangle of the board (the board is a square or 1.25:1 rectangle, for which the published square is the lower end).
* Both new laws are tested by the author against numerical solutions of the strip, not against a board; the measurement does that.
* The jump at 1e7 of the face up (+25 %) is real in the source (the two equations are separate fits); a joined form (the larger of the two, as Lienhard says for inclined plates) would switch at Ra = 6.8e5, inside the range of a 200 mm board at 40 K: not recommended without a measurement.
