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

(the same boards at half and double power move the extremes by 0.3 points.) In kelvin: 0.1 to 1 K on the boards of 60 to 80 K rise and up to 2 K on the 300 K plate. The vertical board does not change.
Frozen numbers: every record of a horizontal board with computed h moves by the percentages above (FVM, FDM, 3D solid, Lumped, Analytic in the same direction): a pending file
(`tests/regression/data/pending/<topic>.json`) as in the rules of the regression test.

## 3. Recommendation

1. **The measurement is the decision, and it is cheap** (`docs/measurement-plan.md`, board D: the ratio of the rise with a bright face up and down is 0.62 for the program, 0.69 for B,
   0.66 for Raithby-Hollands with Fujii-Imura, 0.52 for Jaffer, a spread five times larger than the resolution). The numerical plate solved here cannot decide it (README section 5: the two-dimensional steady
   symmetric flow is not the flow above Ra of about 1e4, and the cold box adds cooling).
2. **If the maintainer wants to change before measuring, B is the option that rests on sources that were read**: the face up in its published range with a read equation, the face down
   with the exponent of every published form. The effect is -0.9 to +1.0 % of the rise (mean +0.3 %); no board gets worse than the old law is wrong (the old law is not proven conservative on either face).
3. If nothing is measured and nothing changes (option A): document the limit (the sentence is in `docs/theory-text.md` of this folder).

## 4. Acceptance tests for B (if adopted on a `fix/horizontal-laws` branch)

* `h_natural_horizontal` against the values of README table 3.1 (Raithby-Hollands at Ra 1e2, 1e3, 1e4, 1e5: 1.977, 3.064, 4.965, 8.324 at Pr 0.71, computed from eq. 8.37; the Goldstein-Lau column) within 1e-3, and continuity of the correction at Nu = 10.
* A cold surface swaps the faces (existing test); vertical boards unchanged bit for bit.
* The 17 boards of the harness at 2, 1 and 0.5 mm: shifts within the table of section 2 (-1.0 to +1.7 %), every other record bit-identical; a pending file for the horizontal computed-h records.
* `docs/theory.md` 8: the sentence on the laws and its sources by key, Ra range stated, the discontinuity at 1e7 stated; `docs/models.md` 2; `tests/test_docs.py` unchanged.
* Reproduction by the reviewer of the section 2 numbers (`scripts/study_board_effect.py`, one minute).

## 5. Risks and limits

* The Goldstein-Lau coefficient is the **mean of three shapes** (disk, square, strip) at Pr 0.71; its strip value is 0.524 (page 8), the range of C is 0.44 to 0.527: the choice of 0.475 is a mean, not a value for the rectangle of the board (the board is a square or 1.25:1 rectangle, for which the published square is the lower end).
* Both new laws are tested by the author against numerical solutions of the strip, not against a board; the measurement does that.
* The jump at 1e7 of the face up (+25 %) is real in the source (the two equations are separate fits); a joined form (the larger of the two, as Lienhard says for inclined plates) would switch at Ra = 6.8e5, inside the range of a 200 mm board at 40 K: not recommended without a measurement.
