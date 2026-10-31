# horizontal-plate-h: how it would enter the program

Nothing of `pcbthermal/` was edited. Everything below was measured on copies in memory (`lib/correlations.py`, `scripts/study_board_effect.py`). The numbers are in `README.md`; this file gives the proposals, their measured impact and what is left to the maintainer.

## 1. What was found, in terms of decisions

| Finding | Evidence | Size of the effect on the rise of a board |
| :-- | :-- | :-- |
| The upper-face correlation of the program (0.54 `Ra^(1/4)`, then 0.15 `Ra^(1/3)`) is within the scatter of the measurements that Jaffer fits (3 to 7 % low over `Ra` 1e3 to 5e5 of `A/P`) | README 3.2, section 4 | none worth a change |
| The lower-face correlation (0.27 `Ra^(1/4)`) has the wrong exponent against the published forms (`Ra^(1/5)`) and no shape dependence: equal to Jaffer's square at `Ra` 1e3 and 15 to 43 % above it from 1e4 to 3e5, 29 % below his long strip at `Ra` 1e3 and equal at 1e5 | README 3.2 | 0.4 to 1.7 % of the rise with radiation (4 % at most without), at most 3 % for the finned block with fins down (README 7) |
| Schulenberg's printed coefficients are consistent; Jaffer's correction replaces a number of the report | README 3.1 | a statement for the documents, no code |
| A thin board with both faces hot loses part of its upper-face coefficient to the warm air of the lower face (30 to 45 % in the solver) | README 6 | if it were real at that size: +2 to +10 % of the rise (+5 % for the two examples), +3 to +5 % for the finned block with fins down; with radiation removed up to +21 % |
| The solver cannot reproduce the measured upper face | README 5 | the size of the coupling is therefore not established; the measured upper-face data are for isolated faces |

## 2. Proposals

**A. Document the limit (recommended; no change of the program).** Text for `docs/theory.md`, `docs/models.md` and `docs/validation.md` is in `docs/theory-text.md` and `docs/research.md`: the horizontal coefficients are textbook correlations for an isolated face with `L = A/P`; the upper face is within the scatter of the measurements; the lower face has the wrong exponent and no shape dependence and may be 29 % low (long strip, small `Ra`) or 43 % high (square, large `Ra`); the air warmed by the other face of a free board is not modelled; the effect on the rise is a few percent with radiation (the program's default), up to 4 % (lower face) or 21 % (a 40 % loss of the upper face) without it. No warning text in the interface is proposed (the effect does not reach the size at which the existing warnings fire); a line in the user guide's section on heat transfer would be enough. This is the maintainer's rule for a limit of the model.

**B. Jaffer's forms as an option (not recommended now).** `Board.natural_form`-like switch (`horizontal_form`: `textbook` (default, bit-identical) or `jaffer`), with the shape factor `q` of the lower face taken from the outline (`q = (half the shorter side)/(A/P)` for a rectangle, `4/pi` for a disc; a general outline would need the harmonic-mean construction of Jaffer's equation 57). Measured impact on 12 boards and 3 finned blocks: the rise changes by **-2.8 to +0.5 %** (convection and radiation) and **-4.0 to +1.7 %** (convection only); the finned block with fins down by -0.6 to -0.5 %. The source is a fit of one author to plot values, the lower-face formula is a derivation that its author describes as a bound, and its shape metric needs a new geometry routine: more machinery than the effect warrants.

**C. A correction of the upper face of a free board (not recommended).** The solver's coupling (README 6) cannot be turned into a coefficient: it comes from a steady symmetric two-dimensional solution that does not reproduce the isolated upper face of the measurements (12 to 36 % below at `Ra` 1e2 to 1e4, and no usable answer at 1e5). A factor would be a guess, and "up x0.6" is only a sensitivity (README 7).

## 3. What would change the conclusion

* A measurement or a three-dimensional unsteady solution of a thin free horizontal plate with both faces heated in air, at `Ra` 1e3 to 5e5: it would give the size of the coupling (C8 stays open for that case, see `research/ROADMAP.md`).
* The originals of Fujii and Imura (1972), Al-Arabi and El-Riedy (1976), Raithby and Hollands (handbook chapter) and Lloyd and Moran (1974) read, and the downward measurements below `Ra` 1e5 (only Goldstein and Lau, 250 to 4500, 10 % scatter, are in that range).
* The radiation between close fins and between the fins and the ground, which the fins-down finned block needs more than the convection correlation (C9, not solved here: the finned block was run with the program's uniform fin coefficient; the sensitivity of its rise to the lower-face coefficient is -2.4 to -2.6 % for +30 % and +2.9 to +3.0 % for -30 %).

## 4. Risks and what does not change

No input file, no model, no result of the program changes under proposal A. Under B a new key would have to be saved and old files keep `textbook`; the test of equivalence at `textbook` would be bit-identity of the examples. The vertical orientation (`plate-h-level`) is untouched, and so is the forced convection and the radiation.
