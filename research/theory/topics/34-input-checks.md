# 34. The input checks: what makes a result doubtful

![Input checks](../figures/fig_27_input_checks.png)

*Figure 27 (`figures/fig_27_input_checks.png`): one board with the situations that `check_problem` warns about: 1 a heater partly outside the board, 2 no copper under a heater, 3 a copper edge crossing a footprint, 4 a heater only a few cells wide, 5 overlapping heaters, 6 a via outside the board, 7 a metal block with no copper under it. Items 8 and 9 and the last line were added for the checks that came later (fins closer than a still-air gap, the thick-plate check after the run, the 3D size limit).*

**Status: in program** (`pcbthermal/checks.py`, `docs/models.md` section 3).

## 1. What it does

`check_problem` (also run by `simulate` and live in the application under the Run button) **never blocks a run**. It lists, in plain words with what is wrong and what to do, the inputs that make a result physically doubtful. The warnings are the program's honesty about where the models are known to fail (topics 05, 06, 11, 20):

| # | Situation | Why it matters |
| :-- | :-- | :-- |
| 1 | a heater partly outside the board | its power is moved onto the part inside |
| 2 | no copper under a heater | the heat has only the laminate to spread in; Lumped and Analytic assume copper |
| 3 | a copper edge or hatching crossing a footprint | Lumped and Analytic unreliable (27 % low with an edge across the footprint, topics 05 and 06) |
| 4 | a heater only a few cells wide | the footprint is poorly resolved (thin heaters, +9.5 % in Lumped) |
| 5 | overlapping heaters | the powers add on the same cells |
| 6 | vias or zones outside the board | they are ignored |
| 7 | a metal block with no copper under it, or an almost perfect contact | the heat has no path into the block, or the contact is optimistic (topic 24) |
| - | zero total power | there is nothing to simulate |

The Results summary also carries the warnings of the models themselves (a model skipped on an outline, a block refused in time, the Analytic transient smearing vias).

## 2. Where it is tested

`tests/` (the checks) and the stress test of the application (bad inputs, odd boards).

## 3. Related topics

05, 06, 11, 20, 24.

## 4. Sources

Own design; the failure cases are measured in `docs/validation.md` sections 2, 3 and 13 ([L-validation]).

*What was read and what was not verified:* from `docs/models.md` section 3 (read in full); the thresholds inside `checks.py` were not re-derived here.
