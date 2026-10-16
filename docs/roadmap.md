# Roadmap and Design Notes (next version: 2.1.0)

Status 2026-10-16: version 2.0.0 is released. Work for 2.1.0 happens on `feature/more-models`. This file records the design discussions, the
evidence gathered and the decisions taken, so that implementation can start from here. Items are in the agreed order.
References are listed at the end; claims taken from the literature are marked with the source number, the rest are our own derivations or measurements.

## 1. Variable power: profiles, PWM, pulses (implemented on `feature/more-models`)

> **Status**: implemented as designed below (`pcbthermal/profiles.py`, `fvm/lumped/analytic.run_profile`, GUI "Power profile" tab, CLI `run` options). Differences from the notes:
> the periodic-peak decision uses a monotone (PCHIP) interpolation of the step response in log time (0.4 % error against the exact RC solution); the analytic transient smears
> vias and sinks; the mixed run is validated by `tests/test_profiles.py` (the difference to the fully resolved run is bounded by the neglected oscillation).

### 1.1 Why it matters (measured)

Same average power, same board (example board, 4 W + 1.5 W scaled together; 10× power for 10 % of every 10 s):

| Quantity | Value |
| :-- | --: |
| Steady state with the average power | 85.8 °C |
| Steady state if the pulse power were continuous (upper bound) | 633.1 °C |
| Periodic-steady-state peak at the end of a pulse (simulated) | 262.7 °C |

The steady-state models alone would call this board safe at 86 °C while it peaks near 263 °C.

### 1.2 Peak-temperature formulas (verified against our solver)

Linear time-invariant response: with `Z(t)` the step response of the hottest point (°C/W of total power), `Rth = Z(∞)`, period `T`, pulse width `tp = D·T`
and on-state power `P_on`, the peak at the end of a pulse in periodic steady state is, by superposition,

`ΔT_peak = P_on · Σ_{m=0..∞} [ Z(m·T + tp) − Z(m·T) ]`

The datasheet shortcut used by manufacturers [1, 2, 3] is `ΔT_peak ≈ P_on · [ D·Rth + (1 − D)·Z(tp) ]` (the "normalised effective transient thermal impedance"
`D + (1 − D)·z(tp)`), and the average-power result is `P_on · D · Rth`.

| T [s] | D | P_on / P_nominal | simulated, periodic steady state | exact superposition sum | datasheet shortcut | steady, average power | steady, P_on (bound) |
| --: | --: | --: | --: | --: | --: | --: | --: |
| 10 | 0.10 | 10 | 262.7 °C | 267.3 | 278.0 | 85.8 | 633.1 |
| 2 | 0.25 | 4 | 123.9 | 127.6 | 134.7 | 85.8 | 268.3 |
| 60 | 0.50 | 2 | 124.3 | 124.2 | 127.3 | 85.8 | 146.6 |
| 1 | 0.10 | 10 | 117.9 | 118.7 | 131.5 | 85.8 | 633.1 |

Reading: the exact sum agrees with the simulation within 0.1 to 3 % (the remaining difference is time discretisation of the check); the datasheet shortcut is
**conservative by 4 to 11 %**. A cold start overestimates the first cycle (273.5 °C against 262.7 °C converged). Starting from the **steady state of the average power**
the periodic regime is reached in about 5 to 12 cycles, because only the ripple has to settle.
(The exact superposition expressions in the sources [1, 2] could not be read from the PDFs; the sum above was derived and verified numerically here.)

### 1.3 Design (agreed 2026-10-16)

- **Which models:** all three, because with constant `h` the problem is linear.
  FVM: implicit time stepping (exists, validated). Lumped: the same stepping on each heater's small dense network (capacities from the real cells), heaters superposed.
  Analytic: every cosine mode decays exponentially, so piecewise-constant power has a closed form; vias and sinks are smeared in the transient (documented limit).
  Because the response is linear, one step response (Zth) per heater plus convolution gives any profile quickly (sweeps of duty cycle and frequency).
  With temperature-dependent `h` (section 2) superposition no longer holds: only time stepping.
- **Steady-state models and power:** selectable per run: **average** (default, physical for fast PWM), **peak** (`P_on`, worst-case bound) and, when a step response is available, the **periodic peak** (formula above).
  Results show all three numbers side by side so the bracket is visible.
- **Initial state (selectable):** cold (ambient), uniform temperature `T0` (for example an enclosure at 60 °C), steady state of a chosen baseline power (standby), or the periodic steady state
  (start from the steady state of the average power and iterate cycles until the change per cycle is below 0.1 °C).
- **Power profile tab** (not "PWM"; simplified in 1.4): a square wave (frequency or period, duty, `P_on`, `P_off`) with the derived average power and an automatic regime decision based on the
  estimated oscillation of the hottest point. Later: a segment table and CSV import.
- **What power is stored (open point, proposal):** store the **physical on-state power `P_on` and the duty** (a MOSFET's conduction loss or an LED's electrical input in the on-state do not
  change when the duty changes), and *derive* the average. A toggle lets the user enter the average instead (then `P_on = P_off + (P_avg − P_off)/D`), with a lock
  "keep `P_on` fixed / keep average fixed" for when the duty is edited. A heater without profile is a constant source (`D = 1`), so existing projects do not change.
  Switching losses of a converter are naturally an *average* contribution (extra average loss field), not part of `P_on`.
- **Limit to document:** switching at kHz to MHz is not resolved; the board responds to variations on the scale of its thermal time constants (hot spot about 19 s on the example board,
  milliseconds only very locally). Microsecond to millisecond events belong to the transient thermal impedance of the part [1, 2, 6].
- **Outputs:** Tmax(t) per heater, peak, minimum, oscillation, time above a limit, Zth(t) curve (with mutual curves between heaters), **peak-envelope map** (maximum over time at every cell), animation.
- **Validation plan:** square wave on the uniform slab against the exact RC solution; periodic peak against the superposition sum; energy balance; steady-state models reproduce the average-power result.

### 1.4 Time scales and the profile editor (refined 2026-10-16)

**Two situations that look alike, and the board treats them differently.** A switching waveform at kHz to MHz (MOSFET, LED PWM dimming at 100 Hz to a few kHz) is far faster than the
board can follow: the board only feels its **average power**. A slow duty cycle (seconds to hours: a fan on 30 s / off 70 s, a motor accelerating and holding, a radio transmitting in
bursts, a charger) is slow enough for the temperature to rise and fall: it must be **resolved in time**. Both are "power versus time" and use the same description (period, duty, on-state power,
off-state power); what differs is what the simulator does with it. So the feature is **not called PWM**: it is a **Power profile**, with an automatic regime decision.

**How fast is "fast" on our board** (example board, hottest point, from the FVM step response):

| t [s] | 1e-4 | 1e-3 | 1e-2 | 0.1 | 1 | 10 | 100 | 1000 |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: |
| Z(t) [°C/W] | 0.001 | 0.010 | 0.104 | 0.93 | 3.87 | 6.34 | 9.31 | 11.06 |
| share of Rθ | 0.0 % | 0.1 % | 0.9 % | 8.4 % | 35 % | 57 % | 84 % | 100 % |

Square wave with 10× the nominal power at 10 % duty (average rise 60.8 °C), exact periodic response by superposition of `Z(t)`:

| Frequency | Period | Peak rise | Valley rise | Ripple (peak-to-peak) | Ripple / average rise | Decision (threshold 1 °C) |
| --: | --: | --: | --: | --: | --: | :-- |
| 100 kHz | 10 µs | 60.81 °C | 60.81 | 0.001 °C | 0.00 % | average |
| 1 kHz | 1 ms | 60.83 | 60.79 | 0.05 | 0.08 % | average |
| 100 Hz | 10 ms | 61.1 | 61.2 | below the 0.06 °C noise floor of this check | about 0 % | average |
| 50 Hz | 20 ms | 62.71 | 61.51 | 1.2 | 2.0 % | average (boundary) |
| 30 Hz | 33 ms | 63.57 | 60.06 | 3.5 | 5.8 % | resolve in time |
| 10 Hz | 0.1 s | 63.5 | 44.95 | 18.6 | 30.5 % | resolve in time |
| 1 Hz | 1 s | 93.4 | 43.7 | 49.7 | 82 % | resolve in time |
| 0.1 Hz | 10 s | 242.1 | 29.8 | 212 | 349 % | resolve in time |
| 0.01 Hz | 100 s | 363.2 | 15.9 | 347 | 571 % | resolve in time |

On this board the boundary is near 50 Hz. It depends on the board (heater size, copper), so the **simulator computes it for the board at hand**: the ripple is obtained from the step response `Z(t)` of
the selected reference model (peak and valley sums as in 1.2, with the tail `D (Rθ − Z(M T))`). The decision rule is *oscillation below the threshold → use the average* (default threshold 1.0 °C, user-adjustable).

**Profile editor: simple on purpose (decided 2026-10-16: no waveform designer).** Two kinds of profile in 2.1:

1. **Constant** (default, the present behaviour).
2. **Square wave**, nothing else: frequency or period (unit selector Hz, kHz, ms, s, min), duty (%), power while on `P_on`, power while off `P_off` (default 0).
   Read-only derived values: on-time, average power `P_off + D (P_on − P_off)`, and the **decision text**
   ("Fast: the board only sees the average, oscillation 0.05 °C, using 12.4 W" or "Slow: resolved in time, about N steps, about X s").
   No delay, no rise and fall times, no extra-loss field: edges of milliseconds are invisible to the board (section 1.4 table), a delay is just a different start state, and any
   extra average loss can be added to `P_on` or `P_off` by the user.

Later and only if needed: a table of steps ("power for X seconds", repeated) and CSV import of a measured profile.

Typical uses: LED dimmed at 1 kHz and 30 %, MOSFET at 100 kHz: **fast, average**; fan or heater on/off every few seconds or minutes, motor start-hold-stop, communication bursts: **slow, resolved**.
A short single pulse (microseconds to a few milliseconds) heats the **die**, not the board: that belongs to the component's own transient thermal impedance (section 3), and the tab says so.

**The oscillation threshold.** One setting, in °C: *ignore oscillations smaller than* (default **1.0 °C**). The simulator estimates the peak-to-peak oscillation of the hottest point
(from the step response, section 1.2). If it is below the threshold the waveform is replaced by its average (exact to within that error, and instant); otherwise the cycle is simulated in time.
No percentages: the threshold is a temperature the user cares about. Temperatures and temperature differences are shown in **°C** everywhere in the application and the reports; thermal resistance is shown in **K/W** (the same number as °C/W).

**Per heater:** every heater has its own profile (different periods are fine: the response is the sum of each heater's contribution). The steady-state models use, per run, the average (default), the peak `P_on`
(worst-case bound) or the periodic peak (from `Z(t)`).

### 1.5 Duration, start state and cost

Two different "how long" questions:

**Simulated time (how much of the profile is simulated).** Setting *Duration*, derived from the profile and the board, three choices:
- **Until stable** (default for a square wave): cycle after cycle until the peak temperature changes by less than 0.1 °C between two consecutive cycles (cap: 100 cycles).
  Starting from the steady state of the average power this takes about 5 to 12 cycles (measured), because the mean of a periodic response equals the average-power steady state and only the oscillating part has to settle.
- **N cycles**: a fixed number of periods.
- **Fixed time**: seconds (the choice for heat-up from cold, where the board needs several of its time constants, hundreds of seconds on the example board).

**Computing time (how long the run takes).** The time step is automatic: about one tenth of the shorter of the on-time and the off-time (the implicit Crank-Nicolson scheme is stable at any step, so the step
only has to resolve the waveform), with one matrix factorisation per run. Measured on the example board (FVM, one step of the 4-layer board):

| Cell size | Unknowns | Factorise once | One step | Steps per second |
| --: | --: | --: | --: | --: |
| 2 mm | 8 000 | 0.03 s | 0.8 ms | 1 300 |
| 1 mm | 32 000 | 0.23 s | 5.7 ms | 176 |
| 0.5 mm | 128 000 | 2.0 s | 29.6 ms | 34 |

Examples at 1 mm cells: period 10 s, duty 10 %, 12 cycles (120 s simulated, step 0.1 s, 1 200 steps): about 7 s; period 60 s, duty 50 %, 6 cycles (step 3 s, 120 steps): about 1 s;
50 Hz, 12 cycles (0.24 s, step 2 ms, 120 steps): about 1 s. The Lumped model needs milliseconds and the Analytic model microseconds per evaluation. The editor shows the estimated number of steps and time before running and
refuses runs above a cap (default 200 000 steps), suggesting the average instead.

**Start temperature (setting *Initial temperature*):** the user types a temperature in °C; the default is the board's **ambient temperature** (Environment ▸ Ambient, 25 °C unless changed), so
"cold start" is simply "initial temperature = ambient" and no separate cold value exists. A second option, *start from the steady state of the average power* (default for a square wave), starts the board already at
its mean operating temperature so that only the oscillation has to settle. An enclosure at 60 °C is "initial temperature 60 °C" (and, if the air stays at 60 °C, ambient 60 °C).
Results report the last cycle (peak, minimum, oscillation) and, when starting from a user temperature, the heat-up curve; the animation shows the last cycles.

### 1.6 How the average-or-resolve decision is calculated (several heaters, each with its own regime)

Everything below is arithmetic on the **step response**, so it costs almost nothing once the response is known.

1. **Thermal response (once per board, cached until the board is edited).** For every heater *i* compute the response of its own hottest point to a unit step of its own power, `Z_i(t)` in °C/W, from about 10 µs to about five
   board time constants. With the FVM all heaters are solved together as several right-hand sides of the same matrix (about the cost of one transient, 0.4 s with 2 mm cells); the Lumped model gives `Z_i` from each heater's own network;
   the Analytic model from its modal closed form. The decision is made **once, with the reference model** (FVM if selected, otherwise Lumped, otherwise Analytic) and applied to all models so that they are compared on the same power input.
2. **Oscillation of one heater (instant, live while editing).** For a square wave of period `T`, on-time `tp = D·T` and swing `ΔP = P_on − P_off`, superposition of delayed steps gives the
   periodic peak and valley rises:
   `peak = ΔP · Σ_{m≥0} [Z(mT + tp) − Z(mT)]`, `valley = ΔP · Σ_{m≥1} [Z(mT) − Z(mT − tp)]`, with the tail of each sum `D·(Rθ − Z(M·T))` after `M` terms;
   `oscillation_i = peak − valley` in °C. (Verified against full time-stepping, section 1.2.)
3. **Several heaters: an error budget.** The oscillation a heater produces is largest at its own footprint and smaller elsewhere (diffusion smooths it), so `oscillation_i` bounds its effect on the whole board.
   The user threshold θ (default 1.0 °C) is a **budget for the total oscillation that may be ignored**: heaters are sorted by `oscillation_i` and averaged, smallest first, while the running sum stays within θ;
   the others are resolved. By the triangle inequality the neglected oscillation anywhere on the board never exceeds θ. The editor shows a table: heater, period, duty, average power, oscillation (°C and % of its average rise), decision.
4. **Running a mixed board.** The response is linear, so averaged heaters enter as constant power and resolved heaters as square waves **in the same time-stepping run** (one matrix factorisation, a source vector rebuilt each step).
   Time step: one tenth of the shortest on or off time **among the resolved heaters**; duration: *until stable* is judged over a window equal to the longest resolved period (default 10 windows, stop when the peak changes by less than 0.1 °C).
   If the resolved periods are incommensurate the combined signal never repeats exactly: the result is the peak observed in the window, and an extra number gives the **worst case if all peaks coincided**
   (average rise plus the sum of the individual peak excesses, an upper bound by linearity).
   When a slow and a fast heater are both resolved the step count grows (duration over the small step): the editor shows the estimate and, above the cap, proposes averaging the fast one (raising the threshold) instead.
5. **Percentages** may be shown next to °C ("oscillation 18.6 °C, 31 % of the average rise"); the decision itself uses °C only.

**Validation of the mixed run (2026-10-16, example board, 2 mm cells, 20 s).** Two heaters: U1 at 100 Hz, 30 % duty, 13.3 W on (average 4 W); U2 with a 20 s period, 25 % duty, 6 W on (average 1.5 W).

| Heater | Average rise | Estimated oscillation | % of the average rise | Decision (threshold 1.0 °C) |
| :-- | --: | --: | --: | :-- |
| U1 (100 Hz) | 54.4 °C | 0.41 °C | 0.8 % | **average** |
| U2 (20 s) | 31.4 °C | 84.8 °C | 270 % | **resolve** |

Reference: both heaters resolved with 0.5 ms steps (40 000 steps, 32 s of computing). Mixed run: U1 replaced by its average, U2 resolved (same start state, the steady state of the average power):

| Quantity | Both resolved | U1 averaged | Difference |
| :-- | --: | --: | --: |
| Peak of the hottest point over the run | 136.631 °C | 136.631 °C | 0.000 °C |
| Mean difference over the 20 s | | | +0.002 °C |
| Largest instantaneous difference | | | 0.384 °C (estimate: 0.41 °C) |

The neglected oscillation (0.38 °C) is within the estimate (0.41 °C) and the peak is identical, so the decision and the error budget are consistent. A mixed run with the large step needs only 40 steps (0.06 s of computing instead of 29 s).

**Time stepping rules learned from this test (implementation requirements):**
- The power held during a step `[t_n, t_n+1]` is the value **at the start of the step** (right-continuous), and the time grid must **contain every edge** of every resolved heater.
  Sampling at the end of the step shifted a pulse by one step: it turned a 30 % duty into 25 % (a 2 °C bias) and misplaced a 5 s pulse (a 41 °C error) in a first, wrong version of the test.
- Uniform steps of about one tenth of the shortest on or off time are accurate enough: hottest-point error at the end of a 5 s pulse (reference 136.52 °C):
  step 0.5 s (40 steps, implicit Euler) −0.37 °C; step 0.1 s (200 steps) +0.02 °C; geometric steps restarted after each edge with Crank-Nicolson (24 steps) +0.19 °C.
  Default: uniform step, Crank-Nicolson, with the number of steps shown before the run.


## 2. Computed convection and radiation (`h` not typed by the user) — implemented

> **Status (2026-10-16)**: implemented in `pcbthermal/convection.py` and `api._solve_computed_h`. Decisions taken from the open questions:
> (1) radiation is always part of the computed coefficient (emissivity 0 switches it off), per face, default 0.9; (2) the calibration multiplier is **global** and scales the convection only, never the radiation;
> (3) the coefficient is **one value per face** from the mean face temperature, the same definition for the three models (the correlations are for plate-average temperature), not per cell; the edge coefficient stays as typed;
> (4) the Picard iteration runs **outside** the models (`simulate` calls the model again with new coefficients, 3 to 4 solves); the time simulation and the animation use the coefficients of the reference model's steady state with the average power and keep them fixed during the cycle.
> Air properties are Sutherland-type fits checked against textbook values (300 K and 400 K within 1 to 3 %); blending of natural and forced convection is `(h_n³ + h_f³)^(1/3)` (Churchill's rule).
> The component top (section 3) will reuse the same functions.
>
> **Measured on the example board (FVM, 1 mm, orientation horizontal, emissivity 0.9)**; Tmax in °C, typed `h` = 10 top / 15 bottom:
>
> | Power (W) | Typed h | Computed h | Difference | Computed h top / bottom (W/m²K) | Vertical board | 2 m/s | Convection ×0.8 |
> | --: | --: | --: | --: | :-: | --: | --: | --: |
> | 0.55 | 31.1 | 31.9 | +0.8 | 10.4 / 7.9 | 32.0 | 29.9 | 32.1 |
> | 1.4 | 40.2 | 41.4 | +1.2 | 11.6 / 8.6 | 41.7 | 37.2 | 42.0 |
> | 5.5 | 85.8 | 85.8 | +0.0 | 14.2 / 10.1 | 86.7 | 73.5 | 88.1 |
> | 11 | 146.6 | 141.2 | −5.4 | 16.1 / 11.3 | 142.7 | 121.5 | 145.3 |
> | 22 | 268.3 | 245.3 | −23.0 | 18.6 / 13.1 | 247.8 | 215.6 | 252.0 |
>
> The typed values happen to be right near 5.5 W (a coincidence of top 14 + bottom 10 against 10 + 15), and wrong away from it: a constant `h` overestimates the temperature rise at high power by 10 % (22 W) and underestimates it at low power.
> Of the computed coefficient about 40 % is radiation on the top face (6.2 of 14.2 W/m²K) and 60 % on the bottom (6.1 of 10.1), which shows why emissivity matters: with 0.1 on both faces Tmax rises by more than 5 °C (test).
> The bottom face is worse than the top (facing down), unlike the typed defaults.

### 2.1 Idea and evidence

The user keeps the option of typing `h` (manual) and gains a **computed** option. `h` depends on the surface temperature, orientation, size, emissivity and air speed, so it is computed per cell from the
current temperature and iterated (Picard) on the same matrices. Prototype on the example board: `h` top 14.1 W/m²K at the hot spot, 11.7 average; bottom 9.1 (against 15 typed);
the temperature rise changed by **+6 %** (89.4 °C against 85.8 °C).

### 2.2 Correlations (isothermal plates, air)

- Rayleigh number `Ra = g β ΔT L³ / (ν α)`, `β = 1/T_film`, air properties at `T_film = (T_s + T_amb)/2`, `L = A/P` (area over perimeter) for horizontal plates [4, 5].
- Hot surface facing up: `Nu = 0.54 Ra^(1/4)` for 10⁴ ≤ Ra ≤ 10⁷, `Nu = 0.15 Ra^(1/3)` for 10⁷ ≤ Ra ≤ 10¹¹; facing down: `Nu = 0.27 Ra^(1/4)` for 10⁵ ≤ Ra ≤ 10¹⁰ [4, 5].
- Vertical plate (Churchill-Chu, laminar): `Nu = 0.68 + 0.670 Ra^(1/4) / [1 + (0.492/Pr)^(9/16)]^(4/9)` for Ra ≤ 10⁹, and the full-range form [4].
- Forced flow over a flat plate: laminar `Nu_L = 0.664 Re_L^(1/2) Pr^(1/3)` [4]; mixed laminar-turbulent and the combination of natural and forced `h` (general textbook practice, to be checked against the source before implementing).
- Radiation, linearised: `h_r = ε σ (T_s² + T_a²)(T_s + T_a)`; about 6 W/m²K near 50 °C, comparable with natural convection [7]. Typical emissivity of solder mask about 0.9 (to be sourced before shipping a default).
- Honest limit: these are isothermal-plate correlations; on a board with a hot spot the local `h` is uncertain by about ±20 to 30 %, so a **calibration multiplier** (fit to a measurement) is part of the design.
- Cooling selector: *manual h* · *still air (computed)* with orientation and emissivity · *forced air at v m/s*. The same model gives `h` for component bodies and heatsinks (section 3).

## 3. Component models (future; one Component element, today's heater is its Source type)

> The evidence for this section (standards, which datasheet metrics may be used, limits, validation plan) is in [`package_models.md`](package_models.md).

### 3.1 What the current models do and what a part really does

Today a part is a heater: all of its power enters the board under the footprint, and `theta_jb` only adds an offset to the reported junction temperature afterwards.
A real part has the junction (the die) generating the heat, which leaves by **two parallel paths**: downwards through the package pad and solder into the board (resistance junction-to-board, `θJB`), and
upwards through the package top (junction-to-case, `θJC,top`) into the air or a heatsink. The JEDEC two-resistor model (JESD15-3) is exactly this pair of resistances, for single-die packages [8, 9].
The current models cannot represent the top path: they send too much heat into the board (hotter board, hotter junction) and cannot represent a heatsink on the part itself
(a "sink" element only raises `h` on the board surface). Estimate with the reference board (5 W, board resistance 13 °C/W, `θJB` 6 °C/W):
board only: junction rise 5 × (13 + 6) = 95 °C; with a top path of 25 °C/W (θJC plus heatsink) the heat splits 57 % board / 43 % top and the junction rises about 54 °C (series-parallel estimate, not a measurement).
Limits of the 2R model (one-dimensional heat flow, lowest accuracy of the JEDEC models, DELPHI recommended for higher fidelity) are stated in [8, 9].

### 3.2 Implementation sketch

- **Element `Component`** with a type (*Source* = today's heater, *Package* = JEDEC 2R, passive areas, see 3.3 and 3.4; the earlier working names Pad and Duo are withdrawn): layer, pad/footprint polygon, power or profile,
  `θJB` (°C/W), `θJC,top` (°C/W), top cooling (none, a heatsink resistance in °C/W, or a surface area exposed to the computed `h`), optional heat capacities and, later, a Foster RC chain of the
  junction-to-case transient impedance (as published by manufacturers [6, 10]) so that package-level pulses are captured. Values are entered by the user; no datasheet numbers are invented.
- **FVM:** one extra unknown `T_j` per component (a dense row over the footprint cells). The footprint cells couple to `T_j` with `G_i = w_i / θJB` (`w_i` coverage weights, `Σ w_i = 1`), `T_j` couples to ambient with
  `G_top = 1 / (θJC,top + R_top)`, and the power is injected at `T_j`. The augmented matrix stays symmetric positive definite. Outputs: `T_j`, `T_case`, power into the board and through the top.
- **Lumped:** `T_j` is a node attached to ring 0 of the heater layer (conductance `1/θJB`) and to ambient (`G_top`); power enters `T_j`.
- **Analytic:** a scalar Woodbury update using the footprint-average modal response already available from the tile machinery: `θ̄_fp = θ̄_0 + g_ff f`, `f = G_b (T_j − θ̄_fp)`, `T_j = (P + G_b θ̄_fp)/(G_b + G_top)`.
- **Backward compatibility:** a heater is the special case `θJB = 0`, `G_top = 0`. The old `theta_jb` post-processing field is superseded.
- **Validation:** limits (θJB → 0 reproduces the heater; G_top → 0 gives heater + offset), exact series-parallel solution on the uniform board, energy balance, power split.
- **Timing:** implement after power profiles and the computed `h` (the `h` model feeds the top surface; the profile model defines the component's power input). Suggested stages:
  (1) Pad and Duo, static, in the three models; (2) top surface and heatsink from the computed `h`; (3) Foster chain for package transients.

### 3.3 Areas that are not heaters (to discuss before implementing)

A "component" is more than a heat source: it is an *area* of the board with its own thermal behaviour. Candidate kinds, all sharing the same footprint polygon and a layer:
- **Heat source** (today's heater): power into the board.
- **Passive area with extra cooling**: a heatsink or exposed surface, extra `h` or a resistance to ambient in K/W over the polygon (today's "sink" is the simplest case).
- **Contact area**: a thermal pad or enclosure touching the board, a conductance in W/(m²·K) to a fixed temperature (not necessarily the ambient).
- **Material patch**: a region with different conductivity or thickness (metal-core insert, thermal-via field described by density instead of single vias).
- **Package (2R)**: heat source plus a junction node and the two paths of section 3.2.

**Decision (2026-10-16, maintainer agreed):** one **Component** element with a type and the properties that type needs. Today's heater is the type *Source* with nothing else set, so existing projects keep working unchanged.

### 3.5 Heat sink on a component

Decided: top cooling "heat sink" = `θCS` and `θSA` in K/W, `θSA` scaled with the temperature rise from a reference `ΔT_ref` (`(ΔT/ΔT_ref)^(-1/4)` for natural convection, checked against a real curve before shipping), and an optional heat-sink capacity `C_hs` (J/K) from the first version. Details and reasons: [`package_models.md`](package_models.md) section 4b.

### 3.4 How a component enters the simulator

| Question | Design |
| :-- | :-- |
| Simple use | A Source is just a power in a footprint, as today. Types and parameters are opt-in; the editor shows only the fields of the chosen type. |
| Heat generation | Types *Source* and *Package* have a power (constant or square wave). Passive types (*Cooled area*, *Contact*, *Material patch*) have none. |
| Package (2R) | One extra node `T_j`; the power enters `T_j`; `θJB` to the footprint cells, `θJC,top` plus a top cooling path to the air (sections 3.1, 3.2). Reported: `T_j`, `T_case`, split of the power between board and top. |
| Temperature | The top cooling uses the computed `h` of section 2 (a small hot surface, its own area and temperature), so a package makes the problem temperature dependent exactly as the board does: the Picard iteration of section 2 covers both. Without computed `h`, the top path is a fixed resistance in K/W. |
| Power profile | The profile drives the power of the Source/Package as now. The average-or-resolve decision measures the oscillation at `T_j` (the thing the user cares about), computed from the step response of `T_j`, which includes `θJB`; the periodic-peak formulas of section 1.2 are unchanged. |
| Time behaviour | Quasi-static `T_j` (no heat capacity) is exact for periods above a few milliseconds; the package heat capacity matters for microsecond to millisecond pulses and is added later as a Foster RC chain from the manufacturer's `Zth,JC` curve. Until then the warning lists the shortest period for which the quasi-static assumption holds. |
| Models | FVM: extra unknown per package (section 3.2); Lumped: a node on ring 0; Analytic: scalar Woodbury update. Passive areas map to extra `h` or conductance on the footprint cells (the analytic tile machinery already does this for sinks). |
| Staging | (1) Component element + Package statically, three models; (2) top path from the computed `h`; (3) passive areas; (4) Foster chain. |
| Validation | `θJB → 0` reproduces a Source; no top path gives Source plus an offset; exact series-parallel solution on a uniform board; energy balance; split of the power. |

## 4. Multigrid solver (optional, low priority)

Measured on the example board (4 layers), seconds per steady solve:

| Unknowns | Sparse direct (current default) | CG, Jacobi | CG, algebraic multigrid (`pyamg`) |
| --: | --: | --: | --: |
| 32 000 | 0.24 | 0.08 | 0.12 |
| 128 000 | 2.3 | 0.6 | 0.7 |
| 262 000 | 4.6 | 2.3 | 2.1 |
| 512 000 | 16.2 | 6.5 | 4.2 |
| 987 000 | not run (memory) | 12.8 | 8.0 |

All agree to 1e-8 °C. The gain only appears above about 500 000 unknowns, where the direct solver slows down and needs a lot of memory and multigrid scales almost linearly (`pyamg` stays an optional dependency,
chosen automatically above a threshold). Plain CG already captures most of the benefit for moderate sizes.

## 5. 3D finite elements as an independent validation (not a product feature)

Runs locally (laptop, no cloud): `scikit-fem` is already installed in the venv. A 100×80 mm board with 4 copper layers on a graded hexahedral mesh is a few hundred thousand elements, seconds to a few minutes with a sparse solver. One script, run by hand when needed.


Offline script with `scikit-fem` (installed in the virtual environment for experiments, not in `requirements.txt`): structured hexahedral mesh of the board with graded layers (35 µm copper slabs between FR-4 layers),
anisotropic FR-4, convection on the faces. Compare with the FVM on three reference boards to quantify the error of treating copper as a 2D sheet; validate vias separately with one via on a fine mesh. Output: a short validation report in `docs/`.

## 6. Deferred

Neural-network surrogates (not now); trace Joule heating (IPC-2152 style); reduced-order models (only if transients become too slow); naming of the models. The working names Mesh / Network / Fin and Source / Pad / Duo were proposed without research and are **withdrawn**: the standard terms are finite volume method (FVM),
lumped-parameter thermal network (LPTN, also called thermal resistance network) and analytical or semi-analytical (Fourier series) models [11, 12, 13, 14], and for components the JEDEC two-resistor (2R) and DELPHI
compact models [8, 9]. Recommendation under discussion: keep the technical names and API keys (`fvm`, `lumped`, `analytic`; renaming would break project files, the API and the published 2.0.0), and only make the
labels in the interface more descriptive, for example "Finite volume (FVM), reference", "Thermal network (LPTN)", "Analytical (Fourier series)", and "2R component" for the future component element.

## 7. Import of Gerber files for the copper of each layer (future extra)

Goal: read the copper of every layer from the manufacturing files instead of drawing zones by hand, so the real copper (traces, pours, pads, thermal reliefs) enters the models.
- **Input**: Gerber RS-274X per copper layer (plus the Excellon drill file for the vias and the board outline layer for the shape). Candidate library: `gerbonara`, a Python library for reading, modifying and writing Gerber, Excellon and IPC-356 files [15]
  (to be evaluated for licence, rasterisation of apertures, regions and clear polarity; not installed). Alternative: parse only what we need.
- **Mapping to the model**: rasterise each layer on a fine grid and store the **copper fill fraction per cell**. This is what the FVM already needs (`f` in the cell conductivity `S = f k_cu t_cu + k_FR4 (slab - f t_cu)`) and what the Lumped and Analytic models use through the zone coverage;
  the editor keeps zones as polygons for the hand-drawn case and gets a second source "imported raster" that is not editable polygon by polygon. Drills with plating become vias (position, drill diameter, plating from the stack-up).
- **Limits to state in the program**: the fill fraction of a cell hides the connectivity of traces (a cell that is half copper may be one long trace or two disconnected pieces; the effective in-plane conductivity depends on the direction), so the imported raster is an approximation
  that improves with a finer grid; the fine grid must be the FVM grid (or the cell fraction is averaged), which raises the cell count; the Analytic model needs layer-average copper plus local corrections and loses the detail; soldermask openings are irrelevant for conduction but matter for the emissivity of section 2.
- **Open questions**: units and file variants (KiCad, Altium and Eagle outputs differ in apertures and polarity); one file per layer needs a layer-assignment step in the GUI; how to treat plane splits and anti-pads; component positions come from a pick-and-place file (a later extra), not from the Gerbers.
- **Validation**: import a board whose copper we also drew by hand and compare areas per layer and the FVM result; check energy balance and the number of cells.

## 8. Variable stack-up (future; plan the model for it now)

Today the board has one total thickness, per-layer copper thicknesses (already a list) and **equal dielectric gaps** (`Board.dielectric_thickness()` shares what is left of the thickness among the `layers - 1` gaps; each layer node represents a slab `thickness / layers`).
Real stack-ups have different copper weights, different core and prepreg thicknesses, and sometimes different materials. What changes and what to prepare:
- **Parameters** (per layer and per gap): copper thickness (exists), **dielectric thickness per gap**, **dielectric material per gap** (FR-4 core, prepreg, high-Tg, polyimide for flex, metal-core insulating layer, ceramic), through-plane `k`, in-plane `k`, density and specific heat. The same list gives the heat capacities for the time simulation.
  The board thickness becomes the **sum** of the stack (a derived value or a check), not an independent input; a stack-up table in the GUI (rows = copper and dielectric layers from the top).
- **Model impact**:
  - FVM: the layer node should represent `copper + half of each adjacent dielectric`, not `thickness / layers`; vertical conductance between two layers is the series of the half dielectrics (`g = k_through / d_gap` per gap, different per gap); the in-plane conduction uses the layer's own thickness. Vias cross all gaps (series of the plated barrel is unchanged; the dielectric between the barrel walls is negligible).
  - Lumped and Analytic: the vertical coupling `g_l` becomes a vector over gaps (the Analytic model uses one scalar coupling today: `slab`, `d_diel` and `g_diel` in `_effective_sheet` become per-gap vectors and the tridiagonal modal matrix takes a coupling per gap).
  - Time simulation: capacities per layer from the real thicknesses and materials.
  - Edge cooling uses the real thickness of each layer.
- **Why it matters**: the through-board resistance is the sum of the gaps `d_i / k_i`, so a thin prepreg under the heater layer and a thick core elsewhere give a very different result from equal gaps (the equal-gap model spreads the thickness evenly); a thick core between planes changes the spreading; a metal-core board is a different regime (high-`k` base). Expect first-order changes in `T_j` for boards with a thin top prepreg and an inner plane.
- **Backward compatibility**: when the gaps are equal the new code must reproduce the current results exactly (regression test).
- **Link with the Gerber import (section 7)**: the stack-up table also provides the copper thickness and plating that the import needs.

## References

1. Texas Instruments, *Using MOSFET Transient Thermal Impedance Curves in Your Design*, SLUAAT8, https://www.ti.com/lit/pdf/sluaat8 (repetitive pulses, effective normalised impedance `D + (1 − D) z(t)`).
2. Vishay, *Current Rating of Power Semiconductors*, https://www.vishay.com/docs/91419/appnote9.pdf.
3. Infineon, *Dynamic thermal behavior of MOSFETs*, https://www.infineon.com/assets/row/public/documents/24/42/infineon-application-note-dynamic-thermal-behavior-of-mosfets-applicationnotes-en.pdf.
4. Nusselt number correlations (natural convection vertical and horizontal plates, flat-plate forced convection), https://en.wikipedia.org/wiki/Nusselt_number (secondary source quoting the standard textbook correlations).
5. Natural convection from an isothermal plate (MIT DSpace), https://dspace.mit.edu/bitstream/handle/1721.1/148015/thermo-03-00010-v2.pdf.
6. Nexperia, AN11261, *Using RC thermal models* (Foster and Cauer networks), https://mouser.com/pdfDocs/AN11261-3.pdf.
7. Electronics Cooling, *Don't underestimate radiation in electronics cooling*, https://www.electronics-cooling.com/2001/02/dont-underestimate-radiation-in-electronic-cooling/.
8. JEDEC JESD15-3, *Two-Resistor Compact Thermal Model Guideline* (2008), https://www.jedec.org/standards-documents/docs/jesd-15-3 (page not readable by the fetch tool; scope taken from the search summary).
9. ROHM, *Two-resistor model for thermal simulation*, https://fscdn.rohm.com/en/products/databook/applinote/common/two_resistor_model_for_thermal_simulation-e.pdf.
10. Infineon, *Application Note AN 2012-03 (OptiMOS datasheet explanation)*, https://www.infineon.com/assets/row/public/documents/24/42/infineon-mosfet-optimos-datasheet-explanation-applicationnote-en.pdf.
11. Review of thermal modeling classes (analytical lumped-parameter network versus numerical FEM, FVM, FDM, CFD), https://www.sciencedirect.com/topics/engineering/thermal-model.
12. Maya HTT, *Lumped parameter thermal networks in electric machine design*, https://www.mayahtt.com/blog/lumped-parameter-thermal-networks-in-electric-machine-design/ (LPTN, thermal resistance network).
13. Siemens, Simcenter Flotherm (structured Cartesian grid solver, compact thermal models), https://www.siemens.com/en-us/products/simcenter/fluids-thermal-simulation/flotherm/ ; Cadence Celsius EC Solver, https://www.cadence.com/en_US/home/resources/technical-briefs/celsius-ec-solver-tb.html ; Ansys Icepak (Fluent CFD solver), https://www.padtinc.com/simulation/simulation-product/ansys-icepak/.
14. Fourier-series analytical models of multilayer PCBs, https://hal-univ-paris10.archives-ouvertes.fr/hal-01473744v1 (via clusters as heat spreaders) and https://arxiv.org/pdf/1705.09925 (semi-analytical multilayer diffusion).
15. gerbonara, Python library to read, modify and write Gerber, Excellon and IPC-356 files, https://pypi.org/project/gerbonara/ (documentation: https://gerbolyze.gitlab.io/gerbonara); listed only; not evaluated or installed.
