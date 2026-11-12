# Integration: fast-wave-oscillation

**Status (audit 2.6.1): A, B, D and W2 are implemented in 2.6.0** (`fix/fast-wave-ripple`, reviewed: the criterion of B is the shortest stretch, the heater's copper a slab of the column, repeating power tables get the floor too; `docs/validation.md` 37); C and W are not (W was the alternative to A and B). What is left is in 'Planned', "Fast waves, what is left". The text below is the recommendation as written.

Recommendation, for the maintainer to decide. Nothing of the program was edited; the prototypes are in `lib/` and were measured on copies (README 5 and 8). The review (README 8) changed the recommendation: the floor in the decision (A) is not to be adopted alone.

## What is wrong (program, measured)

1. The decision average-or-resolve (`profiles.decide`) and the resolved curves of the FVM and FDM understate the swing of a square wave whose shortest stretch (on or off time) is below about 4 s (1.6 mm board, one or two layers; about 2 s on four layers) by 2 to 3 times at 1 to 3 Hz and 8 to 12 times from 50 Hz to 1 kHz (4 layers: 5 to 7). Cause: the laminate capacity of the slab (about 0.77 mm of FR-4 per node) sits on the copper node (README 3). Checked against two independent references that agree within 2 % (README 8.1, 8.2).
2. In a sweep the decision averages a wave whose true swing exceeds the 1 K budget in 18 to 20 % of the decisions, never the other way (README 4, 8.2).
3. **The application makes it worse** (review, README 8.3): `api._step_response` computes the step response at `max(cell, 2 mm)`; a 2 mm part is one cell and its decision swing is 0.67 of the truth already at 0.1 Hz; wrong averages 24.7 % on the review's sample, worst true swing averaged 37.5 K.
4. **The resolved curve has the same error** (review, README 8.7): 0.741 K against 6.375 K for the 20 Hz, 30 %, 10 W wave of a 10 mm part, in the FVM and the FDM, with implicit Euler and Crank-Nicolson.
5. A part on bare laminate: the node plus the face term is 0.46 to 0.82 of the truth from 10 to 100 Hz and 1.3 to 4.1 times above 300 Hz (README 3 (b) as corrected, 8.5).

## Decisions for the maintainer, with the recommendation of the review

| item | what | recommendation | measured effect |
| :-- | :-- | :-- | :-- |
| A | E3 as a floor of the decision, `oscillation = max(program, E3)`, for a heater whose layer has copper under the part (fill at least 0.9), **at every period** (no T_w gate), with the **two-sided** admittance for an inner layer (`lib/impedance_layer.py`) | **adopt in 2.6.0, only together with B** | 0 wrong averages in 5184 + 3168 decisions on full copper (948 and 634 before), 0 wrong resolves with the two-sided form; overstates up to 1.57 with vias, planes, elongated parts (safe side, a few extra resolves of slow waves, which are cheap) |
| B | a heater whose shortest stretch is below the node's window is **averaged** in the board run, and its curve and its peak get the E3 waveform (the harmonic sum without its mean) added at that heater | **adopt in 2.6.0 with A** | the curve then agrees with the decision (6.36 K instead of 0.74 K for the headline case); no time steps for kilohertz waves, so the example board stays under the step limit; 2 ms per heater |
| D | the step response of the decision at the cell of the run (or side / 4, at most the cell), not `max(cell, 2 mm)` | **adopt as a `fix/` (2.6.0 or a patch)** | 2 mm parts: 24.7 % -> 20.0 % wrong averages without A; with A the decision is covered, but the curves and the steady peak of the profile run still use the coarse response; its cost (finer step responses) to be measured on the fix branch |
| C | laminate cells under the footprint | **no** | 8 graded nodes per gap for 10 to 20 % (README 8.7 table), and the run still needs steps a twentieth of the shortest stretch |
| W | a warning instead of A and B | **only if A and B are not adopted**; the rule on the **shortest stretch** `t_s < 4 s` (one or two layers), `< 2 s` (four layers), not the T_w on the period of README 6 (corrected) | — |
| W2 | warning for a part on bare laminate with a wave of 3 to 300 Hz (E3 does not apply; 2.2 times low at 10 Hz) and for a part within a few millimetres of the board edge with a wave below 1 Hz (E3 0.61 to 0.88) | **adopt with A and B** (text only) | — |

## How A and B would enter the program

* `profiles.py`: a function `fast_swing(problem, heater, profile)` (E3 of `lib/impedance.py`, two-sided as `lib/impedance_layer.py`; the stack as the FVM reads it (gaps, dielectric properties, copper thickness), the disc of the part's area, `h_top` / `h_bottom` of the effective problem, so computed h is the steady value as now); in `decide`, the floor; in `run_windows` and the reports, the ripple added to the averaged fast heater (a new regime name, for example 'average + ripple', in the decision table and the user guide).
* Documents: `docs/theory.md` 10 (the decision and the ripple), `docs/models.md` 4, `docs/validation.md` (a section with README tables 1 and 8.4), the user guide (why the wave was resolved or averaged with a ripple).
* Tests that would move: `tests/test_profiles.py` (U1 of `example_with_profiles()` at 100 Hz: average -> average + ripple of 2.0 K; the mixed-regimes test: the fast heater 0.75 -> 6.36 K), `tests/test_gui_profile.py`, the stress scenarios of the profile page, `tests/test_fdm.py`, `tests/test_convection.py` and `tests/test_memory.py` (they run `example_profile_board()`), the screenshots of the profile page. **A alone would not move these numbers but break the runs**: the example board with U1 resolved needs 800 004 steps against the limit of 200 000 and the run is refused (README 8.7).
* Frozen numbers: none of `tests/regression` moves (the harness has no profiles).

## Risks and what is not verified

E3 rests on two references (the author's axisymmetric modal solver and the reviewer's Cartesian frequency-domain solver) and on the semi-infinite solid (Lienhard eq. 5.62); no published fast-wave case of a layered board and no measurement exist. Not verified: the Lumped and Analytic step responses (they make the decision when neither the FVM nor the FDM is selected), an outline, a metal block, several heaters sharing the budget, 10 kHz with the reviewer's reference. Near the board edge at slow waves E3 understates and the floor gives no protection (README 8.4).
