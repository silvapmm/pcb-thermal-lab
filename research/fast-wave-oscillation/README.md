# fast-wave-oscillation

Question: with one node per copper layer the FVM and FDM understate the oscillation of fast square waves over full copper (`docs/validation.md` 36.2 and 36.3 of `fix/laminate-edge-band`: a 20 Hz, 30 %, 10 W wave on a 10 mm part of a 1.6 mm board reads 0.75 K, an independent 1D solution 6.3 K). Why, over which frequencies and sizes, how often the average-or-resolve decision (`profiles.decide`, budget 1 K) is wrong because of it, and what is the smallest correction. Nothing of the program is edited; the proposal is in [INTEGRATION.md](INTEGRATION.md).

Run (repository root, `QT_QPA_PLATFORM=offscreen`, about 1.5 minutes in all, peak memory under 0.5 GB):
`study_fast_wave_sweep.py` (writes `out/sweep.json`), `study_correction.py` (the rejected column difference), `study_estimator.py` (tables 3 to 5, writes `out/sweep_e3.json`), `study_impact.py`, `make_diagrams.py`, `make_figures.py`; tests: `research/fast-wave-oscillation/tests` (8 passed).

## 1. The reference and the situation

![the heat path of a fast and of a slow wave through the real section, and the program's node](figures/fig_01_section_fast_wave.png)

*Figure 1 (`fig_01_section_fast_wave.png`): the section under a part (copper not to scale). A 20 Hz wave heats the copper and about 0.06 mm of laminate; the program holds the copper and 0.77 mm of laminate (half of the 1.53 mm gap) at one temperature.*

**The independent reference** (`lib/axisym_stack.py`, imports nothing from the program): axisymmetric (r, z) finite volumes of the board as the disc of the same area as the rectangle (60 x 40 mm, radius 27.6 mm), the part a disc of the same area as the square part (uniform flux on the top copper), copper 385 W/mK and 3.45 MJ/m3K in four cells per layer, laminate k_z 0.3 / k_r 0.9 W/mK and 1.665 MJ/m3K in cells that grow from 1.5 um at each copper face (16 per side of a gap; the penetration depth of a 10 kHz wave in FR-4 is 4 um), faces h, insulated edge. The system is symmetric, so it is diagonalised once (1360 to 3800 unknowns) and every response is a sum of exponentials: the periodic steady state of a square wave is a closed form per mode, with no time step and no cycle count. Checks (`tests/test_fast_wave.py`): the steady resistance equals the series-parallel circuit (0.2 %); a bare slab follows the semi-infinite solid `2 q sqrt(t/pi)/e` apart from the expected t_cu/(2 k A) offset of a source spread over the first 35 um (the test is loose: absolute 0.68 K/W on 8.7 and 16 K/W); the 1D column gives 6.33 K and the 2D reference 6.37 K for the case of 36.3, against the **6.31 K** of the independent 1D solution of the review (not rerun here: it is the number in `docs/validation.md`).

**The program's number is reproduced**: `profiles.decide` gives 0.747 / 0.758 K at the 2 mm and 1 mm cell (the wave response itself: 0.7578 / 0.7581), steady resistance 33.13 K/W at 1 mm against 33.05 K/W of the reference. The ratio is **8.4**.

## 2. The sweep (question 1)

Full copper, 60 x 40 mm, 1.6 mm, 35 um, simple stack-up (equal gaps), layers 1, 2 and 4, part 2, 5 and 10 mm (cell: side / 4, at most 1 mm), faces 10 and 30 W/m2K, 12 frequencies from 0.1 Hz to 10 kHz, duty 10, 30, 50 and 90 % (a linear system: the swing is the same for D and 1 - D), 864 cases. The swing is per watt of the on-power, at the centre cell of the top copper (the program's hottest cell of a footprint over full copper is its node; over full copper there is no face term). **Computed h**: the program holds the coefficient at its steady value during the time simulation, so a computed-h board is a board with another manual h; 30 W/m2K is the order of a forced-air or radiating board and it changes no conclusion (the 10 and 30 W/m2K rows are in `out/sweep.json`; E3 below ratio 0.994 to 1.111 over both).

![swing against frequency and the ratio program / reference](figures/fig_02_swing_against_frequency.png)

*Figure 2 (`fig_02_swing_against_frequency.png`): left, reference, program and the closed-form E3 for three part sizes (2 layers, 30 %); right, program / reference for 1, 2 and 4 layers (50 %).*

**Table 1. Program (decision's oscillation) divided by the reference, duty 50 %, h 10** (`out/sweep.json`):

| layers, part | 0.1 Hz | 0.3 | 1 | 3 | 10 | 20 | 50 | 100 | 300 | 1 k | 3 k | 10 k |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| 2, 2 mm | 0.95 | 0.87 | 0.73 | 0.56 | 0.34 | 0.23 | 0.14 | 0.10 | 0.09 | 0.08 | 0.08 | 0.07 |
| 2, 5 mm | 0.92 | 0.79 | 0.55 | 0.31 | 0.16 | 0.12 | 0.10 | 0.10 | 0.09 | 0.08 | 0.07 | 0.04 |
| 2, 10 mm | 0.91 | 0.70 | 0.37 | 0.20 | 0.13 | 0.12 | 0.11 | 0.10 | 0.09 | 0.07 | 0.04 | 0.01 |
| 1, 10 mm | 0.91 | 0.68 | 0.37 | 0.20 | 0.13 | 0.12 | 0.11 | 0.09 | 0.09 | 0.07 | 0.04 | 0.04 |
| 4, 2 mm | 0.97 | 0.94 | 0.87 | 0.75 | 0.55 | 0.42 | 0.27 | 0.20 | 0.17 | 0.16 | 0.15 | 0.15 |
| 4, 10 mm | 0.96 | 0.88 | 0.66 | 0.39 | 0.25 | 0.23 | 0.21 | 0.19 | 0.18 | 0.15 | 0.12 | 0.07 |

The program understates the swing **at every frequency from about 0.2 Hz up** (periods below roughly 5 s on a 1.6 mm two-layer board): by 10 % at 0.1 to 0.3 Hz, 2 to 3 times at 1 to 3 Hz, about **8 to 10 times from 50 Hz to 1 kHz**, and 5 to 7 times for 4 layers (the slab is half as thick, so half the capacity). Across all 864 cases the program is at 0.06 to 0.97 of the reference (median 0.18, 5 % to 95 %: 0.07 to 0.90). The plateau at 8 to 12 is the ratio of the node capacity (1394 J/m2K) to the copper's own (120 J/m2K); it falls to 0.01 to 0.05 above 3 kHz, where the swing is below 3 mK/W and a numerical limit of the program's time grid (first sample 1.8 us, Crank-Nicolson at the first steps) may add to the physical one: not separated here, and irrelevant to the decision (swing below 0.1 K for 10 W).

## 3. What causes it (question 1 a, b, c)

![the step response of the exact and the lumped column, and the swing against the cells](figures/fig_03_column_and_cells.png)

*Figure 3 (`fig_03_column_and_cells.png`): left, the first seconds of the step response of a 10 mm part (exact column, program column, 2D reference); right, the swing of the 20 Hz, 10 W wave against the number of laminate cells across the gap.*

**(a) Through the thickness: the laminate's capacity that the node holds, not the copper.** The 1D column of the program's structure (one node per layer, the copper plus 0.77 mm of FR-4 of its slab, link k_z A / d, `lib/columns.py`) gives 0.753 K for the wave, the program 0.747 to 0.758 K: the 8.4 is the discretisation. The copper alone is not at fault: one copper cell or four per layer give the same swing (the 35 um of copper is isothermal in 11 us), 6.33 K. What is wrong is the 0.77 mm of laminate at the temperature of the copper: capacity 1394 J/m2K against 120 J/m2K of the copper plus the laminate that actually follows (the depth is `sqrt(alpha_FR4 T / pi)`: 0.06 mm at 20 Hz). In steady state and for periods above a few seconds the node is right.

**What it costs to fix by cells.** Laminate cells across the gap, swing of the 10 W, 20 Hz wave: graded cells (1.5 um at each copper face) 2 / 4 / 8 / 16 / 32 per gap: 8.68 / 8.37 / 6.55 / 6.40 / 6.33 K; **equal** sub-gaps (the laminate rule) 1 / 4 / 16 / 64 / 256: 8.69 / 8.62 / 7.55 / 6.41 / 6.32 K. The 2.33 / 3.62 / 4.93 K of `docs/validation.md` 36.3 for 4 / 8 / 16 sub-gaps are the program's own numbers with the cells only (a different structure from the equal sub-gaps above, where the node keeps its half-gap; the trend is the same: the series reaches the reference only at 16 graded or 64 equal cells). A converged answer needs about 16 cells per gap under the part and a thin first cell: 8 to 16 laminate nodes per gap under the part instead of one. Not tried in the program.

**(c) Lateral spreading.** Over a full-copper sheet it matters only for the slow end and small parts. 1D exact against 2D reference (K/W, duty 30 %): 10 mm part 21.8 / 5.82 / 1.12 / 0.151 / 0.0169 against 9.85 / 4.73 / 1.14 / 0.151 / 0.0169 at 0.1 / 1 / 10 / 100 / 1000 Hz; 2 mm part 546 / 145 / 28.0 / 3.77 / 0.417 against 27.1 / 20.2 / 12.1 / 3.81 / 0.421. From 100 Hz up the 1D column is the answer (a 2 mm part: 1 %); below it the spreading takes over, so a pure column correction fails (section 5.1).

**(b) The quasi-static face term of 2.5.x (part over bare laminate, no copper: 10 mm part, 2 layers, h 10; reference = pure FR-4 board, top face; duty 50 %).** Program / reference: 0.98 / 0.92 / 0.78 / 0.58 / 0.49 / 0.52 / 0.67 / **0.90** / 1.66 / 3.94 / 10.5 / 34 at 0.1 / 0.3 / 1 / 3 / 10 / 20 / 50 / 100 / 300 / 1 k / 3 k / 10 k Hz. The face term `Q t_cu / (2 k_z A)` is right where it was said to be (about 100 Hz: 0.635 against 0.641 K/W), overstates above (not attenuated: 0.58 K/W where the true value falls to 0.014 at 10 kHz; the safe side, as `profiles.py` says) and below 50 Hz the node (capacity again) underestimates by up to 2 times. So the bare case has both effects with the opposite sign at the two ends. The reference with the copper taken out is a bare-board idealisation: the program's bare node still holds `t_cu` of absent copper.

## 4. The decision today (question 2)

![where the decision is wrong](figures/fig_04_wrong_decisions.png)

*Figure 4 (`fig_04_wrong_decisions.png`): 10 mm part, 2 layers, 30 %: the swing of the power and the frequency where the program averages (red) a wave whose true swing exceeds 1 K.*

One heater, budget 1 K, swing of the power 0.5, 1, 2, 5, 10 and 20 W, all 864 cases (5184 decisions): the program **averages a wave whose true swing exceeds the budget in 948 decisions (18.3 %)**, never the other way (0 resolves of a wave that could be averaged: the node errors are all on the low side). By frequency (decisions of 432): 1 Hz 28, 3 Hz 66, 10 Hz 124, 20 Hz 152, **50 Hz 176**, 100 Hz 168, 300 Hz 124, 1 kHz 68, 3 kHz 36, 10 kHz 6. The worst: a 20 W swing on a 2 mm part at 1 kHz, 50 % (the program 0.8 K, the truth 9.97 K). With the shared budget (several heaters) the sum of the true swings is also higher than the budget by the same factors. The profile curves of a heater that is resolved carry the same error (the same node), so even a correct decision leaves a fast resolved ripple 8 to 12 times too small (fast waves that are resolved are rare: they cost one step per fraction of the period).

## 5. The correction (question 3)

### 5.1 First try, rejected: the difference of two columns

`lib/correction.py`: `Z_corr(t) = Z_program(t) + [Z_exact column(t) - Z_lumped column(t)]`, both columns of the footprint area; zero at t = 0 and at long times. Against the reference over the sweep it is within 0.90 to 1.00 from 100 Hz to 3 kHz (2 layers, 10 mm: 0.98 at 100 Hz), but **overshoots at the slow end** (2 mm part, 2 layers: 8.9, 8.2, 6.0 times at 0.1, 0.3, 1 Hz; 10 mm part 1.7, 1.6, 1.3) because the column has no lateral spreading. Scaling by the share the program keeps, `phi = Z_program / Z_lumped column`, fixes 1 layer at the slow end but spoils the fast end (0.5 for 1 layer, 5 to 10 mm: the program's own spreading is too slow, 3.3 above). Not adopted.

### 5.2 E3: the closed-form impedance of the top sheet (adopted as the proposal)

`lib/impedance.py`. Two derived pieces, both own derivations:

1. `Y(w)`, the admittance per unit area of the stack under the top face of the top copper, from the transfer matrices of the layers (the recursion with `tanh`, stable for a thick laminate; `gamma = sqrt(j w rho c / k)`, convection of both faces) with the layers' real thicknesses and properties.
2. The top copper as a sheet of conductance `S = k_cu t_cu` over the vertical admittance `Y`: `S nabla2(theta) - Y theta = -q(r)`. For a uniform flux on the disc of radius `a` (equal area to the part), `m^2 = Y / S`, the centre rise is `(q0 / Y)(1 - m a K1(m a))` and the disc mean `(q0 / Y)(1 - 2 I1(m a) K1(m a))` (complex Bessel functions). The deeper copper layers are **not** added to `S` (laminate decouples them in a wave: with their conductance the swing is 0.4 to 0.7 of the reference at the slow end).

The swing of a square wave is the peak-to-peak of the sum of the harmonics `Z(k w0) c_k` (16 384 samples per period, one inverse FFT, 2.2 ms). **Against the reference over all 864 cases: ratio 0.994 to 1.111, median 1.000, 5 %-95 % 0.995 to 1.056** (the 5 % high ones are the 10 kHz points, a limit of the harmonic count; 1.057 for four layers at 0.1 Hz, from the inner planes: on the safe side). Spot values (K/W, duty 30 %): 10 mm 2 layers 0.1 / 1 / 20 / 100 / 1000 / 10 000 Hz ratios 0.999 / 0.996 / 0.997 / 0.999 / 1.005 / 1.053; 2 mm: 1.009 / 1.000 / 0.995 / 0.997 / 1.004 / 1.053. Cost: no unknowns, 2 ms per heater and wave.

**Decision with the floor `oscillation = max(program, E3)`** (same 5184 decisions): 0 wrongly averaged (948 before), 12 wrongly resolved (the truth is within 11 % below the budget), which is the E3 overshoot on the boundary.

### 5.3 What it changes in the program's own cases (`study_impact.py`, budget 1 K)

| case | heater | program | E3 | decision |
| :-- | :-- | --: | --: | :-- |
| `example_with_profiles` 100 Hz (`tests/test_profiles.py`), `examples/profile_board` | U1, 13.3 W swing | 0.393 K | 2.013 K | average -> **resolve** |
| the same at 1 kHz (`test_profiles.py` line 160) | U1 | 0.039 K | 0.226 K | stays average |
| mixed regimes test (60 x 50 mm, 10 mm, 20 Hz) | fast | 0.747 K | 6.355 K | average -> **resolve** |
| the slow heaters (0.05 and 0.5 Hz) | U2 / slow | 84.9 / 9.5 K | 97.9 / 23.5 K | already resolved (E3 overstates: no vias, no inner planes, no neighbours) |

Which frozen numbers move: **none** of the 251 records and 58 times of `tests/regression` (the harness copies the problems without profiles, and the correction is in the decision, not in the step responses). Which tests would move: `tests/test_profiles.py` (the tests that use `example_with_profiles()` at 100 Hz and expect `average` for U1 (lines 46 to 211), the mixed-regimes test that expects `["average", "resolved"]`), `tests/test_gui_profile.py` and the stress scenarios that run the profile page on the example, the screenshots of the profile page (`examples/make_screenshots.py`). They would need expectations that say 'resolved' or a faster U1 (1 kHz). Not run: they were reasoned from the table, because the program is not edited here.

### 5.4 Limits of E3

Tested only with a heater on the top copper of a full-copper board, a disc source, manual h, no vias, no other heater. Not tested: a heater on an inner or bottom layer (the same recursion from that layer, both directions), a partial copper, an elongated part, vias (they carry heat down: E3 overstates at the slow end, as the 97.9 against 84.9 K above, which is the safe side for a floor), the copper edges and the board edge. Because it overestimates at the slow end where the program is already right to 5 to 10 % above 5 s, the floor is applied **only for periods below the threshold of section 6**.

## 6. The warning rule if E3 is not adopted (question 4)

The program's swing is within 10 % of the truth for `T >= T_w` and below it understates by a factor that grows to 8 to 12 (table 1). From the sweep, per slab of `s = thickness / layers`: `T_w = 5 s * (s / 0.8 mm)^2`: 5 s (0.2 Hz) for the 1.6 mm two-layer or one-layer board, 1.25 s for four layers (ratio 0.88 to 0.97 at 0.3 Hz, 0.66 to 0.87 at 1 Hz; the exponent is read from two thicknesses, not fitted further). The warning: *"the heater X switches faster than T_w; the layered models average through the laminate; the real swing is about 8 times larger than computed (up to 12 for 2 layers): use E3 or the 3D solid"*; it needs no run: the period and the stack are enough. A bare part: the same threshold, and above about 300 Hz the face term overstates (safe).

## 7. Conclusions

1. The 8 times is reproduced with an independent reference (6.37 K against 0.75 K, 8.4 times) and the program's own number (0.747 to 0.758 K).
2. It is the laminate capacity held by the single node, not the copper, not the lateral spreading (from 100 Hz up) and not the face term: the program understates the swing at every frequency above about 0.2 Hz, by 2 to 3 times at 1 to 3 Hz and by 8 to 12 times (4 layers 5 to 7) from 50 Hz to 1 kHz.
3. The decision is wrong (averages a wave above the budget) in 948 of 5184 decisions (18 %) in the sweep, never the other way; it is wrong over the whole range of 1 Hz to 10 kHz for the powers of an electronic part (a few watts, a 10 mm part at 10 to 300 Hz).
4. The smallest correction that works over the sweep is a closed-form estimator (E3: the impedance of the layered stack under a disc on the top sheet, no unknowns, 2 ms) used as a floor of the decision: 0 wrong averages, 12 borderline resolves; the column difference tried first is rejected (section 5.1). The curves of a resolved fast heater keep the error (section 4) and are a second step of the proposal (INTEGRATION.md).

## What was read and what was not verified

* **Read in full**: `CLAUDE.md` (research rules), `docs/validation.md` 36.2 and 36.3 and the `docs/versions.md` 'Planned' note of `fix/laminate-edge-band`, `pcbthermal/profiles.py` (decision, wave_response, face terms), `fvm.py` step_responses_from_network, the `fvm.Network` node rules (capacity, link), `laminate.py` (one-layer nodes). `tests/test_profiles.py` for the decisions.
* **Reproduced**: the 0.75 K of the program and the 6.3 K of the independent solution (6.33 / 6.37 K here); every table above is printed by the scripts and saved in `out/` (git-ignored).
* **Sources by key** (`research/theory/BIBLIOGRAPHY.md`): [CarslawJaeger] for the disc source on a sheet with a vertical loss and the layered slab impedance, **status M** (not opened: the forms of 5.2 are own derivations, checked against the numerical reference to 0.5 % and 5 % at 10 kHz); the semi-infinite step `2 q sqrt(t/pi)/e` is a textbook result checked numerically (status M). No published numerical case of a fast-wave swing was reproduced: the only external anchor is the 6.31 K of the independent 1D solution of the review of `fix/laminate-edge-band` (its script was not rerun).
* **Not verified**: a heater on an inner or bottom layer; partial copper, vias, an elongated or rotated part, edges; a real board measurement (none exists); the time grid of the program above 3 kHz as the cause of ratios below 0.05; the Analytic and Lumped models (the study is of the FVM and FDM step responses; the FDM was not run, it shares the node structure); the 17 frozen boards' profile records: there are none (the harness removes profiles), and the tests listed in 5.3 were not run against the correction; computed h as a separate case (only h 10 and 30 W/m2K). The program-side numbers use the cell of side/4 (at most 1 mm) at 60 x 40 mm; the cell dependence of the program's swing was seen only at 1 and 2 mm (0.758 and 0.747 K).
