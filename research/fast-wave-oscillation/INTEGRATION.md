# Integration: fast-wave-oscillation

Recommendation, for the maintainer to decide. Nothing of the program was edited; the prototype is in `lib/` and was measured on copies (README 5).

## What is wrong (program, measured)

The decision average-or-resolve (`profiles.decide`) and the resolved curves of the FVM and FDM understate the swing of a square wave whose period is below about 5 s (1.6 mm, two layers) by 2 to 3 times at 1 to 3 Hz and 8 to 12 times from 50 Hz to 1 kHz (4 layers: 5 to 7). In the sweep (864 cases, 5184 decisions) a wave whose true swing exceeds the 1 K budget is averaged in 948 decisions (18 %), never the other way. Cause: the laminate capacity of the slab (0.77 mm of FR-4 per node) sits on the copper node (README 3).

## Proposal A (smallest, recommended): the floor E3 in the decision

In `profiles.decide`, for a heater with a repeating square wave on a layer with copper under its footprint (fill at least 0.9 in the heater's layer) and a period below `T_w = 5 s (s / 0.8 mm)^2` (s = thickness / layers; README 6): `oscillation = max(oscillation_program, E3)`, E3 = `impedance.square_swing` of `lib/impedance.py` (the stack under the footprint by the layer recursion with `tanh`, the top copper as a sheet with a Bessel disc term, one inverse FFT). No unknowns, 2 ms per heater and wave, nothing else changes (steady results, step responses, frozen numbers: none of the 251 records and 58 times of `tests/regression` moves, the harness has no profiles). Measured: 0 wrongly averaged in 5184 decisions (948 before), 12 borderline resolves.

Changes: a new function in `profiles.py` (or `laminate.py`), the call in `decide`, the decision text of `docs/theory.md` 10, `docs/models.md` 4, the user guide's power-profile page ('why was my wave resolved'), `docs/validation.md` (a section with README tables 1 and 3). Tests that would move (reasoned, not run): `tests/test_profiles.py` (U1 of `example_with_profiles()` at 100 Hz, 4 W / 30 %, goes from average to resolved: 0.39 K -> 2.01 K; the mixed-regimes test; use 1 kHz, 0.23 K, to keep an averaged case), `tests/test_gui_profile.py`, the stress scenarios of the profile page, the `examples/profile_board` result and its screenshots. Not covered by E3 (keep the old behaviour there and the warning): a heater on an inner or bottom layer (needs the recursion from that layer, both sides), partial copper and bare laminate, vias (E3 overstates: the safe side).

## Proposal B (after A, larger): the ripple of a resolved fast heater

The resolved curves have the same error (README 4). For a heater whose period is below `T_w`, average it in the board run and add the E3 waveform (the harmonic sum, centred on the mean) at that heater: peak = average-run temperature + the positive half of the ripple. This also removes the cost of resolving kilohertz waves (the 200 000-step limit). Not prototyped: needs the ripple's phase against slow neighbours and the report of peak and minimum, so it is a feature with its own tests.

## Proposal C (not recommended): laminate cells under the footprint

Converged only with 16 graded cells (1.5 um first) or 64 equal sub-gaps per gap under the part (README 3, figure 3): an order more unknowns locally, a new coupling to the neighbouring cells. The column difference (README 5.1) overshoots at the slow end and is rejected.

## If A is not adopted: warning only

Warn from the stack and the period alone (README 6): "the layered models average the laminate; the swing of a wave faster than T_w is understated by about 8 times".

## Risks

E3 is validated against one independent reference (the axisymmetric modal solver of this folder, itself tied to the 6.31 K of an earlier independent 1D solution and to the semi-infinite solid) over one family of boards (full copper, top-layer heater, no vias); the decisions near the budget could flip by up to 11 %; a reviewer should repeat the sweep with a heater on an inner layer and with vias before an adoption.
